"""A simulated duck that looks like the real one to the Pi's code: Dynamixel Protocol 2.0 bytes on one TCP port, the IMU on another, MuJoCo behind them.

  python sim/server.py [--pinned] [--port 9000] [--imu-port 9001]

run.py connects with --port socket://127.0.0.1:9000 --imu 127.0.0.1:9001, and nothing else changes. Servo model as the trainer's: position gain (scaled by each servo's
POSITION_P register once written), a torque limit falling with speed, a 15-30 ms delay. No backlash or sag: those are the trainer's randomization. --pinned holds the body in the air, for checking directions and the loop without a policy that balances.
"""
import argparse
import json
import os
import socket
import struct
import threading
import time
from collections import deque

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, os.path.dirname(HERE))
from duck import dxl  # noqa: E402
import twin  # noqa: E402


class Servo:
    def __init__(self, ident, centre, direction, joint=None):
        self.mem = bytearray(256)
        self.id, self.centre, self.dir, self.joint = ident, centre, direction, joint
        self.put(dxl.PRESENT_VOLTAGE, 78)     # 7.8 V
        self.put(dxl.GOAL_POSITION, centre)
        self.put(dxl.PRESENT_POSITION, centre)

    def put(self, reg, v):
        self.mem[reg[0]:reg[0] + reg[1]] = int(v).to_bytes(reg[1], 'little', signed=v < 0)

    def get(self, reg, signed=False):
        return int.from_bytes(self.mem[reg[0]:reg[0] + reg[1]], 'little', signed=signed)


class Duck:
    def __init__(self, cfg, pinned, start=None, level=False, tilt=None):
        spec = mujoco.MjSpec.from_file(os.path.join(HERE, 'model', 'milli.xml'))
        twin.decorate(spec, collide=True)              # a solid floor, with the twin's sky and checks
        self.m = spec.compile()
        for frm, to, kg in MASS_MOVES:                 # --head-mass: weight moved from one body to another (the real battery sits under the head)
            a_, b_ = (mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, n) for n in (frm, to))
            if frm != '-':
                self.m.body_mass[a_] -= kg
            self.m.body_mass[b_] += kg
        if SOLE[0] is not None:                         # --sole: springy feet (the real duck's sprung TPU soles): the foot contacts' solref, timeconst and damping ratio
            for g in range(self.m.ngeom):
                n = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, g) or ''
                if n.endswith('foot_collision'):
                    self.m.geom_solref[g] = SOLE[0]
                    self.m.geom_solmix[g] = 1e6         # the foot's solref wins over the floor's
        if FRICTION[0] is not None:                    # --friction: every hinge's gear friction (the real XL330s hold ~0.04 N m: 120 mA of deadband)
            for j in range(self.m.njnt):
                if self.m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE:
                    self.m.dof_frictionloss[self.m.jnt_dofadr[j]] = FRICTION[0]
        self.d = mujoco.MjData(self.m)
        self.cfg, self.pinned = cfg, pinned
        # each joint's peak torque and no-load speed from the model's home.json (the trainer's numbers: the XL330 at 5 V, 0.52 N m, 10.8 rad/s), else the config's
        home = json.load(open(os.path.join(HERE, 'model', 'home.json')))
        self.limits = {} if cfg['servo'].get('peak_from_cli') else {j: (s['peak_nm'], s['noload_rads']) for s in home.get('servos', {}).values() for j in s['joints']}
        self.servos = {}
        k = 2 * np.pi / dxl.TICKS_PER_REV
        self.k = k
        self.joints = {}
        for name, j in cfg['joints'].items():
            jid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, name)
            self.servos[j['id']] = Servo(j['id'], j['centre'], j['direction'], name if jid >= 0 else None)
            if jid >= 0:
                self.joints[j['id']] = (self.m.jnt_qposadr[jid], self.m.jnt_dofadr[jid], self.m.jnt_range[jid])
        self.d.qpos[:3] = [0, 0, cfg['root_z'] + (0.1 if pinned and not HELD[0] else 0.0)]
        self.d.qpos[3:7] = [1, 0, 0, 0]
        for name, v in (start or cfg['home']).items():
            jid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, name)
            if jid >= 0:
                if start and self.m.jnt_limited[jid]:
                    v = float(np.clip(v, *self.m.jnt_range[jid]))     # the real knees fold past the model's limits: start at the limit
                self.d.qpos[self.m.jnt_qposadr[jid]] = v
        if start and not pinned:
            mujoco.mj_forward(self.m, self.d)
            if level:                                   # the body level, resting on whatever touches first: the real duck sits on its heels, torso upright
                twin.orient_to_gravity(self.m, self.d, [0.0, 0.0, -1.0])
                twin.rest_on_floor(self.m, self.d, False)
            else:
                twin.rest_on_floor(self.m, self.d)      # a start pose: feet flat on the floor
        if tilt is not None and not pinned:            # (pitch, roll) deg: the body tilted, resting on the floor, as a hand might hold it
            mujoco.mj_forward(self.m, self.d)
            p, r = np.radians(tilt)
            twin.orient_to_gravity(self.m, self.d, [np.sin(p) * np.cos(r), np.sin(r), -np.cos(p) * np.cos(r)])
            twin.rest_on_floor(self.m, self.d, False)
        self.base = self.d.qpos[:7].copy()
        self.lag = deque(maxlen=max(1, int((0.02 + EXTRA_LAG[0]) / self.m.opt.timestep)))
        self.imu_hist = deque(maxlen=max(1, int(IMU_LAG[0] / self.m.opt.timestep)))       # --imu-lag-ms
        self.vel_hist = deque(maxlen=max(1, int(VEL_LAG[0] / self.m.opt.timestep)))       # --vel-lag-ms    # about the trainer's 15-30 ms, plus --extra-lag-ms
        self.lock = threading.Lock()
        self.imu_site = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_SITE, 'imu')
        self.stop = False
        self.fallen_at = None
        self.t_real = 0.0
        mujoco.mj_forward(self.m, self.d)
        self.sync_present()

    def sync_present(self):
        if VEL_LAG[0]:                                  # --vel-lag-ms: the servos' reported speed, that long old (the real XL330 filters it)
            self.vel_hist.append(self.d.qvel.copy())
        qvel = self.vel_hist[0] if VEL_LAG[0] else self.d.qvel
        for i, (qa, da, _) in self.joints.items():
            s = self.servos[i]
            s.put(dxl.PRESENT_POSITION, int(round(self.d.qpos[qa] * s.dir / self.k + s.centre)))
            s.put(dxl.PRESENT_VELOCITY, int(round(qvel[da] * s.dir / dxl.VELOCITY_UNIT)))

    def step(self):
        c = self.cfg['servo']
        with self.lock:
            # a goal is ticks within a turn of the zero: a joint whose zero sits by the 0/4095 wrap (the hip yaws, centres 14 and 17) gets goals
            # just under 0 or over 4095; read as unsigned they were a huge angle and pinned the joint at its limit (2026-11-24)
            goals = {i: ((self.servos[i].get(dxl.GOAL_POSITION, signed=True) - self.servos[i].centre + 2048) % 4096 - 2048) * self.k * self.servos[i].dir
                     for i in self.joints}
            on = {i: self.servos[i].get(dxl.TORQUE_ENABLE) for i in self.joints}
            self.lag.append(goals)
            goals = self.lag[0]
            self.d.qfrc_applied[:] = 0
            for i, (qa, da, _) in self.joints.items():
                if not on[i]:
                    continue
                v = self.d.qvel[da]
                # the stiffness follows the position P this servo was sent, as the trainer's does (kp 0.55 at P 200: tools/make_rl_model.py
                # DEPLOYED_P); until one is written, the config's
                p_gain = self.servos[i].get(dxl.POSITION_P)
                kp = c['kp'] * p_gain / self.cfg.get('position_p', 200) if p_gain else c['kp']
                tau = kp * (goals[i] - self.d.qpos[qa])
                # the torque the motor can give, falling linearly to zero at no-load speed
                peak, noload = self.limits.get(self.servos[i].joint, (c['peak_nm'], c['noload_rads']))
                lim_up = peak * np.clip(1 - v / noload, 0, 1)
                lim_dn = peak * np.clip(1 + v / noload, 0, 1)
                self.d.qfrc_applied[da] = np.clip(tau, -lim_dn, lim_up)
            mujoco.mj_step(self.m, self.d)
            if TRACE[0] is not None and self.d.time - TRACE[1] >= 0.1:     # --trace: where the body is, ten times a second
                TRACE[1] = self.d.time
                w, x, y, z = self.d.qpos[3:7]
                TRACE[0].write(f'{self.d.time:.2f},{self.d.qpos[0]:.4f},{self.d.qpos[1]:.4f},{self.d.qpos[2]:.4f},'
                               f'{np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))):.1f}\n')
                TRACE[0].flush()
            if any(on.values()) and getattr(self, 't_on', None) is None:
                self.t_on = self.d.time
            held = HELD[0] and (getattr(self, 't_on', None) is None or self.d.time - self.t_on < HELD[1])
            if self.pinned or held or not any(on.values()):     # until the torque comes on, someone is holding it (--held: a hand on the body)
                self.d.qpos[:7] = self.base
                self.d.qvel[:6] = 0
            self.sync_present()

    def imu_now(self):
        R = self.d.site_xmat[self.imu_site].reshape(3, 3)
        gyro = self.d.sensordata[self.m.sensor_adr[mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_SENSOR, 'imu_ang_vel')]:][:3].copy()
        return np.concatenate([gyro, R.T @ np.array([0, 0, -1.0])])

    def imu(self):
        with self.lock:
            return self.imu_hist[0].copy() if IMU_LAG[0] and self.imu_hist else self.imu_now()

    def physics(self):
        dt, nxt = self.m.opt.timestep, time.monotonic()
        while not self.stop:
            self.step()
            if IMU_LAG[0]:
                with self.lock:
                    self.imu_hist.append(self.imu_now())
            nxt += dt
            wait = nxt - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            else:
                nxt = time.monotonic()      # running behind real time: slow down, don't jump


def bus_server(duck, sock):
    """Answers instruction packets as the servos would."""
    conn, _ = sock.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    buf = bytearray()

    def status(ident, params=b'', err=0):
        body = dxl.stuff(bytes((dxl.STATUS, err)) + bytes(params))
        head = dxl.HEADER + bytes((ident,)) + struct.pack('<H', len(body) + 2)
        pkt = head + body
        return pkt + struct.pack('<H', dxl.crc16(pkt))

    while not duck.stop:
        try:
            d = conn.recv(4096)
        except OSError:
            break
        if not d:
            break
        buf += d
        while True:
            k = buf.find(dxl.HEADER)
            if k < 0 or len(buf) < k + 7:
                break
            n = struct.unpack('<H', buf[k + 5:k + 7])[0]
            if len(buf) < k + 7 + n:
                break
            pkt = bytes(buf[k:k + 7 + n])
            del buf[:k + 7 + n]
            if struct.unpack('<H', pkt[-2:])[0] != dxl.crc16(pkt[:-2]):
                continue                    # a real servo ignores a bad packet, and the Pi's read times out
            ident, inst, p = pkt[4], pkt[7], dxl.unstuff(pkt[8:-2])
            out = b''
            with duck.lock:
                if inst == dxl.PING and ident in duck.servos:
                    out = status(ident, b'\x60\x00\x01')
                elif inst == dxl.READ and ident in duck.servos:
                    a, s = struct.unpack('<HH', p[:4])
                    out = status(ident, duck.servos[ident].mem[a:a + s])
                elif inst == dxl.WRITE and ident in duck.servos:
                    a = struct.unpack('<H', p[:2])[0]
                    duck.servos[ident].mem[a:a + len(p) - 2] = p[2:]
                    out = status(ident)
                elif inst == dxl.SYNC_READ:
                    a, s = struct.unpack('<HH', p[:4])
                    out = b''.join(status(i, duck.servos[i].mem[a:a + s]) for i in p[4:] if i in duck.servos)
                elif inst == dxl.SYNC_WRITE:
                    a, s = struct.unpack('<HH', p[:4])
                    for k2 in range(4, len(p), s + 1):
                        if p[k2] in duck.servos:
                            duck.servos[p[k2]].mem[a:a + s] = p[k2 + 1:k2 + 1 + s]
            if out:
                conn.sendall(out)
    duck.stop = True


def imu_server(duck, sock):
    conn, _ = sock.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    while not duck.stop:
        try:
            if not conn.recv(1):
                break
            conn.sendall(struct.pack('<6f', *duck.imu()))
        except OSError:
            break


EXTRA_LAG = [0.0]
IMU_LAG = [0.0]
TRACE = [None, -1.0]                            # --trace: the file, and the time of its last line
SOLE = [None]                                           # (timeconst s, damping ratio), --sole                                         # s, --imu-lag-ms
VEL_LAG = [0.0]                                         # s, --vel-lag-ms
FRICTION = [None]                                       # N m, --friction
MASS_MOVES = []                                         # (from body or '-', to body, kg)
HELD = [False, 1e9]                                     # --held: the body held still where it stands, feet on the floor, for HELD[1] s


def serve(cfg, pinned=False, port=9000, imu_port=9001, start=None, level=False, tilt=None):
    duck = Duck(cfg, pinned, start, level, tilt)
    socks = []
    for p in (port, imu_port):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', p))
        s.listen(1)
        socks.append(s)
    threads = [threading.Thread(target=duck.physics, daemon=True), threading.Thread(target=bus_server, args=(duck, socks[0]), daemon=True), threading.Thread(target=imu_server, args=(duck, socks[1]), daemon=True)]
    for t in threads:
        t.start()
    return duck


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pinned', action='store_true')
    ap.add_argument('--port', type=int, default=9000)
    ap.add_argument('--imu-port', type=int, default=9001)
    ap.add_argument('--config', default=os.path.join(os.path.dirname(HERE), 'config', 'dynamixel.json'))
    ap.add_argument('--view', action='store_true', help='a MuJoCo window')
    ap.add_argument('--start', help='a JSON of joint angles (rad) to start from, feet flat on the floor: twin.py --save-pose writes the real duck pose')
    ap.add_argument('--kp', type=float, help='servo stiffness, N m/rad, in place of the config value (0.55 is position_p 200; it scales with P)')
    ap.add_argument('--peak-nm', type=float, help='servo torque limit, N m, in place of the config value, 0.96 at 7.4 V. At 5 V an XL330 stalls at 0.52; capped at I mA it gives about 0.354 x I/1000')
    ap.add_argument('--battery-in-head', action='store_true', help='move 40 g (the battery and bus board) from the body to the neck, as on the real duck')
    ap.add_argument('--head-mass', type=float, default=0.0, help='kg added to the head (jaw_soft), for checking a heavier real head')
    ap.add_argument('--held', type=float, default=None, metavar='SECONDS', help='hold the body still where it stands (a hand on it, feet on the floor) for this long after the torque comes on; 0 = for good')
    ap.add_argument('--extra-lag-ms', type=float, default=0.0, help='ms of extra delay from a goal to the motor, on top of the ~20 ms modelled (the real duck lagged more)')
    ap.add_argument('--start-tilt', type=float, nargs=2, metavar=('PITCH', 'ROLL'), help='deg: start with the body tilted (pitch nose down +, roll left down +), resting on the floor')
    ap.add_argument('--sole', type=float, nargs=2, metavar=('TIMECONST', 'DAMPRATIO'), help='springy foot contacts: MuJoCo solref, e.g. 0.05 0.3 (default 0.02 1, near rigid)')
    ap.add_argument('--imu-lag-ms', type=float, default=0.0, help='ms: the IMU readings sent that old (the real BNO085 fuses and lags)')
    ap.add_argument('--vel-lag-ms', type=float, default=0.0, help='ms: the servos report their speed that old (the real XL330 filters it)')
    ap.add_argument('--friction', type=float, help='N m of gear friction on every joint, in place of the model 0.0048: the real XL330s measure ~0.04')
    ap.add_argument('--start-level', action='store_true', help='with --start: the body level (as the real duck sits, on its heels), not the feet flat')
    ap.add_argument('--trace', help='a CSV of the body, ten times a second: t, x, y, z (m), yaw (deg). For measuring how far a walk travels')
    a = ap.parse_args()
    if a.trace:
        TRACE[0] = open(a.trace, 'w', encoding='utf-8')
        TRACE[0].write('t,x,y,z,yaw_deg\n')
    cfg = json.load(open(a.config, encoding='utf-8'))
    if a.kp is not None:
        cfg['servo']['kp'] = a.kp
    if a.peak_nm is not None:
        cfg['servo']['peak_nm'] = a.peak_nm
        cfg['servo']['peak_from_cli'] = True          # one number for every joint, in place of home.json's
    start = json.load(open(a.start, encoding='utf-8')) if a.start else None
    EXTRA_LAG[0] = a.extra_lag_ms / 1000
    FRICTION[0] = a.friction
    IMU_LAG[0], VEL_LAG[0] = a.imu_lag_ms / 1000, a.vel_lag_ms / 1000
    SOLE[0] = a.sole
    if a.battery_in_head:
        MASS_MOVES.append(('trunk_base', 'neck', 0.040))
    if a.head_mass:
        MASS_MOVES.append(('-', 'jaw_soft', a.head_mass))
    if a.held is not None:
        HELD[0], HELD[1] = True, (a.held if a.held > 0 else 1e9)
    d = serve(cfg, a.pinned, a.port, a.imu_port, start, a.start_level, a.start_tilt)
    print('listening: bus', a.port, 'IMU', a.imu_port, '(Ctrl-C to stop)', f"servo kp {cfg['servo']['kp']} at P {cfg.get('position_p', 200)} (follows each servo's P), peak and speed by joint from sim/model/home.json")
    if a.view:
        import mujoco.viewer
        with mujoco.viewer.launch_passive(d.m, d.d, show_left_ui=False, show_right_ui=False) as v:
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
            while v.is_running() and not d.stop:
                with d.lock:
                    v.cam.lookat[:] = d.d.subtree_com[1]
                    v.sync()
                time.sleep(1 / 60)
    else:
        while not d.stop:
            time.sleep(0.2)
