"""Export a policy from the trainer's slop tasks (milli_slop_env_cfg.py) to ONNX, with a JSON beside it that says how to build its input.

Run from the trainer's folder, with its environment active:
  python ../duck-droids/trainer/export_slop.py TASK CHECKPOINT OUT.onnx
writes OUT.onnx (the trainer's exporter) and OUT.json: each input block in order, its size, history, units and where a runtime gets it,
the joint order, the standing pose the joint inputs and the actions are relative to, and the servo numbers it was trained with.

The two policies of the two-stage walk:
  walk_imu.onnx    Mjlab-Velocity-Flat-Milli-Dynamixel-Slop          gyro, gravity, joints, last action, commands (the Pi with its IMU)
  walk_blind.onnx  Mjlab-Velocity-Flat-Milli-Dynamixel-Slop-Student  joints, last action, each with history, commands: built from servo bus
                                                                     reads alone, so a PC on the bus can run it with no IMU
A Student task needs MILLI_TEACHER_CKPT set to its teacher's checkpoint (the runner loads it to build the algorithm).
"""
import json
import sys
from pathlib import Path

import mjlab_microduck.tasks  # noqa: F401  (registers the tasks)
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg

from mjlab_microduck.export import ExportConfig, run_export
from mjlab_microduck.tasks import milli_slop_env_cfg as SL

WHERE = {
    "base_ang_vel": ("IMU gyro, body frame (x forward, y left, z up)", "rad/s"),
    "projected_gravity": ("gravity's direction in the IMU frame, unit vector; (0, 0, -1) standing level", "1"),
    "joint_pos": ("present position minus the standing pose below, in the trainer's joint directions (encoder reading: it includes gear play)", "rad"),
    "joint_vel": ("present velocity, same directions; trained one control step (20 ms) late, as the Dynamixel's averaged reading is", "rad/s"),
    "actions": ("the policy's own output at the previous step(s), raw (before adding the standing pose)", "rad"),
    "command": ("speed command: forward, left, turn", "m/s, m/s, rad/s"),
    "head_command": ("head pose command, off the standing pose: neck_pitch, head_pitch, head_yaw, head_roll; zeros to hold it", "rad"),
    "body_command": ("body pose command x, y, z, roll, pitch, yaw: unused by the walk, feed zeros", "m, rad"),
}


def main():
    task, ckpt, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.parent.mkdir(parents=True, exist_ok=True)
    run_export(task, ExportConfig(onnx_file=str(out), checkpoint_file=ckpt))
    cfg = load_env_cfg(task)
    cfg.scene.num_envs = 1
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda:0")
    om = env.observation_manager
    robot = env.scene["robot"]
    joints = [n for n in robot.joint_names if not n.startswith("passive_")]
    default = robot.data.default_joint_pos[0].tolist()
    blocks, off = [], 0
    for name, dims in zip(om.active_terms["actor"], om.group_obs_term_dim["actor"]):
        t = cfg.observations["actor"].terms[name]
        size = int(dims[-1]) if len(dims) else 1
        for d in dims[:-1]:
            size *= int(d)
        h = max(t.history_length, 1)
        what, unit = WHERE.get(name, (name, "?"))
        blocks.append(dict(name=name, offset=off, size=size, history=h, per_step=size // h, history_order="oldest first, newest last" if h > 1 else None,
                           source=what, unit=unit, delay_steps=[t.delay_min_lag, t.delay_max_lag],
                           noise=[t.noise.n_min, t.noise.n_max] if getattr(t, "noise", None) is not None and hasattr(t.noise, "n_min") else None))
        off += size
    info = dict(
        task=task, checkpoint=ckpt, inputs=off, outputs=len(robot.actuator_names), rate_hz=round(1 / env.step_dt),
        joint_order=joints, standing_pose_rad={j: default[robot.joint_names.index(j)] for j in joints},
        action="goal position = standing pose + output, per joint in joint_order, rad, in the trainer's joint directions (the Pi code's config maps them to ticks)",
        blocks=blocks,
        trained_servos={j: dict(kp_nm_per_rad_max=round(v["kp"], 3), peak_nm_max=round(v["peak_nm"], 3), noload_rads=v["noload_rads"]) for j, v in SL.SERVO_TABLE.items()},
        trained_position_p={"legs": 800, "neck_pitch": 1200, "head": 600, "note": "write these to the servos (the Pi code's default is 200); kp = P x 0.55/200"},
        latency="trained with 16-30 ms from command to servo, and the observation delays above",
        randomized=dict(gain_scale=SL.GAIN_DR, peak_nm=SL.PEAK_DR, backlash_deg=SL.BACKLASH_DEG, sag_travel_deg=SL.SAG_TRAVEL_DEG, sag_stiffness=SL.SAG_STIFFNESS),
    )
    out.with_suffix(".json").write_text(json.dumps(info, indent=1))
    print(f"{out} ({off} inputs) and {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
