"""Calibrate one joint without mistakes: every other servo holds where it is, only the named joint goes limp, and its angle (by the
config's centre) prints twice a second. Put that joint at its zero by a reference (a leg flat on the table, a foot flat on the floor), read
the angle: the config's centre for it moves by that much. Streams to the twin. Ctrl-C (or SIGTERM): all torque off.

  systemctl --user stop duck-launcher; python calib_hold.py right_hip_roll; systemctl --user start duck-launcher
"""
import argparse
import math
import os
import signal
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from duck.telemetry import Publisher  # noqa: E402
from stand_test import GOAL_CURRENT, MODE_CURRENT_POSITION  # noqa: E402

K = 360 / 4096


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('joint')
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--cap', type=int, default=500, help='mA for the held servos')
    ap.add_argument('--seconds', type=float, default=900)
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    J = load_config(a.config)['joints']
    if a.joint not in J:
        raise SystemExit(f'no joint {a.joint}: one of {", ".join(J)}')
    target = J[a.joint]['id']
    all_ids = sorted(j['id'] for j in J.values())
    held = [i for i in all_ids if i != target]
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    pub = Publisher()
    bus.write(target, dxl.TORQUE_ENABLE, 0)
    for i in held:
        p = bus.read(i, dxl.PRESENT_POSITION, signed=True)
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, a.cap)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
        bus.write(i, dxl.GOAL_POSITION, p)
        bus.write(i, dxl.TORQUE_ENABLE, 1)
    j = J[a.joint]
    print(f'holding everything but {a.joint} (ID {target}, centre {j["centre"]}): move it to its zero', flush=True)
    t0, last = time.monotonic(), 0.0
    try:
        while time.monotonic() - t0 < a.seconds:
            raw = bus.sync_read(all_ids, dxl.PRESENT_POSITION[0], 4)
            ticks = {i: int.from_bytes(raw[i], 'little', signed=True) for i in all_ids}
            pub.send(ticks)
            if time.monotonic() - last > 0.5:
                last = time.monotonic()
                p = ticks[target]
                deg = ((p - j['centre'] + 2048) % 4096 - 2048) * K * j['direction']
                print(f'{last - t0:6.1f}s  {a.joint} {deg:+6.1f} deg  (raw {p}: centre {p % 4096} would read 0)', flush=True)
            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
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


if __name__ == '__main__':
    main()
