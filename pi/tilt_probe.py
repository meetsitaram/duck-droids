"""Can the joints feel a tilt? No policy: the legs ease the duck up from sitting to the trained standing pose and hold it there, while you hold
the duck and tilt it, following the prompts. Every tick logs each joint's angle, its goal and its current; at the end a table shows, per tilt,
how far each joint moved off its goal and how its current changed, against the upright hold and against the reading noise.

Why: a blind policy sees only joint angles, speeds and its own last goals. With the feet flat, a tilt changes the joints' load (the ankles,
knees and hips hold the weight further forward or back), so a soft servo (P 800: about 2.2 N m/rad) gives way a little and draws more current.
This measures whether that is big enough to see over the gear play (+-1 deg) and the noise.

  python tilt_probe.py                         through the Waveshare board's USB-C (jumpers at B), the port found by itself
  python tilt_probe.py --hold 6 --tilts forward,back,left,right
  python tilt_probe.py --port socket://127.0.0.1:9000 --max-volts 9     against the simulator (sim/server.py): plumbing only, nobody tilts it

Tilt by hand about the feet, keeping both soles on the floor (a heel or toe lifting changes everything), about 10 deg, and hold still at
each prompt. Safety as stand_test.py: current caps, torque on where each joint is, a hardware error, a low supply or Ctrl-C eases it back
down to sitting before the torque goes off.
"""
import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from stand_test import CAP, GOAL_CURRENT, HEAD, HW_ERROR, LED, LEGS, MODE_CURRENT_POSITION, POSITION_D, at  # noqa: E402

K = 2 * math.pi / dxl.TICKS_PER_REV
RATE = 50.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--rise', type=float, default=10.0)
    ap.add_argument('--lower', type=float, default=10.0)
    ap.add_argument('--hold', type=float, default=6.0, help='seconds at each prompt; the first 2 s of each are a settle, not measured')
    ap.add_argument('--tilts', default='forward,back,left,right', help='the order of the tilts, each between upright holds')
    ap.add_argument('--cap', type=int, default=800)
    ap.add_argument('--gain', type=int, default=800, help='leg position P, as the policies trained at')
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--max-volts', type=float, default=6.0)
    ap.add_argument('--log', default=os.path.join(HERE, 'tilt_probe_log.csv'))
    a = ap.parse_args()

    cfg = load_config(a.config)
    home = json.load(open(os.path.join(HERE, 'sim', 'model', 'home.json')))['joint_pos']     # the trained standing pose
    J = LEGS                                                # the legs only; the head stays limp, as stand_test.py without --show
    port = find_port() if a.port == 'auto' else a.port
    bus = dxl.Bus(port, timeout=0.05)
    ids = [cfg['joints'][n]['id'] for n in J]
    sign = {n: cfg['joints'][n]['direction'] for n in J}
    for i in ids:
        if not bus.ping(i):
            raise SystemExit(f'servo {i} does not answer')
    volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
    print(f'supply {volts:.1f} V')
    if not a.min_volts <= volts <= a.max_volts:
        raise SystemExit(f'{volts:.1f} V: needs {a.min_volts}-{a.max_volts} V')
    for n, i in zip(J, ids):
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, a.cap)
        bus.write(i, dxl.POSITION_P, a.gain)
        bus.write(i, POSITION_D, 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)

    def read_state():
        raw = bus.sync_read(ids, 126, 10)                  # current 2, velocity 4, position 4
        cur, pos = {}, {}
        for n, i in zip(J, ids):
            b = raw[i]
            cur[n] = int.from_bytes(b[0:2], 'little', signed=True) * sign[n]     # in the joint's direction, as the angle
            pos[n] = int.from_bytes(b[6:10], 'little', signed=True)
        return cur, pos

    _, p0 = read_state()
    q0 = {n: ((p0[n] - cfg['joints'][n]['centre'] + 2048) % 4096 - 2048) * K * sign[n] for n in J}
    angle = lambda pos, n: q0[n] + (pos[n] - p0[n]) * sign[n] * K
    goal_ticks = lambda q: [p0[n] + int(round((q[n] - q0[n]) * sign[n] / K)) for n in J]
    stand = {n: home.get(n, 0.0) for n in J}

    script = []                                             # (label, seconds): upright between the tilts
    for tilt in a.tilts.split(','):
        script += [('upright', a.hold), (tilt, a.hold)]
    script += [('upright', a.hold)]

    bus.sync_write(ids, dxl.GOAL_POSITION, [p0[n] for n in J])
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)
        bus.write(i, LED, 1)
    log = open(a.log, 'w', newline='')
    w = csv.writer(log)
    w.writerow(['t', 'phase', 'label', 'volts'] + [f'{n}_{k}' for n in J for k in ('goal', 'q', 'mA')])
    rows, stopped = [], None
    t0 = time.monotonic()
    nxt, tick, last_label = t0, 0, None
    total_hold = sum(s for _, s in script)
    try:
        while True:
            t = time.monotonic() - t0
            if t < a.rise:
                phase, label = 'rise', ''
                _, g = at([(a.rise, stand)], q0, t)
            elif t < a.rise + total_hold:
                phase, g = 'hold', stand
                u = t - a.rise
                for label, secs in script:
                    if u < secs:
                        break
                    u -= secs
                if label != last_label:
                    last_label = label
                    print(f'\n>>> {label.upper()} now: {"hold it upright" if label == "upright" else "tilt it " + label + " about 10 deg, both soles on the floor"} '
                          f'({secs:.0f} s)', flush=True)
                    sys.stdout.write('\a')
                settled = u > 2.0
            else:
                break
            bus.sync_write(ids, dxl.GOAL_POSITION, goal_ticks(g))
            cur, pos = read_state()
            if tick % 25 == 0:
                volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
                raw = bus.sync_read(ids, HW_ERROR[0], 1)
                hw = {n: raw[i][0] for n, i in zip(J, ids)}
                if any(hw.values()) or volts < a.min_volts:
                    stopped = 'hardware error ' + str({n: v for n, v in hw.items() if v}) if any(hw.values()) else f'supply {volts:.1f} V'
                    break
            q = {n: angle(pos, n) for n in J}
            w.writerow([round(t, 3), phase, label, volts] + [v for n in J for v in (round(g[n], 4), round(q[n], 4), cur[n])])
            if phase == 'hold' and settled:
                rows.append((label, {n: math.degrees(q[n] - g[n]) for n in J}, dict(cur)))
            tick += 1
            nxt += 1 / RATE
            time.sleep(max(0.0, nxt - time.monotonic()))
    except KeyboardInterrupt:
        stopped = 'Ctrl-C'
    finally:
        try:
            _, pos = read_state()
            here = {n: angle(pos, n) for n in J}
            print(f'\neasing back down over {a.lower:.0f} s' + (f' (stopped: {stopped})' if stopped else ''), flush=True)
            t1 = time.monotonic()
            while (qb := at([(a.lower, q0)], here, time.monotonic() - t1)[1]) is not None:
                bus.sync_write(ids, dxl.GOAL_POSITION, goal_ticks(qb))
                time.sleep(1 / RATE)
            time.sleep(0.5)
        finally:
            for i in ids:
                try:
                    bus.write(i, dxl.TORQUE_ENABLE, 0)
                    bus.write(i, LED, 0)
                    bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
                except dxl.DxlError:
                    pass
            log.close()
            bus.close()
    report(rows, J)
    print('log:', a.log)


def report(rows, J):
    """Per tilt, each joint's offset from its goal (deg) and its current (mA), as the change from the upright holds, with the upright noise."""
    if not rows:
        print('nothing measured')
        return
    by = {}
    for label, off, cur in rows:
        by.setdefault(label, []).append([off[n] for n in J] + [cur[n] for n in J])
    by = {k: np.array(v, float) for k, v in by.items()}
    up = by.get('upright')
    if up is None:
        print('no upright hold measured')
        return
    base, noise = up.mean(0), up.std(0)
    n = len(J)
    print('\nchange from upright (offset from goal in deg, then current in mA); "noise" is the upright hold\'s spread. Over ~3x noise is a signal.')
    print(f'{"joint":16s} {"noise deg":>9s} ' + ' '.join(f'{k:>10s}' for k in by if k != 'upright') + f' {"noise mA":>9s} ' + ' '.join(f'{k:>10s}' for k in by if k != 'upright'))
    for j, name in enumerate(J):
        degs = ' '.join(f'{by[k][:, j].mean() - base[j]:+10.2f}' for k in by if k != 'upright')
        mas = ' '.join(f'{by[k][:, n + j].mean() - base[n + j]:+10.0f}' for k in by if k != 'upright')
        print(f'{name:16s} {noise[j]:9.2f} {degs} {noise[n + j]:9.0f} {mas}')


if __name__ == '__main__':
    main()
