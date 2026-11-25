"""Which servo is which: one servo at a time turns ~10 deg one way and back, the rest stay limp, with a pause between, so you can watch
what really moves and compare with the name the config gives that ID. It streams to the twin (`twin.py --remote <pi>`): the twin moves
the joint the config names, the duck the joint that is wired there.

  systemctl --user stop duck-launcher; python servo_wiggle.py 5 4 3 2 1; systemctl --user start duck-launcher
  python servo_wiggle.py 10 9 8 7 6 --amp 15
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
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', type=int, nargs='+')
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--amp', type=float, default=10.0, help='deg')
    ap.add_argument('--gap', type=float, default=3.0, help='seconds between servos')
    a = ap.parse_args()
    cfg = load_config(a.config)
    name = {j['id']: n for n, j in cfg['joints'].items()}
    all_ids = sorted(name)
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    pub = Publisher()

    def stream(secs):
        t0 = time.monotonic()
        while time.monotonic() - t0 < secs:
            raw = bus.sync_read(all_ids, dxl.PRESENT_POSITION[0], 4)
            pub.send({i: int.from_bytes(raw[i], 'little', signed=True) for i in all_ids})
            time.sleep(0.03)

    stream(1.0)
    for k, i in enumerate(a.ids, 1):
        p0 = bus.read(i, dxl.PRESENT_POSITION, signed=True)
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, 600)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
        bus.write(i, dxl.GOAL_POSITION, p0)
        bus.write(i, dxl.TORQUE_ENABLE, 1)
        print(f'{k}: ID {i} ({name.get(i, "?")}) moving', flush=True)
        d = int(round(math.radians(a.amp) / K))
        for f in [x / 10 for x in range(11)] + [1 - x / 10 for x in range(11)]:
            bus.write(i, dxl.GOAL_POSITION, p0 + int(d * math.sin(f * math.pi / 2)))
            stream(0.05)
        stream(0.3)
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
        stream(a.gap)
    pub.close()
    bus.close()
    print('done, all limp')


if __name__ == '__main__':
    main()
