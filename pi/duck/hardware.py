"""The duck's servos and IMU, in the policy's units: radians, in the model's joint order.

config (config/dynamixel.json): for each joint its servo id, direction and centre tick. Directions and centres start as
guesses, and `python -m duck.calibrate` measures the centres on the real robot.
"""
import json
import math
import socket
import struct
import time

import numpy as np

from . import dxl


class Servos:
    def __init__(self, port, cfg, baud=1_000_000):
        self.cfg = cfg
        self.bus = dxl.Bus(port, baud=baud)
        self.names = cfg['policy_joints']
        self.ids = [cfg['joints'][n]['id'] for n in self.names]
        self.all_names = self.names + cfg['extra_joints']
        self.all_ids = [cfg['joints'][n]['id'] for n in self.all_names]
        self.sign = np.array([cfg['joints'][n]['direction'] for n in self.names], float)
        self.centre = np.array([cfg['joints'][n]['centre'] for n in self.names], float)
        self.k = 2 * math.pi / dxl.TICKS_PER_REV

    def setup(self):
        """Position mode at the trained gain. Torque must be off to change a mode."""
        for i in self.all_ids:
            if not self.bus.ping(i):
                raise dxl.DxlError(f'no servo {i}')
            self.bus.write(i, dxl.TORQUE_ENABLE, 0)
            self.bus.write(i, dxl.RETURN_DELAY, 0)
            self.bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
            self.bus.write(i, dxl.POSITION_P, self.cfg['position_p'])
            self.bus.write(i, dxl.PROFILE_VELOCITY, 0)

    def torque(self, on):
        for i in self.all_ids:
            self.bus.write(i, dxl.TORQUE_ENABLE, 1 if on else 0)

    def read(self):
        """Joint positions (rad) and velocities (rad/s), from one sync read of velocity and position."""
        addr = dxl.PRESENT_VELOCITY[0]
        raw = self.bus.sync_read(self.ids, addr, 8)
        vel, tick = np.zeros(len(self.ids)), np.zeros(len(self.ids))
        for k, i in enumerate(self.ids):
            v, p = struct.unpack('<ii', raw[i])
            vel[k], tick[k] = v, p
        return (tick - self.centre) * self.k * self.sign, vel * dxl.VELOCITY_UNIT * self.sign

    def write(self, q):
        ticks = np.rint(np.asarray(q) * self.sign / self.k + self.centre).astype(int)
        self.bus.sync_write(self.ids, dxl.GOAL_POSITION, [int(t) for t in ticks])

    def hold_beak(self, q=0.0):
        for n in self.cfg['extra_joints']:
            j = self.cfg['joints'][n]
            self.bus.write(j['id'], dxl.GOAL_POSITION, int(round(q * j['direction'] / self.k + j['centre'])))

    def voltage(self):
        """Volts, from the first servo on the bus."""
        return self.bus.read(self.ids[0], dxl.PRESENT_VOLTAGE) * 0.1

    def close(self):
        self.bus.close()


class Bno085:
    """The real IMU over I2C (pins 3 and 5), the GY-BNO08X at 0x4B on the duck (2026-11-23). Returns (gyro rad/s, gravity unit vector), both in
    the robot's frame. Read in a thread: the Adafruit library on the Pi's I2C now and then gets a garbled packet (the BNO085 stretches the clock,
    which the Pi's I2C handles badly) and raises, here a KeyError on an unknown report id after ~25 s. A bad packet is skipped; errors in a row
    restart the IMU. read() gives the latest good reading at once, and .age is how old it is, for the caller to stop on a silent IMU."""

    def __init__(self, cfg, rate=100.0):
        import threading
        self.R = np.array(cfg['imu_to_robot'], float)
        self.rate = rate
        self._latest = (np.zeros(3), np.array([0.0, 0.0, -1.0]))
        self._t = None
        self.errors = 0
        self.restarts = 0
        self._stop = False
        self._lock = threading.Lock()
        self._start()                                     # the first start in the caller's thread, so a missing IMU fails at once
        t1 = time.monotonic()
        while not self._read_once() and time.monotonic() - t1 < 2.0:
            time.sleep(0.01)
        threading.Thread(target=self._run, daemon=True).start()

    def _start(self):
        import board
        import busio
        from adafruit_bno08x import BNO_REPORT_GAME_ROTATION_VECTOR, BNO_REPORT_GYROSCOPE
        from adafruit_bno08x.i2c import BNO08X_I2C
        if getattr(self, 'i2c', None) is None:
            self.i2c = busio.I2C(board.SCL, board.SDA)    # the clock is set by the Pi (config.txt), not here
        # 0x4A on Adafruit's board; the GY-BNO08X's AD0 pad can make it 0x4B. Try both (i2cdetect -y 1 shows which)
        last = None
        for addr in (0x4B, 0x4A):
            try:
                self.imu = BNO08X_I2C(self.i2c, address=addr)
                break
            except (ValueError, OSError, RuntimeError) as e:
                last = e
        else:
            raise last
        # every 10 ms: the library's default is 50 ms (20 Hz), under the policy's 50 Hz, and the first real stand (2026-11-23) saw the
        # readings change every third tick, then a 200 ms gap that stopped it
        self.imu.enable_feature(BNO_REPORT_GYROSCOPE, report_interval=10_000)
        self.imu.enable_feature(BNO_REPORT_GAME_ROTATION_VECTOR, report_interval=10_000)

    def _read_once(self):
        """-> True for a new, believable reading. The library hands back its last values when no report came, so a reading identical to the
        last is not new; and a garbled packet can parse as a report (seen: gyro -63.6 rad/s, gravity 6 long), so those are dropped."""
        gyro = np.array(self.imu.gyro, float)
        quat = tuple(self.imu.game_quaternion)
        raw = tuple(gyro) + quat
        if raw == getattr(self, '_raw', None):
            return False
        if quat in ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 0.0)):    # the library's value before any report (after every restart): not a measurement
            return False
        self._raw = raw
        x, y, z, w = quat
        g = -np.array([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)])     # world down, in the sensor's frame
        if not (0.9 < np.linalg.norm(g) < 1.1 and np.all(np.abs(gyro) < 35.0)):
            self.errors += 1
            return False
        with self._lock:
            self._latest = (self.R @ gyro, self.R @ g)
            self._t = time.monotonic()
        return True

    def _run(self):
        in_row = 0
        while not self._stop:
            try:
                self._read_once()
                in_row = 0
                if self.age > 0.3:                         # nothing new for 0.3 s: the sensor has stopped reporting; start it again
                    self._start()
                    self.restarts += 1
                    self._t = time.monotonic() - 0.15      # give it a moment before the next restart
            except Exception:                              # noqa: BLE001  the library raises KeyError, IndexError, RuntimeError, OSError on a bad packet
                self.errors += 1
                in_row += 1
                if in_row >= 5:
                    try:
                        self._start()
                        self.restarts += 1
                    except Exception:                      # noqa: BLE001
                        time.sleep(0.2)
                    in_row = 0
            time.sleep(1 / self.rate)

    @property
    def age(self):
        return float('inf') if self._t is None else time.monotonic() - self._t

    def read(self):
        with self._lock:
            return self._latest

    def close(self):
        self._stop = True


class SimImu:
    """The simulated IMU: pi/sim/server.py answers with 6 floats."""

    def __init__(self, addr):
        host, port = addr.rsplit(':', 1)
        self.s = socket.create_connection((host, int(port)), timeout=1.0)
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def read(self):
        self.s.sendall(b'r')
        buf = b''
        while len(buf) < 24:
            buf += self.s.recv(24 - len(buf))
        v = np.array(struct.unpack('<6f', buf), float)
        return v[:3], v[3:]

    def close(self):
        self.s.close()


def load_config(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
