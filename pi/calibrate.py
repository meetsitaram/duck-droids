"""Calibrate the servos' zeros, one joint at a time, from the Xbox controller (or Enter on the keyboard): every other servo holds where it
is and only the joint being calibrated goes limp, so there's no doubt which one you're moving. Its angle prints twice a second, and the twin
on the PC shows it (`twin.py --remote <pi>` or `watch.py <pi>`).

Put the joint at its zero by a reference, not by eye:
  knee         thigh and shin flat on the table together (the knee bends both ways: there's no stop at straight)
  ankle        foot pressed flat on the table, shin upright
  hip roll     leg straight down, parallel to the body's centre line (from the front)
  hip pitch    leg straight down in line with the body (from the side), body upright
  hip yaw      foot pointing straight ahead
  head joints  head level and facing forward, beak shut

Then A (or Enter): that position becomes the joint's zero (its config 'centre'). B (or s + Enter): keep the old centre. The controller
buzzes on each. Each new centre is written to the config as soon as it's set (the old config kept as .bak), so a crash loses nothing.
The twin shows it: the joint being calibrated yellow, with what to do and its angle on screen, done ones green, the rest grey.

  systemctl --user stop duck-launcher; python calibrate.py; systemctl --user start duck-launcher
  python calibrate.py right_knee left_knee        only these
  python calibrate.py --dry-run                   show, write nothing
"""
import argparse
import json
import os
import select
import shutil
import signal
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from duck.telemetry import Publisher  # noqa: E402
from stand_test import GOAL_CURRENT, MODE_CURRENT_POSITION  # noqa: E402

K = 360 / 4096
ORDER = ['right_ankle', 'left_ankle', 'right_knee', 'left_knee', 'right_hip_pitch', 'left_hip_pitch',
         'right_hip_roll', 'left_hip_roll', 'right_hip_yaw', 'left_hip_yaw',
         'neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'beak']
HINT = {'ankle': 'foot pressed flat on the table, shin upright',
        'knee': 'thigh and shin flat on the table together',
        'hip_pitch': 'leg straight down in line with the body (from the side)',
        'hip_roll': 'leg straight down, square to the servo it hangs from (from the front)',
        'hip_yaw': 'foot pointing straight ahead',
        'neck_pitch': 'neck upright', 'head_pitch': 'head level', 'head_yaw': 'head facing forward',
        'head_roll': 'head level side to side', 'beak': 'beak shut'}


def hint(n):
    return next(v for k, v in HINT.items() if n.endswith(k))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('joints', nargs='*', help='default: every joint, ankles first, up to the head')
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--cap', type=int, default=500, help='mA for the held servos')
    ap.add_argument('--pad', default='evdev', help="evdev (the Xbox controller), or 'none' for the keyboard only")
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--done', nargs='*', default=[], help='joints already calibrated (shown green in the twin)')
    ap.add_argument('--max-change', type=float, default=20.0, help='deg: a bigger change needs A pressed twice (the joint was likely not at its zero)')
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    cfg = json.load(open(a.config))
    J = cfg['joints']
    joints = a.joints or [n for n in ORDER if n in J]
    for n in joints:
        if n not in J:
            raise SystemExit(f'no joint {n}: one of {", ".join(J)}')
    pad = None
    if a.pad != 'none':
        from duck.gamepad import open_pad
        pad = open_pad(a.pad)
    all_ids = sorted(j['id'] for j in J.values())
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    pub = Publisher()
    for i in all_ids:                                       # all held where they are
        p = bus.read(i, dxl.PRESENT_POSITION, signed=True)
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, a.cap)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
        bus.write(i, dxl.GOAL_POSITION, p & 0xFFFFFFFF)
        bus.write(i, dxl.TORQUE_ENABLE, 1)

    def answer():
        """'A', 'B' or None: the controller's A/B (on release of nothing else), or Enter / s + Enter on the keyboard"""
        if pad is not None:
            held = pad.state().held
            for b in ('A', 'B'):
                if b in held:
                    while b in pad.state().held:           # wait for the release, so one press is one answer
                        time.sleep(0.02)
                    return b
        if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
            return 'B' if sys.stdin.readline().strip().lower().startswith('s') else 'A'
        return None

    new = {}
    done = list(a.done)
    show = [n for n in ORDER if n in J and (n in joints or n in done)]

    def status(n, deg, warn=''):
        return dict(now=n, deg=round(deg, 1), step=f'{joints.index(n) + 1}/{len(joints)}', hint=hint(n), warn=warn,
                    done=[x for x in show if x in done], todo=[x for x in show if x not in done and x != n])

    def save():
        if a.dry_run or not new:
            return
        cur = json.load(open(a.config))
        for x, (_, c, _) in new.items():
            cur['joints'][x]['centre'] = c
        with open(a.config, 'w') as f:
            json.dump(cur, f, indent=1)
            f.write('\n')

    bak = a.config + time.strftime('.%Y%m%d-%H%M%S.bak')
    if not a.dry_run:
        shutil.copy(a.config, bak)
    warn = ''
    try:
        for k, n in enumerate(joints, 1):
            j = J[n]
            i = j['id']
            bus.write(i, dxl.TORQUE_ENABLE, 0)
            print(f'\n[{k}/{len(joints)}] {n} (ID {i}) is limp, the rest hold: put it at its zero, then A to set, B to keep', flush=True)
            if pad is not None:
                pad.rumble(150, 0.5)
            last, got = 0.0, None
            while got is None:
                raw = bus.sync_read(all_ids, dxl.PRESENT_POSITION[0], 4)
                ticks = {x: int.from_bytes(raw[x], 'little', signed=True) for x in all_ids}
                p = ticks[i]
                deg = ((p - j['centre'] + 2048) % 4096 - 2048) * K * j['direction']
                pub.send(ticks, calib=status(n, deg, warn))
                if time.monotonic() - last > 0.5:
                    last = time.monotonic()
                    print(f'  {n} {deg:+6.1f} deg', flush=True)
                got = answer()
                time.sleep(0.03)
            if got == 'A' and abs(deg) > a.max_change:
                print(f'  {n} reads {deg:+.1f} deg: more than {a.max_change:.0f} away from the old zero. Is it really at its zero? A again to set it anyway, B to keep', flush=True)
                if pad is not None:
                    pad.rumble(600, 1.0)
                got, warn = None, f'{deg:+.0f} deg from the old zero: really at zero? A again = set, B = keep'
                while got is None:
                    raw = bus.sync_read(all_ids, dxl.PRESENT_POSITION[0], 4)
                    pub.send({x: int.from_bytes(raw[x], 'little', signed=True) for x in all_ids}, calib=status(n, deg, warn))
                    got = answer()
                    time.sleep(0.03)
                warn = ''
            if got == 'A':
                new[n] = (j['centre'], p % 4096, deg)
                save()
                print(f'  set: {n} zero here, centre {j["centre"]} -> {p % 4096} ({deg:+.1f} deg)', flush=True)
                if pad is not None:
                    pad.rumble(300, 1.0)
            else:
                print(f'  kept: {n} centre {j["centre"]} (it read {deg:+.1f} deg)', flush=True)
                if pad is not None:
                    pad.rumble(80, 0.4)
            done.append(n)
            p = bus.read(i, dxl.PRESENT_POSITION, signed=True)   # hold it where it was left, then on to the next
            bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
            bus.write(i, GOAL_CURRENT, a.cap)
            bus.write(i, dxl.GOAL_POSITION, p & 0xFFFFFFFF)
            bus.write(i, dxl.TORQUE_ENABLE, 1)
    except KeyboardInterrupt:
        print('\nstopped')
    finally:
        for i in all_ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
            except dxl.DxlError:
                pass
        pub.close()
        bus.close()
        print('torque off')

    if not new:
        print('nothing changed')
        return
    print('\nnew zeros:')
    for n, (old, c, deg) in new.items():
        print(f'  {n:16s} centre {old} -> {c}   ({deg:+.1f} deg)')
    if a.dry_run:
        print('--dry-run: config not written')
        return
    print(f'written to {a.config} (the old one: {bak}). Copy it back to the repo: pi/config/dynamixel.json')


if __name__ == '__main__':
    main()
