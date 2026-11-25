"""Check the knee and ankle calibration by eye, the duck held up in the air: the knees and ankles curl in, hold, stretch out straight, hold,
then curl back and the torque goes off. The hips hold where they are. At each hold it prints every joint's goal, where it got to and its
current, and it streams to the twin (`twin.py --remote <pi>`) the whole time, so both legs can be compared on the PC.

  systemctl --user stop duck-launcher; python leg_sweep.py; systemctl --user start duck-launcher
  python leg_sweep.py --curl-knee 50 --curl-ankle 40 --move 5
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from duck.telemetry import Publisher  # noqa: E402
from stand_test import GOAL_CURRENT, LEGS, MODE_CURRENT_POSITION, POSITION_D  # noqa: E402

K = 2 * math.pi / 4096
SIDE = {'left': 1, 'right': -1}       # the standing pose bends the left knee and ankle +, the right ones -


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--curl-knee', type=float, default=55.0, help='deg')
    ap.add_argument('--curl-ankle', type=float, default=50.0, help='deg')
    ap.add_argument('--move', type=float, default=4.0, help='seconds for each move')
    ap.add_argument('--hold', type=float, default=2.0, help='seconds at each pose')
    ap.add_argument('--cap', type=int, default=800, help='mA')
    ap.add_argument('--gain', type=int, default=800)
    a = ap.parse_args()
    cfg = load_config(a.config)
    J = cfg['joints']
    legs = [n for n in LEGS if n in J]
    moving = [n for n in legs if n.endswith(('knee', 'ankle'))]
    all_ids = sorted(j['id'] for j in J.values())
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    pub = Publisher()

    def read_all():
        raw = bus.sync_read(all_ids, dxl.PRESENT_POSITION[0], 4)
        return {i: int.from_bytes(raw[i], 'little', signed=True) for i in all_ids}

    def angle(n, p):
        return ((p - J[n]['centre'] + 2048) % 4096 - 2048) * K * J[n]['direction']

    p0 = read_all()
    q0 = {n: angle(n, p0[J[n]['id']]) for n in legs}

    def tick(n, q):                    # from the first reading, so no joint can jump a turn at the 0/4095 wrap
        return p0[J[n]['id']] + int(round((q - q0[n]) * J[n]['direction'] / K))

    ids = [J[n]['id'] for n in legs]
    for n in legs:
        i = J[n]['id']
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, a.cap)
        bus.write(i, dxl.POSITION_P, a.gain)
        bus.write(i, POSITION_D, 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
    bus.sync_write(ids, dxl.GOAL_POSITION, [tick(n, q0[n]) for n in legs])
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)

    def pose(knee, ankle):
        g = dict(q0)
        for n in moving:
            s = SIDE[n.split('_')[0]]
            g[n] = s * math.radians(knee if n.endswith('knee') else ankle)
        return g

    def go(goal, secs, label):
        start = dict(cur)
        t0 = time.monotonic()
        while (t := time.monotonic() - t0) < secs:
            f = 0.5 - 0.5 * math.cos(math.pi * min(1.0, t / secs))
            g = {n: start[n] + (goal[n] - start[n]) * f for n in legs}
            bus.sync_write(ids, dxl.GOAL_POSITION, [tick(n, g[n]) for n in legs])
            pub.send(read_all())
            time.sleep(0.02)
        cur.update(goal)
        bus.sync_write(ids, dxl.GOAL_POSITION, [tick(n, goal[n]) for n in legs])
        t0 = time.monotonic()
        while time.monotonic() - t0 < a.hold:
            pub.send(read_all())
            time.sleep(0.05)
        r = bus.sync_read(ids, 126, 10)
        print(f'\n{label}: joint            goal    got   off    mA')
        for n in moving:
            b = r[J[n]['id']]
            mA = int.from_bytes(b[0:2], 'little', signed=True)
            q = angle(n, int.from_bytes(b[6:10], 'little', signed=True))
            print(f'  {n:16s} {math.degrees(goal[n]):+6.1f} {math.degrees(q):+6.1f} {math.degrees(q - goal[n]):+5.1f} {mA:5d}', flush=True)

    cur = dict(q0)
    print('from ' + '  '.join(f'{n}:{math.degrees(q0[n]):+.0f}' for n in moving), flush=True)
    try:
        go(pose(a.curl_knee, a.curl_ankle), a.move, 'curled')
        go(pose(0, 0), a.move, 'stretched')
        go(pose(a.curl_knee, a.curl_ankle), a.move, 'curled again')
    except (KeyboardInterrupt, dxl.DxlError) as e:
        print('stopped:', e)
    finally:
        for i in ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
            except dxl.DxlError:
                pass
        pub.close()
        bus.close()
        print('torque off')


if __name__ == '__main__':
    main()
