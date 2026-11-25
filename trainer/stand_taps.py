"""How a stand policy behaves when a hand lets go of it, when it is nudged, and while its head performs microduck's emotions: who stays up,
and how often the feet tap (a foot leaving the floor and coming back).

  python stand_taps.py CHECKPOINT --task Mjlab-StandHand-Flat-Milli-Dynamixel-Bam [--envs 256] [--emote] [--video out.mp4]

Run from the trainer's folder (milli-rl), its environment active. Each robot: released tilted up to --tilt rad in pitch and roll (as the
hand-over task starts them), left alone to 4 s, then nudged forward (half the robots) or backward (the other half) by --kick m/s at 4 s,
measured to 7 s. With --emote, from 7 s each robot's head plays the 13 emotions one after another (as emote.py would), and that stretch is
measured too. The training's random pushes are off. Per stretch: % up at its end, foot lift-offs per robot per second, % of robots that lifted
a foot at all, and the median time between one foot's lift-offs on the robots that tapped (a fast tap shows as ~0.1-0.2 s).
"""
import argparse
import json
import os
from dataclasses import asdict

import numpy as np
import torch

import mjlab_microduck.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

ap = argparse.ArgumentParser()
ap.add_argument("ckpt")
ap.add_argument("--task", default="Mjlab-StandHand-Flat-Milli-Dynamixel-Bam")
ap.add_argument("--envs", type=int, default=256)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--tilt", type=float, default=0.35, help="rad: the release, up to this far off upright in pitch and roll")
ap.add_argument("--kick", type=float, default=0.15, help="m/s: the nudge at 4 s, forward on half the robots, backward on the rest")
ap.add_argument("--emote", action="store_true", help="from 7 s, the head plays every emotion in turn")
ap.add_argument("--emote-scale", type=float, default=1.0)
ap.add_argument("--out", help="a JSON of the numbers")
ap.add_argument("--head-direct", action="store_true", help="the head joints driven straight from the head command, the policy's head outputs ignored (it balances with the legs alone)")
ap.add_argument("--head-offset", default="0,0,0,0", help="rad, neck,head_pitch,yaw,roll: added to every head command, at rest too (the head's rest pose)")
ap.add_argument("--pushes", action="store_true", help="keep the training's random pushes on throughout (they are off by default)")
a = ap.parse_args()

cfg = load_env_cfg(a.task)
cfg.scene.num_envs = a.envs
cfg.seed = a.seed
torch.manual_seed(a.seed)
np.random.seed(a.seed)
if not a.pushes:
    cfg.events.pop("push_robot", None)
    cfg.events.pop("nudge", None)
    cfg.events.pop("tip", None)
cfg.curriculum = {}
cfg.episode_length_s = 1000.0
rb = cfg.events["reset_base"].params["pose_range"]
rb["roll"] = rb["pitch"] = (-a.tilt, a.tilt)
hp = cfg.commands["head_pose"]
hp.ranges = tuple((0.0, 0.0) for _ in hp.ranges)
hp.resampling_time_range = (1000.0, 1000.0)
if hasattr(hp, "emote_prob"):
    hp.emote_prob = 0.0
for n in ("body_pose",):
    if n in cfg.commands:
        cfg.commands[n].ranges = tuple((0.0, 0.0) for _ in cfg.commands[n].ranges)
env = RslRlVecEnvWrapper(ManagerBasedRlEnv(cfg=cfg, device="cuda:0"), clip_actions=load_rl_cfg(a.task).clip_actions)
runner = load_runner_cls(a.task)(env, asdict(load_rl_cfg(a.task)), device="cuda:0")
runner.load(a.ckpt, map_location="cuda:0")
policy = runner.get_inference_policy(device="cuda:0")
base = env.unwrapped
robot = base.scene["robot"]
feet = base.scene["feet_ground_contact"]
head_cmd = base.command_manager.get_term("head_pose")
_tn = list(base.action_manager.get_term("joint_pos").target_names)
HEAD_ACT = [_tn.index(n) for n in ("neck_pitch", "head_pitch", "head_yaw", "head_roll")]
HEAD_OFF = torch.tensor([float(v) for v in a.head_offset.split(",")], device="cuda:0")
dt = base.step_dt

emo = None
if a.emote:
    from mjlab_microduck.tasks.emotion_head import load_emotions
    emo = load_emotions()
    seq = torch.cat([torch.cat([q * a.emote_scale, torch.zeros(int(0.6 * 50), 4)]) for q in emo.values()]).to("cuda:0")   # 50 Hz = 1/dt
    owner = sum([[n] * (len(q) + int(0.6 * 50)) for n, q in emo.items()], [])        # which emotion each frame belongs to

T_KICK, T_EMOTE = 4.0, 7.0
T_END = T_EMOTE + (len(seq) * dt + 1.0 if emo is not None else 0.0)
STRETCHES = [("release 0-4 s", 0.0, T_KICK), ("nudge 4-7 s", T_KICK, T_EMOTE)] + ([("emotions", T_EMOTE, T_END)] if emo is not None else [])

obs, _ = env.reset()
N = a.envs
up = torch.ones(N, dtype=torch.bool, device="cuda:0")
fwd = torch.arange(N, device="cuda:0") < N // 2
prev = (feet.data.found > 0)
hid = [robot.joint_names.index(n) for n in ("neck_pitch", "head_pitch", "head_yaw", "head_roll")]
bl = [robot.joint_names.index(f"passive_{n}_backlash") if f"passive_{n}_backlash" in robot.joint_names else None for n in ("neck_pitch", "head_pitch", "head_yaw", "head_roll")]
head_err = []
# heat, as the over_rated penalty counts it: each servo's torque RMS over ~2 s (first order), against its rated 0.17 N m
RATED, TAU = 0.17, 2.0
heat = torch.zeros(N, len(robot.actuator_names), device="cuda:0")
act_names = list(robot.actuator_names)
groups = {"neck": [act_names.index("neck_pitch")], "head": [i for i, n in enumerate(act_names) if n.startswith("head_")],
          "knees": [i for i, n in enumerate(act_names) if "knee" in n], "hips": [i for i, n in enumerate(act_names) if "hip_pitch" in n],
          "ankles": [i for i, n in enumerate(act_names) if "ankle" in n]}
per_emo = {}
# the ankles as the real servo sees them, which friction doesn't hide (the parent, 2026-11-25: the sim's static motor torque runs 7-10x the real
# current-derived one): goal - present position on the motor side (no backlash; the servo's current scales with it), and the goal's step-to-step
# change (jitter)
ank_j = [list(robot.joint_names).index(n) for n in robot.joint_names if n.endswith("_ankle")]
ank_a = [act_names.index(n) for n in act_names if n.endswith("_ankle")]
prev_goal = None
hp_j, hp_a = list(robot.joint_names).index("head_pitch"), act_names.index("head_pitch")
rest_dev = []
lifts = []              # (t, env, foot)
ups = {}
for k in range(int(T_END / dt)):
    t = k * dt
    if abs(t - T_KICK) < dt / 2:
        v = robot.data.root_link_vel_w.clone()
        yaw = robot.data.heading_w if hasattr(robot.data, "heading_w") else torch.zeros(N, device="cuda:0")
        sgn = torch.where(fwd, 1.0, -1.0)
        v[:, 0] += sgn * a.kick * torch.cos(yaw)
        v[:, 1] += sgn * a.kick * torch.sin(yaw)
        robot.write_root_link_velocity_to_sim(v)
    head_cmd._command[:] = HEAD_OFF
    if emo is not None and t >= T_EMOTE:
        i = min(int(round((t - T_EMOTE) / dt)), len(seq) - 1)
        head_cmd._command[:] = seq[i] + HEAD_OFF
    with torch.no_grad():
        act = policy(obs)
        if a.head_direct:
            act[:, HEAD_ACT] = head_cmd.command[:, :4]
        obs, _, _, _ = env.step(act)
    was_up = up.clone()
    up &= ~base.termination_manager.terminated
    heat += ((robot.data.actuator_force / RATED) ** 2 - heat) * min(dt / TAU, 1.0)
    tgt = robot.data.joint_pos_target
    goal = tgt[:, ank_j] if tgt.shape[1] == len(robot.joint_names) else tgt[:, ank_a]
    jit = (goal - prev_goal).abs() if prev_goal is not None else torch.zeros_like(goal)
    prev_goal = goal.clone()
    ank_err = (goal - robot.data.joint_pos[:, ank_j]).abs()
    if t >= 1.0 and (emo is None or t < T_EMOTE) and up.any():   # the head at rest, no emotion: its pitch goal off the command (the real duck's flicks)
        hg = (tgt[:, hp_j] if tgt.shape[1] == len(robot.joint_names) else tgt[:, hp_a]) - robot.data.default_joint_pos[:, hp_j]
        rest_dev.append((hg - head_cmd.command[:, 1]).abs()[up].cpu())
    if emo is not None and t >= T_EMOTE:
        n_ = owner[min(int(round((t - T_EMOTE) / dt)), len(owner) - 1)]
        d = per_emo.setdefault(n_, {"fell": 0, "heat": {g: 0.0 for g in groups}, "aerr": [], "ajit": []})
        if up.any():
            d["aerr"].append(float(ank_err[up].mean()))
            d["ajit"].append(float(jit[up].mean()))
        d["fell"] += int((was_up & ~up).sum())
        if up.any():
            h = heat[up].sqrt()
            for g, ids in groups.items():
                d["heat"][g] = max(d["heat"][g], float(torch.quantile(h[:, ids].max(1).values, 0.9)))
    if emo is not None and t >= T_EMOTE and up.any():
        q = robot.data.joint_pos[:, hid] - robot.data.default_joint_pos[:, hid]
        for j, b in enumerate(bl):
            if b is not None:
                q[:, j] += robot.data.joint_pos[:, b]
        head_err.append((q - head_cmd.command[:, :4]).abs()[up].mean(0).cpu().numpy())
    now = (feet.data.found > 0)
    off = prev & ~now
    for e, f in torch.nonzero(off & up.unsqueeze(1)).tolist():
        lifts.append((t, e, f))
    prev = now
    for name, t0, t1 in STRETCHES:
        if t + dt >= t1 and name not in ups:
            ups[name] = float(up.float().mean())

res = {}
print(f"{a.ckpt}\n{a.task}: {N} robots, released up to {np.degrees(a.tilt):.0f} deg off upright, nudged {a.kick} m/s at {T_KICK:.0f} s" + (", then the emotions" if emo is not None else ""))
for name, t0, t1 in STRETCHES:
    L = [(t, e, f) for t, e, f in lifts if t0 <= t < t1]
    per = len(L) / N / (t1 - t0)
    robots = len({e for _, e, _ in L}) / N
    gaps = []
    by = {}
    for t, e, f in L:
        by.setdefault((e, f), []).append(t)
    for ts in by.values():
        gaps += list(np.diff(ts))
    gap = float(np.median(gaps)) if gaps else float("nan")
    res[name] = dict(up=ups.get(name, float(up.float().mean())), lifts_per_robot_s=per, robots_lifting=robots, median_gap_s=gap)
    print(f"  {name:14s} up {res[name]['up'] * 100:5.1f} %  foot lift-offs {per:5.2f} per robot per s, {robots * 100:5.1f} % of robots lifted a foot, "
          f"median {gap:.2f} s between one foot's lift-offs")
if per_emo:
    res["per_emotion"] = per_emo
    print("  per emotion: robots that fell during it; 90th percentile of the worst servo's ~2 s RMS torque, x rated (0.17 N m), per group:")
    for n_, d in per_emo.items():
        print(f"    {n_:11s} fell {d['fell']:3d}  " + "  ".join(f"{g} {v:.1f}" for g, v in d["heat"].items())
              + (f"   ankle goal-pos {np.mean(d['aerr']) * 1000:4.0f} mrad, jitter {np.mean(d['ajit']) * 1000:4.1f} mrad/step" if d.get("aerr") else ""))
if head_err:
    E = np.array(head_err)
    res["head_tracking_err_rad"] = dict(zip(("neck", "head_pitch", "head_yaw", "head_roll"), map(float, E.mean(0))))
    if rest_dev:
        d_ = torch.cat(rest_dev).numpy()
        print(f"  head at rest (no emotion): pitch goal off the command, 95th percentile {np.degrees(np.percentile(d_, 95)):.1f} deg, "
              f"max {np.degrees(d_.max()):.0f} deg, {100 * (d_ > np.radians(10)).mean():.1f} % of robot-ticks past 10 deg")
    print("  head tracking during the emotions, mean |error| (rad): " + ", ".join(f"{k} {v:.3f}" for k, v in res["head_tracking_err_rad"].items()))
if a.out:
    json.dump(res, open(a.out, "w"), indent=1)
