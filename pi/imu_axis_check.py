"""Which way the IMU's axes point in the duck, and where level is: sets imu_to_robot in config/dynamixel.json.

Torque comes on with every joint held exactly where it is (nothing moves; current capped as stand_test.py), so the duck is one stiff piece.
Then, in --secs (40 s): keep it still and upright for the first 3 s, then tip the whole duck BEAK DOWN about 20 deg and hold 3-5 s, back
upright, then onto ITS OWN LEFT SIDE about 20 deg and hold 3-5 s, back upright. The torque then goes off.

The still start is level (the torso upright): that becomes the robot's z. The first held tip is forward (+x), the second the robot's left
(+y), each from the change in gravity. It prints the matrix and, with --write, puts it in the config (then copy the config to the Pi).

  python imu_axis_check.py                 on the Pi, the duck sitting with its torso upright
  python imu_axis_check.py --write         and save it
It streams to the PC's twin as it goes (python twin.py --remote <pi>).
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import Bno085, load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from stand_test import CAP, GOAL_CURRENT, HEAD, BEAK, LED, MODE_CURRENT_POSITION, POSITION_D  # noqa: E402


def held_tilts(t, G, W, g0, min_deg=10.0, min_s=0.8):
    """Stretches where the duck is held still (gyro under 0.6 rad/s) at least min_deg off the start, at least min_s long, in order."""
    off = np.degrees(np.arccos(np.clip(G @ g0, -1, 1)))
    still = np.linalg.norm(W, axis=1) < 0.6
    on = (off > min_deg) & still
    out, i = [], 0
    while i < len(t):
        if on[i]:
            j = i
            while j + 1 < len(t) and on[j + 1]:
                j += 1
            if t[j] - t[i] >= min_s:
                out.append((t[i], t[j], G[i:j + 1].mean(0), off[i:j + 1].mean()))
            i = j + 1
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--secs', type=float, default=40.0)
    ap.add_argument('--cap', type=int, default=800, help='leg current cap, mA (head 600, beak 300)')
    ap.add_argument('--gain', type=int, default=1500, help='position P while holding: stiff, so the duck tips as one piece')
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--max-volts', type=float, default=6.5)
    ap.add_argument('--write', action='store_true', help='save the result as imu_to_robot in --config')
    ap.add_argument('--telemetry', type=int, default=9100)
    a = ap.parse_args()

    cfg = load_config(a.config)
    raw_cfg = json.load(open(a.config, encoding='utf-8'))
    names = list(cfg['joints'])
    ids = [cfg['joints'][n]['id'] for n in names]
    imu = Bno085(dict(cfg, imu_to_robot=np.eye(3).tolist()))      # the sensor's own axes: that is what is being found
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
    if not a.min_volts <= volts <= a.max_volts:
        raise SystemExit(f'supply {volts:.1f} V: needs {a.min_volts}-{a.max_volts} V')
    pub = None
    if a.telemetry:
        from duck.telemetry import Publisher
        pub = Publisher(a.telemetry)
    for n, i in zip(names, ids):
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, CAP['head'] if n in HEAD else CAP['beak'] if n in BEAK else a.cap)
        bus.write(i, dxl.POSITION_P, a.gain if n not in BEAK else 600)
        bus.write(i, POSITION_D, 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
    raw = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
    here = [int.from_bytes(raw[i], 'little', signed=True) for i in ids]
    bus.sync_write(ids, dxl.GOAL_POSITION, here)                # the goal is where each joint is: nothing moves
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)
        bus.write(i, LED, 1)
    print(f'supply {volts:.1f} V. Holding every joint where it is, {a.secs:.0f} s: still 3 s, BEAK DOWN 20 deg hold 3-5 s, upright, '
          f'ITS LEFT SIDE DOWN 20 deg hold 3-5 s, upright.', flush=True)
    T, G, W = [], [], []
    t0 = time.monotonic()
    nxt = t0
    try:
        while (t := time.monotonic() - t0) < a.secs:
            gyro, grav = imu.read()
            T.append(t); G.append(grav); W.append(gyro)
            if pub and len(T) % 2 == 0:
                r = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
                pub.send({i: int.from_bytes(r[i], 'little', signed=True) for i in ids}, grav, gyro)
            if len(T) % 50 == 0:
                tilt = math.degrees(math.acos(max(-1.0, min(1.0, -float(grav[2])))))
                print(f'{t:4.0f} s  gravity {grav[0]:+.2f} {grav[1]:+.2f} {grav[2]:+.2f}  ({tilt:4.1f} deg)', flush=True)
            nxt += 0.02
            time.sleep(max(0.0, nxt - time.monotonic()))
    except KeyboardInterrupt:
        print('Ctrl-C')
    finally:
        for i in ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, LED, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
            except dxl.DxlError:
                pass
        bus.close()
        imu.close()
        if pub:
            pub.close()
    print(f'torque off. IMU: {imu.errors} bad packets, {imu.restarts} restarts')

    T, G, W = np.array(T), np.array(G), np.array(W)
    G = G / np.linalg.norm(G, axis=1, keepdims=True)
    g0 = G[T < 2.5].mean(0)
    g0 /= np.linalg.norm(g0)
    tips = held_tilts(T, G, W, g0)
    print(f'still start: gravity {np.round(g0, 3)} in the sensor frame ({math.degrees(math.acos(-g0[2])):.1f} deg off its own z)')
    for s, e, g, deg in tips:
        print(f'held tip {s:4.1f}-{e:4.1f} s: {deg:4.1f} deg, gravity {np.round(g, 3)}')
    if len(tips) < 2:
        print('need 2 held tips (beak down, then its left side down), each held still 1 s or more, 10 deg or more: run it again')
        return
    up = -g0                                                    # the robot's z, in the sensor frame
    horiz = lambda v: (v - (v @ up) * up) / np.linalg.norm(v - (v @ up) * up)
    fwd = horiz(tips[0][2])                                     # beak down: gravity swings toward the front, +x
    left_meas = horiz(tips[1][2])                               # its left side down: toward +y
    left = np.cross(up, fwd)
    agree = math.degrees(math.acos(np.clip(left @ left_meas, -1, 1)))
    R = np.array([fwd, left, up])                               # rows: the robot's x, y, z in the sensor frame; robot = R @ sensor
    print(f'forward is sensor {np.round(fwd, 2)}, left is sensor {np.round(left, 2)} (the left tip agrees within {agree:.0f} deg)')
    print('imu_to_robot =', json.dumps(np.round(R, 4).tolist()))
    print('check: the still start now reads', np.round(R @ g0, 3), '(should be 0 0 -1); beak down reads', np.round(R @ tips[0][2], 2),
          '(+x); left down', np.round(R @ tips[1][2], 2), '(+y)')
    if agree > 30:
        print('the two tips disagree by more than 30 deg: not saved. Check the order (beak down first) and run it again')
        return
    if a.write:
        raw_cfg['imu_to_robot'] = np.round(R, 4).tolist()
        raw_cfg.setdefault('notes', {})['imu_to_robot'] = (f'measured by imu_axis_check.py {time.strftime("%Y-%m-%d")}: torso upright sitting = level, '
                                                           f'beak-down tip = +x, left-side tip = +y (agreed within {agree:.0f} deg)')
        json.dump(raw_cfg, open(a.config, 'w', encoding='utf-8'), indent=1)
        print('saved to', a.config)


if __name__ == '__main__':
    main()
