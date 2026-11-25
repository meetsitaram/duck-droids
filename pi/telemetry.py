"""On the Pi: read every servo's position and the IMU, 30 times a second, and send them to the PC's digital twin over Wi-Fi. Read only:
it never writes to a servo, so nothing moves and the torque stays as it is.

  python telemetry.py                    then on the PC: python twin.py --remote <pi address>
  python telemetry.py --no-imu           the servos only

While run_policy.py drives the duck, it owns the bus: use its --telemetry instead.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from duck.telemetry import PORT, Publisher  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto', help='the servo bus')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--net-port', type=int, default=PORT)
    ap.add_argument('--hz', type=float, default=30)
    ap.add_argument('--no-imu', action='store_true')
    a = ap.parse_args()
    cfg = load_config(a.config)
    ids = sorted(j['id'] for j in cfg['joints'].values())
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    imu = None
    if not a.no_imu:
        from duck.hardware import Bno085
        try:
            imu = Bno085(cfg)
        except Exception as e:                             # noqa: BLE001  a loose IMU wire shouldn't stop the twin: the servos alone
            print(f'IMU not answering ({e}): sending the servos only', flush=True)
    pub = Publisher(a.net_port)
    print(f'sending {len(ids)} servos{" and the IMU" if imu else ""} on port {a.net_port}; Ctrl-C to stop', flush=True)
    nxt = time.monotonic()
    try:
        while True:
            try:
                raw = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
                ticks = {i: int.from_bytes(raw[i], 'little', signed=True) for i in ids}
            except dxl.DxlError as e:
                print('read failed:', e, flush=True)
                time.sleep(0.2)
                continue
            gyro, grav = imu.read() if imu else (None, None)
            pub.send(ticks, grav, gyro, imu_age=round(imu.age, 3) if imu else None)
            nxt += 1 / a.hz
            time.sleep(max(0.0, nxt - time.monotonic()))
    except KeyboardInterrupt:
        pass
    finally:
        pub.close()
        bus.close()
        if imu:
            imu.close()


if __name__ == '__main__':
    main()
