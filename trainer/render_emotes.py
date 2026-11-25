"""A review reel of a stand policy performing microduck's 13 emotions in the physics simulator, each labelled with how many robots stayed up
through it, with the sounds muxed in.

  python render_emotes.py CHECKPOINT --task Mjlab-StandEmote-Flat-Milli-Dynamixel-Bam --out emotions_policy.mp4 [--envs 64] [--scale 1.0]

Run from the trainer's folder (milli-rl), its environment active. --envs robots (servo, friction and slop draws as in training; pushes off,
released upright) play the emotions one after another through the head_pose command; the reel shows one of them that stayed up the longest,
close up, rendered from its own simulated states (not a kinematic replay). The label says how many of the robots fell during each emotion.
Sounds: milli-lineup/pi/sounds/microduck/<name>.wav, Pollen Robotics, Apache-2.0.
The beak is locked in the training model (no joint, no servo: the policy never moves it); on the duck pi/emote.py drives it straight from each
emotion's "mouth" keyframes. The reel does the same: it turns the jaw about its hinge (the jaw body's origin, about y, as pi/twin.py does) to
BEAK_SHUT + mouth x (BEAK_OPEN - BEAK_SHUT), emote.py's mapping.
"""
import argparse
import os
import subprocess
import tempfile
import wave
from dataclasses import asdict

import json

import imageio.v2 as imageio
import imageio_ffmpeg
import mujoco
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

import mjlab_microduck.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab_microduck.tasks.emotion_head import EMOTIONS_DIR, load_emotions

ap = argparse.ArgumentParser()
ap.add_argument("ckpt")
ap.add_argument("--task", default="Mjlab-StandEmote-Flat-Milli-Dynamixel-Bam")
ap.add_argument("--out", default="emotions_policy.mp4")
ap.add_argument("--envs", type=int, default=64)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--settle", type=float, default=2.0, help="s standing before the first emotion")
ap.add_argument("--gap", type=float, default=1.0, help="s at home between emotions")
a = ap.parse_args()

cfg = load_env_cfg(a.task)
cfg.scene.num_envs = a.envs
cfg.seed = a.seed
torch.manual_seed(a.seed)
cfg.events.pop("push_robot", None)
cfg.events.pop("nudge", None)
cfg.events.pop("tip", None)
cfg.curriculum = {}
cfg.episode_length_s = 1000.0
rb = cfg.events["reset_base"].params["pose_range"]
rb["roll"] = rb["pitch"] = (0.0, 0.0)
hp = cfg.commands["head_pose"]
hp.ranges = tuple((0.0, 0.0) for _ in hp.ranges)
hp.resampling_time_range = (1000.0, 1000.0)
if hasattr(hp, "emote_prob"):
    hp.emote_prob = 0.0
env = RslRlVecEnvWrapper(ManagerBasedRlEnv(cfg=cfg, device="cuda:0"), clip_actions=load_rl_cfg(a.task).clip_actions)
runner = load_runner_cls(a.task)(env, asdict(load_rl_cfg(a.task)), device="cuda:0")
runner.load(a.ckpt, map_location="cuda:0")
policy = runner.get_inference_policy(device="cuda:0")
base = env.unwrapped
dt = base.step_dt
head_cmd = base.command_manager.get_term("head_pose")

emo = load_emotions()
BEAK_SHUT, BEAK_OPEN = 0.02, 0.35        # pi/emote.py


def beak_track(name, n):
    """The beak angle (rad) at each of n policy steps of this emotion, from its mouth keyframes, linearly interpolated as load_emotions does."""
    keys = json.load(open(os.path.join(EMOTIONS_DIR, name + ".json")))["keyframes"]
    t = np.array([float(k["t"]) for k in keys])
    mo = np.clip([float(k.get("mouth") or 0.0) for k in keys], 0.0, 1.0) * a.scale
    return BEAK_SHUT + np.interp(np.arange(n) * dt, t, mo) * (BEAK_OPEN - BEAK_SHUT)


plan = []                     # (name or None, frames (T,4))
plan.append((None, torch.zeros(int(a.settle / dt), 4)))
for n, q in emo.items():
    plan.append((n, q * a.scale))
    plan.append((None, torch.zeros(int(a.gap / dt), 4)))
names_per_step = sum([[n] * len(q) for n, q in plan], [])
seq = torch.cat([q for _, q in plan]).to("cuda:0")
beak = np.concatenate([beak_track(n, len(q)) if n else np.full(len(q), BEAK_SHUT) for n, q in plan])

obs, _ = env.reset()
N = a.envs
up = torch.ones(N, dtype=torch.bool, device="cuda:0")
fell_at = torch.full((N,), len(seq), device="cuda:0")
fell_in = {n: 0 for n in emo}
qs = []
for k in range(len(seq)):
    head_cmd._command[:] = seq[k]
    with torch.no_grad():
        obs, _, _, _ = env.step(policy(obs))
    newly = up & base.termination_manager.terminated
    if newly.any() and names_per_step[k]:
        fell_in[names_per_step[k]] += int(newly.sum())
    fell_at[newly] = k
    up &= ~base.termination_manager.terminated
    qs.append(base.sim.data.qpos.clone().cpu().numpy())
pick = int(torch.argmax(fell_at).item())
Q = np.array(qs)[:, pick]
print(f"recorded robot {pick} ({'up throughout' if fell_at[pick] == len(seq) else f'fell at step {int(fell_at[pick])}'}); "
      f"{int(up.sum())} of {N} up at the end")
for n, f in fell_in.items():
    print(f"  {n:11s} {'PASS' if f == 0 else 'FAIL'}  fell during it: {f} of {N}")

m = base.sim.mj_model
d = mujoco.MjData(m)
W, H = 720, 540
m.vis.global_.offwidth, m.vis.global_.offheight = max(W, m.vis.global_.offwidth), max(H, m.vis.global_.offheight)
r = mujoco.Renderer(m, H, W)
cam = mujoco.MjvCamera()
cam.distance, cam.azimuth, cam.elevation = 0.55, 145, -12
try:
    font, small = ImageFont.truetype("arial.ttf", 26), ImageFont.truetype("arial.ttf", 18)
except OSError:
    font = small = ImageFont.load_default()
frames = []
look = None
trunk = next(i for i in range(m.nbody) if m.body(i).name.endswith("trunk_base"))
jaw = next(i for i in range(m.nbody) if m.body(i).name.endswith("jaw"))
jaw_q0 = m.body_quat[jaw].copy()
for k in range(len(Q)):
    d.qpos[:] = Q[k]
    turn = np.zeros(4)
    mujoco.mju_axisAngle2Quat(turn, np.array([0.0, 1.0, 0.0]), beak[k])
    mujoco.mju_mulQuat(m.body_quat[jaw], jaw_q0, turn)
    mujoco.mj_forward(m, d)
    tgt = d.subtree_com[trunk].copy()
    look = tgt if look is None else 0.9 * look + 0.1 * tgt
    cam.lookat[:] = look
    r.update_scene(d, cam)
    im = Image.fromarray(r.render())
    dr = ImageDraw.Draw(im)
    n = names_per_step[k]
    if n:
        dr.text((16, 12), n, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
        dr.text((16, 46), f"{N - fell_in[n]} of {N} robots stayed up", fill=(230, 230, 230), font=small, stroke_width=2, stroke_fill=(0, 0, 0))
    dr.text((16, H - 30), "policy in the physics sim, BAM XL330 servos, backlash and sag, pushes off; beak from the keyframes", fill=(220, 220, 220), font=small, stroke_width=2, stroke_fill=(0, 0, 0))
    frames.append(np.asarray(im))

fps = int(round(1 / dt))
audio, rate = np.zeros(int(len(Q) * dt * 48000), dtype=np.int16), 48000
k0 = 0
for n, q in plan:
    if n:
        p = os.path.join(EMOTIONS_DIR, n + ".wav")
        with wave.open(p) as w:
            rate = w.getframerate()
            s = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        i = int(k0 * dt * rate)
        audio[i:i + len(s)] = s[:max(0, len(audio) - i)]
    k0 += len(q)
tmp = tempfile.mkdtemp()
v, wv = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
imageio.mimsave(v, frames, fps=fps, codec="libx264", quality=7, macro_block_size=1)
with wave.open(wv, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(audio.tobytes())
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", v, "-i", wv, "-c:v", "copy", "-c:a", "aac", "-shortest", a.out], check=True)
print(a.out, f"{len(Q) * dt:.0f} s")
