"""Find where one joint really stops: it turns slowly one way, then the other, at a low current cap, and stops each way as soon as it is
blocked (trailing its goal while pushing), so a wire or a shell is pressed lightly, never forced. The other servos stay limp. It prints
the angle each way (the config's zero and direction), and streams to the twin (twin.py --remote <pi>).

  systemctl --user stop duck-launcher; python joint_range.py neck_pitch --to 60 --back -90; systemctl --user start duck-launcher
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
from stand_test import GOAL_CURRENT, MODE_CURRENT_POSITION  # noqa: E402

K = 2 * math.pi / 4096


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('joint')
    ap.add_argument('--to', type=float, required=True, help='deg: the farthest it is asked to go the + way')
    ap.add_argument('--back', type=float, required=True, help='deg: the farthest the - way')
    ap.add_argument('--speed', type=float, default=10.0, help='deg/s')
    ap.add_argument('--cap', type=int, default=300, help='mA: low, so a stop or a wire is only pressed')
    ap.add_argument('--lag', type=float, default=4.0, help='deg behind its goal that counts as blocked')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--port', default='auto')
    a = ap.parse_args()
    cfg = load_config(a.config)
    j = cfg['joints'][a.joint]
    i, s, c = j['id'], j['direction'], j['centre']
    all_ids = sorted(x['id'] for x in cfg['joints'].values())
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    pub = Publisher()
    p0 = bus.read(i, dxl.PRESENT_POSITION, signed=True)
    q0 = math.degrees(((p0 - c + 2048) % 4096 - 2048) * K * s)

    def tick_of(deg):
        return p0 + int(round(math.radians(deg - q0) * s / K))

    def deg_of(p):
        return q0 + math.degrees((p - p0) * s * K)

    bus.write(i, dxl.TORQUE_ENABLE, 0)
    bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
    bus.write(i, GOAL_CURRENT, a.cap)
    bus.write(i, dxl.PROFILE_VELOCITY, 0)
    bus.write(i, dxl.GOAL_POSITION, p0 & 0xFFFFFFFF)
    bus.write(i, dxl.TORQUE_ENABLE, 1)
    found = {}
    try:
        for name, end in (('+', a.to), ('-', a.back), ('home', q0)):
            start = deg_of(bus.read(i, dxl.PRESENT_POSITION, signed=True))
            secs = abs(end - start) / a.speed
            t0 = time.monotonic()
            while True:
                t = time.monotonic() - t0
                goal = start + (end - start) * min(1.0, t / max(secs, 1e-6))
                bus.write(i, dxl.GOAL_POSITION, tick_of(goal) & 0xFFFFFFFF)
                raw = bus.sync_read(all_ids, 126, 10)
                ticks = {x: int.from_bytes(raw[x][6:10], 'little', signed=True) for x in all_ids}
                pub.send(ticks)
                now = deg_of(ticks[i])
                ma = int.from_bytes(raw[i][0:2], 'little', signed=True)
                if name != 'home' and abs(goal - now) > a.lag and abs(ma) > 0.6 * a.cap:
                    found[name] = (now, ma)
                    print(f'{a.joint} blocked going {name}: at {now:+.1f} deg ({ma} mA, goal {goal:+.1f})', flush=True)
                    bus.write(i, dxl.GOAL_POSITION, ticks[i] & 0xFFFFFFFF)    # stop pressing at once
                    time.sleep(0.3)
                    break
                if t > secs + 0.5:
                    if name != 'home':
                        found[name] = (now, ma)
                        print(f'{a.joint} reached {now:+.1f} deg going {name}, not blocked ({ma} mA)', flush=True)
                    break
                time.sleep(0.02)
    except KeyboardInterrupt:
        print('stopped')
    finally:
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
        pub.close()
        bus.close()
    print(f'{a.joint}: ' + ', '.join(f'{k} {v[0]:+.1f} deg' for k, v in found.items()) + ' (torque off)')


if __name__ == '__main__':
    main()
