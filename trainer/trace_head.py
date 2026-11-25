"""One emotion on a stand policy, step by step: the head command against the policy's targets and the angles reached (mean over robots).
  python trace_head.py CHECKPOINT [--task ...] [--emotion sad] [--envs 32]      (from milli-rl, its environment active)"""
import argparse
from dataclasses import asdict

import torch

import mjlab_microduck.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab_microduck.tasks.emotion_head import load_emotions

ap = argparse.ArgumentParser()
ap.add_argument("ckpt")
ap.add_argument("--task", default="Mjlab-StandEmote-Flat-Milli-Dynamixel-Bam")
ap.add_argument("--emotion", default="sad")
ap.add_argument("--envs", type=int, default=32)
ap.add_argument("--every", type=float, default=0.5)
a = ap.parse_args()
cfg = load_env_cfg(a.task)
cfg.scene.num_envs = a.envs
for k in ("push_robot", "nudge"):
    cfg.events.pop(k, None)
cfg.curriculum = {}
cfg.episode_length_s = 1000
rb = cfg.events["reset_base"].params["pose_range"]
rb["roll"] = rb["pitch"] = (0, 0)
hp = cfg.commands["head_pose"]
hp.ranges = tuple((0, 0) for _ in hp.ranges)
hp.resampling_time_range = (1000, 1000)
if hasattr(hp, "emote_prob"):
    hp.emote_prob = 0
env = RslRlVecEnvWrapper(ManagerBasedRlEnv(cfg=cfg, device="cuda:0"), clip_actions=load_rl_cfg(a.task).clip_actions)
r = load_runner_cls(a.task)(env, asdict(load_rl_cfg(a.task)), device="cuda:0")
r.load(a.ckpt, map_location="cuda:0")
pol = r.get_inference_policy(device="cuda:0")
b = env.unwrapped
rob = b.scene["robot"]
hc = b.command_manager.get_term("head_pose")
J = ("neck_pitch", "head_pitch", "head_yaw", "head_roll")
names = list(rob.joint_names)
hid = [names.index(n) for n in J]
bl = [names.index(f"passive_{n}_backlash") if f"passive_{n}_backlash" in names else None for n in J]
seq = load_emotions()[a.emotion].to("cuda:0")
obs, _ = env.reset()
for _ in range(100):
    with torch.no_grad():
        obs, *_ = env.step(pol(obs))
every = max(1, int(a.every / b.step_dt))
print(f"{a.emotion}: command / target / reached, rad (neck, head pitch, yaw, roll), mean of {a.envs} robots")
for k in range(len(seq) + 25):
    hc._command[:] = seq[min(k, len(seq) - 1)]
    with torch.no_grad():
        obs, *_ = env.step(pol(obs))
    if k % every == 0:
        q = rob.data.joint_pos[:, hid] - rob.data.default_joint_pos[:, hid]
        for j, i in enumerate(bl):
            if i is not None:
                q[:, j] += rob.data.joint_pos[:, i]
        tg = rob.data.joint_pos_target[:, hid] - rob.data.default_joint_pos[:, hid]
        c = seq[min(k, len(seq) - 1)]
        f = lambda v: " ".join(f"{x:+.2f}" for x in v)
        print(f"t {k * b.step_dt:4.1f}  cmd {f(c.tolist())}  target {f(tg.mean(0).tolist())}  got {f(q.mean(0).tolist())}")
