"""microduck's emotions on milli: each sound with the head, neck and beak motion Pollen made for it, in time.

  python emote.py --list                         the emotions, how long each runs, and what milli can't follow
  python emote.py yes --preview                  the model in a window, with the sound, again and again (close the window to stop)
  python emote.py --all --preview                every emotion in turn
  python emote.py laugh --video laugh.mp4        a video of the model, with the sound in it
  python emote.py yes                            on the duck: motion.py's playback (eases in, plays, eases back, torque off) with the sound

The motions are pi/sounds/microduck/<name>.json, from Pollen Robotics (Apache-2.0, pi/sounds/README.md): keyframes in seconds, offsets
from the standing pose in radians. milli has microduck's head joints with the same names, axes and signs (neck_pitch negative leans the
neck forward, head_pitch positive tips the nose down), so they map straight across:
  neck, head_pitch, head_yaw, head_roll  ->  neck_pitch, head_pitch, head_yaw, head_roll, added to the config's home pose
  mouth 0 (shut) to 1 (open)             ->  beak, BEAK_SHUT to BEAK_OPEN rad (just short of shut, and under the jaw's 0.39 stop)
Every joint is kept inside the config's limits (pi/config/dynamixel.json): the head roll stops at +-0.24 (curious and mock ask up to
0.44), the neck at its limits. Pollen's body pitch and height (the legs leaning the body), and devastated's "sit", are left out: only the
neck, head and beak move, and the legs aren't commanded at all on the duck. Standing, devastated's neck and head pitch are scaled
by SIT_SCALE (its full droop brings the head to the floor; --full for all of it). On the duck, big or fast neck moves shift the weight forward
or back (sad, devastated): someone steadies it, as for any motion.py playback. --scale shrinks every move.
"""
import argparse
import json
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import sound  # noqa: E402

EMOTIONS = sound.SOUNDS
HEAD_MAP = {'neck': 'neck_pitch', 'head_pitch': 'head_pitch', 'head_yaw': 'head_yaw', 'head_roll': 'head_roll'}
JOINTS = ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'beak']
BEAK_SHUT, BEAK_OPEN = 0.02, 0.35            # rad: stand_test.py's just-short-of-shut, and under the jaw's stop (spec beak_max 0.39)
FPS = 50
FULL = [False]                               # --full, set once in main()
SIT_SCALE = 0.6       # devastated sits first on microduck; standing, its full neck droop (-1.5) brings the head to the floor: 0.6 keeps ~6 cm
TAIL = 0.6                                   # s of rest after a motion, before the next or the loop


def names():
    return sorted(f[:-5] for f in os.listdir(EMOTIONS) if f.endswith('.json'))


def load_config(path=None):
    return json.load(open(path or os.path.join(HERE, 'config', 'dynamixel.json')))


def track(name, cfg, scale=1.0, full=False):
    """The emotion as joint angles over time: [(t, {joint: rad})], and what had to be clipped or left out."""
    keys = json.load(open(os.path.join(EMOTIONS, name + '.json')))['keyframes']
    sits = any(k.get('skill') == 'sit' for k in keys)
    home, lim = cfg['home'], cfg.get('limits', {})
    out, clipped, dropped = [], {}, set()
    for k in keys:
        q = {}
        for src, j in HEAD_MAP.items():
            f = SIT_SCALE if sits and not full and j in ('neck_pitch', 'head_pitch') else 1.0
            v = home.get(j, 0.0) + scale * f * float(k.get(src) or 0.0)
            if j in lim and not lim[j][0] <= v <= lim[j][1]:
                c = min(max(v, lim[j][0]), lim[j][1])
                clipped[j] = max(clipped.get(j, 0.0), abs(v - c))
                v = c
            q[j] = v
        q['beak'] = BEAK_SHUT + min(max(float(k.get('mouth') or 0.0), 0.0), 1.0) * scale * (BEAK_OPEN - BEAK_SHUT)
        for src in ('body_pitch', 'body_z'):
            if abs(float(k.get(src) or 0.0)) > 1e-3:
                dropped.add(src)
        if any(abs(float(v)) > 1e-3 for v in (k.get('twist') or [])):
            dropped.add('twist')
        if k.get('skill'):
            dropped.add(f"skill {k['skill']}" + ('' if full else f' (neck and head pitch x{SIT_SCALE}, standing)'))
        out.append((float(k['t']), q))
    return out, clipped, dropped


def sample(tr, t):
    if t <= tr[0][0]:
        return tr[0][1]
    for (ta, qa), (tb, qb) in zip(tr, tr[1:]):
        if ta <= t <= tb:
            w = (t - ta) / max(tb - ta, 1e-9)
            return {n: qa[n] + w * (qb[n] - qa[n]) for n in qa}
    return tr[-1][1]


def full_pose(cfg, q):
    """The config's home pose for the legs, the emotion's for the head."""
    p = dict(cfg['home'])
    p.update(q)
    return p


def describe(name, cfg, scale=1.0):
    tr, clipped, dropped = track(name, cfg, scale, FULL[0])
    s = f'{name:11s} motion {tr[-1][0]:4.1f} s, sound {sound.duration(name):4.1f} s'
    if clipped:
        s += '; clipped to the limits: ' + ', '.join(f'{j} by {math.degrees(v):.0f} deg' for j, v in clipped.items())
    if dropped:
        s += '; left out: ' + ', '.join(sorted(dropped))
    return s


def preview(todo, cfg, scale):
    import mujoco.viewer
    import twin
    m, d, adr = twin.load_model(cfg, soles=False)
    tracks = [(n, track(n, cfg, scale, FULL[0])[0]) for n in todo]
    with mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.55, 150, -10
        i = 0
        while v.is_running():
            n, tr = tracks[i % len(tracks)]
            print(describe(n, cfg, scale), flush=True)
            dur = tr[-1][0] + TAIL
            sound.play(n)
            t0 = time.monotonic()
            while v.is_running() and time.monotonic() - t0 < dur:
                with v.lock():
                    twin.pose(m, d, adr, full_pose(cfg, sample(tr, time.monotonic() - t0)))
                    v.cam.lookat[:] = d.subtree_com[1]
                v.sync()
                time.sleep(1 / 60)
            i += 1
    sound.stop()


def video(todo, cfg, scale, out, size=(640, 480)):
    """Offscreen frames of the model, captioned, with the sounds muxed in (ffmpeg from imageio-ffmpeg)."""
    import subprocess
    import wave
    import imageio.v2 as imageio
    import imageio_ffmpeg
    import mujoco
    import numpy as np
    import twin
    from PIL import Image, ImageDraw, ImageFont
    m, d, adr = twin.load_model(cfg, soles=False)
    m.vis.global_.offwidth, m.vis.global_.offheight = max(size[0], 640), max(size[1], 480)
    r = mujoco.Renderer(m, size[1], size[0])
    cam = mujoco.MjvCamera()
    cam.distance, cam.azimuth, cam.elevation = 0.55, 150, -10
    try:
        font = ImageFont.truetype('arial.ttf', 22)
    except OSError:
        font = ImageFont.load_default()
    frames, audio, rate = [], [], 48000
    for n in todo:
        tr = track(n, cfg, scale, FULL[0])[0]
        dur = max(tr[-1][0], sound.duration(n)) + TAIL
        with wave.open(sound.path(n)) as w:
            rate = w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
            if w.getnchannels() > 1:
                a = a.reshape(-1, w.getnchannels())[:, 0]
        nf = int(round(dur * FPS))
        clip = np.zeros(int(round(nf / FPS * rate)), dtype=np.int16)
        clip[:min(len(a), len(clip))] = a[:len(clip)]
        audio.append(clip)
        for k in range(nf):
            twin.pose(m, d, adr, full_pose(cfg, sample(tr, k / FPS)))
            cam.lookat[:] = d.subtree_com[1]
            r.update_scene(d, cam)
            im = Image.fromarray(r.render())
            ImageDraw.Draw(im).text((14, 10), n, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
            frames.append(np.asarray(im))
    tmp = tempfile.mkdtemp()
    silent, wav = os.path.join(tmp, 'v.mp4'), os.path.join(tmp, 'a.wav')
    imageio.mimsave(silent, frames, fps=FPS, codec='libx264', quality=7, macro_block_size=1)
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.concatenate(audio).tobytes())
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-c:v', 'copy', '-c:a', 'aac',
                    '-shortest', out], check=True)
    print(f'{out}: {len(frames) / FPS:.1f} s, {", ".join(todo)}')


def on_duck(name, cfg, scale, extra):
    """motion.py's playback of the head-only track, with the sound started as the motion starts."""
    tr = track(name, cfg, scale, FULL[0])[0]
    path = os.path.join(tempfile.mkdtemp(), f'emote_{name}.json')
    json.dump({'about': f'microduck emotion {name} (Pollen Robotics, Apache-2.0), mapped by emote.py', 'hz': FPS, 'joints': JOINTS,
               'frames': [[round(t, 3)] + [round(q[j], 5) for j in JOINTS] for t, q in tr]}, open(path, 'w'))
    import motion
    sys.argv = ['motion.py', 'play', path, '--sound', name, '--ease-back', '2'] + extra
    motion.main()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name', nargs='?', help='an emotion (--list for them)')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--all', action='store_true', help='every emotion in turn (--preview or --video)')
    ap.add_argument('--preview', action='store_true', help='the model in a window, with the sound: no servos')
    ap.add_argument('--video', help='write an mp4 of the model, with the sound')
    ap.add_argument('--scale', type=float, default=1.0, help='every move times this: 0.5 is half as big')
    ap.add_argument('--full', action='store_true', help="devastated's full droop (its head reaches the floor standing)")
    ap.add_argument('--config', default=None)
    a, extra = ap.parse_known_args()
    cfg = load_config(a.config)
    FULL[0] = a.full
    if a.list:
        for n in names():
            print(describe(n, cfg, a.scale))
        return
    todo = names() if a.all else [a.name] if a.name else None
    if not todo:
        ap.error('name an emotion, or --all, or --list')
    for n in todo:
        if n not in names():
            ap.error(f'no emotion {n!r}: one of {", ".join(names())}')
    if a.video:
        video(todo, cfg, a.scale, a.video)
    elif a.preview:
        preview(todo, cfg, a.scale)
    else:
        if len(todo) > 1:
            ap.error('on the duck, one emotion at a time')
        on_duck(todo[0], cfg, a.scale, extra)


if __name__ == '__main__':
    main()
