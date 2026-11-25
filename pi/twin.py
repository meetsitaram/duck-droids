"""The digital twin: the real duck's pose, read from its servos, shown on the MuJoCo model. Read only: it never writes to a servo,
so nothing moves and torque stays as it is. Pose the duck by hand, torque off, and compare.

  python twin.py                     a MuJoCo window, following the duck live, and a table of joint angles every 2 s
  python twin.py --snapshot pose.png  one picture from three sides, then exit
  python twin.py --port COM3          the bus board's port, if more than one is found
  python twin.py --remote                the bus is on the duck's Pi: draw what it sends (pi/telemetry.py, or run_policy.py --telemetry);
                                          the body leans as the IMU says (--feet-flat: as the feet say, the default without an IMU)
  python twin.py --no-soles           the soles aren't fitted yet: stand it on its bare feet
  python twin.py --body-level         body held level, feet as they fall (the duck in the air); by default its feet are flat on the floor

In the window: drag to turn the view, right-drag to move it, scroll to zoom, Tab and Shift+Tab show the menus.

Joint angle = (tick - centre) x direction, in radians, with centre and direction from config/dynamixel.json. Until
`python -m duck.calibrate` has measured the centres with the duck at zero (legs straight, head level, beak shut) and each
direction is checked, the twin won't match: that's what it's for.
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
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402

import mujoco  # noqa: E402

K = 2 * math.pi / dxl.TICKS_PER_REV
PTS = {}          # per model: sample points of each mesh, to rest the duck on the floor
GRAV = [None]     # the IMU's gravity in the body frame, from the Pi's stream: when known, the body is turned to match it, not guessed from the feet
FEET_FLAT = [True]   # turn the model so its feet are flat; --body-level holds the body level instead (the duck held in the air)
SETTLE = [False, (0.0, 0.0)]   # --settle: tip the model as gravity would, onto its lowest parts (the duck lying on a table); the last tilt


def angles(raw, cfg, names):
    """Joint angles (rad) from raw ticks. A reading with torque off can be more than a turn off: wrap it to the turn nearest the centre."""
    q = {}
    for n in names:
        j = cfg['joints'][n]
        if j['id'] not in raw:                       # a sender that doesn't drive every servo (motion.py leaves the beak out): left at 0
            continue
        d = (raw[j['id']] - j['centre'] + 2048) % 4096 - 2048
        q[n] = d * K * j['direction']
    return q


def read_ticks(bus, ids):
    raw = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
    return {i: int.from_bytes(raw[i], 'little', signed=True) for i in ids}


def decorate(spec, collide=False):
    """MuJoCo's usual blue sky and checkered floor, and a light. collide: the floor is solid (the simulator), not only seen (the twin)."""
    spec.add_texture(name='sky', type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                     rgb1=[0.3, 0.5, 0.7], rgb2=[0, 0, 0], width=512, height=3072)
    spec.add_texture(name='grid', type=mujoco.mjtTexture.mjTEXTURE_2D, builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                     rgb1=[0.2, 0.3, 0.4], rgb2=[0.1, 0.2, 0.3], mark=mujoco.mjtMark.mjMARK_EDGE, markrgb=[0.8, 0.8, 0.8],
                     width=300, height=300)
    mat = spec.add_material(name='grid', texrepeat=[5, 5], reflectance=0.2)
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = 'grid'
    spec.worldbody.add_light(pos=[0, 0, 1.5], dir=[0, 0, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL)
    spec.worldbody.add_geom(name='floor', type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05], material='grid',
                            contype=1 if collide else 0, conaffinity=1 if collide else 0)


SOLE = '_f2b233'   # the soles' colour in the spec, and so their meshes' names


def load_model(cfg, soles=True):
    """The sim model, with MuJoCo's usual blue sky and checkered floor added, and each mesh's points kept to rest the duck on the floor."""
    spec = mujoco.MjSpec.from_file(os.path.join(HERE, 'sim', 'model', 'milli.xml'))
    decorate(spec)
    # the beak: locked in the training model, but the twin shows it. Its hinge is the jaw body's origin, about y, open 0 to 0.39 rad (the spec)
    jaw = spec.body('jaw')
    if jaw is not None and not jaw.joints:
        jaw.add_joint(name='beak', type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 1, 0], range=[0, 0.39])
    m = spec.compile()
    d = mujoco.MjData(m)
    adr = {}
    for n in cfg['policy_joints'] + cfg.get('extra_joints', []):
        jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
        if jid >= 0:
            adr[n] = m.jnt_qposadr[jid]
    pts = []
    for g in range(m.ngeom):
        mesh = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, m.geom_dataid[g]) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH else ''
        if not soles and mesh and mesh.endswith(SOLE):
            m.geom_rgba[g, 3] = 0          # not fitted yet: hidden, and not what the duck stands on
            continue
        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_bodyid[g] > 0 and m.geom_group[g] == 2:
            k = m.geom_dataid[g]
            v = m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k] + m.mesh_vertnum[k]]
            pts.append((g, v[::max(1, len(v) // 400)]))          # a few hundred points a mesh is plenty to find its lowest
    PTS[id(m)] = pts
    return m, d, adr


def pose(m, d, adr, q, root_z=None):
    """Joint angles in, then the body lowered or raised till its lowest point rests on the floor."""
    d.qpos[:] = m.qpos0
    free = m.nq >= 7 and m.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE
    if free:
        d.qpos[:3] = [0, 0, 0.5]
        d.qpos[3:7] = [1, 0, 0, 0]
    for n, a in adr.items():
        d.qpos[a] = q.get(n, 0.0)
    d.qvel[:] = 0
    mujoco.mj_forward(m, d)
    if free and SETTLE[0] and GRAV[0] is None:
        settle(m, d)
    elif free:
        if GRAV[0] is not None and FEET_FLAT[0]:
            orient_to_gravity(m, d, GRAV[0])
            rest_on_floor(m, d, False)
        else:
            rest_on_floor(m, d, FEET_FLAT[0])


def orient_to_gravity(m, d, grav):
    """Turn the whole model so the trunk feels the gravity the IMU measured (grav: unit vector, body frame, down). Yaw is kept."""
    R = d.xmat[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'trunk_base')].reshape(3, 3)
    u = R @ (np.array(grav, float) / np.linalg.norm(grav))           # where the measured down points in the world, as posed now
    v = np.array([0.0, 0.0, -1.0])
    axis = np.cross(u, v)
    s_, c_ = np.linalg.norm(axis), float(u @ v)
    if s_ > 1e-6:
        turn, out = np.zeros(4), np.zeros(4)
        mujoco.mju_axisAngle2Quat(turn, axis / s_, math.atan2(s_, c_))
        mujoco.mju_mulQuat(out, turn, d.qpos[3:7].copy())
        d.qpos[3:7] = out
        mujoco.mj_forward(m, d)


def mesh_points(m):
    """A few hundred points of each visible mesh, cached per model: what the duck rests on."""
    if id(m) not in PTS:
        pts = []
        for g in range(m.ngeom):
            if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_bodyid[g] > 0 and m.geom_group[g] == 2 and m.geom_rgba[g, 3] > 0:
                k = m.geom_dataid[g]
                v = m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k] + m.mesh_vertnum[k]]
                pts.append((g, v[::max(1, len(v) // 400)]))
        PTS[id(m)] = pts
    return PTS[id(m)]


def settle(m, d):
    """Tip the whole model (pitch, roll) to where its centre of mass is lowest above its lowest point: how it comes to rest on a flat
    table, on whatever parts touch. Searched near the last rest, so it follows the duck rather than jumping to another stable side."""
    pts = np.vstack([(d.geom_xmat[g].reshape(3, 3) @ v[::4].T).T + d.geom_xpos[g] for g, v in mesh_points(m)])
    com = d.subtree_com[1].copy()
    def height(p, r):
        cp, sp, cr, sr = math.cos(p), math.sin(p), math.cos(r), math.sin(r)
        R = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]]) @ np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        z = pts @ R[2]
        return com @ R[2] - z.min()
    p0, r0 = SETTLE[1]
    for span, step in ((math.radians(45), math.radians(3)), (math.radians(3), math.radians(0.25))):
        grid = np.arange(-span, span + 1e-9, step)
        best = min(((height(p0 + a, r0 + b), p0 + a, r0 + b) for a in grid for b in grid[::2] if abs(r0 + b) < math.radians(80)))
        _, p0, r0 = best
    SETTLE[1] = (p0, r0)
    qp, qr, out = np.zeros(4), np.zeros(4), np.zeros(4)
    mujoco.mju_axisAngle2Quat(qp, np.array([0, 1.0, 0]), p0)
    mujoco.mju_axisAngle2Quat(qr, np.array([1.0, 0, 0]), r0)
    mujoco.mju_mulQuat(out, qp, qr)
    d.qpos[3:7] = out
    mujoco.mj_forward(m, d)
    rest_on_floor(m, d, False)


def rest_on_floor(m, d, feet_flat=True):
    """Turn the model so its feet are flat (if feet_flat), then raise or lower it till its lowest point is on the floor. qpos[0:7] is the free joint."""
    if feet_flat:
        # the feet flat on the floor and the body tilting to suit, as on the real duck: turn the whole model so the feet's mean up
        # direction is straight up (each foot's frame is level at the zero pose). Yaw is kept.
        up = sum(d.xmat[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, f)].reshape(3, 3)[:, 2] for f in ('ankle_left', 'ankle_right'))
        up /= np.linalg.norm(up)
        axis = np.cross(up, [0, 0, 1.0])
        s_, c_ = np.linalg.norm(axis), up[2]
        if s_ > 1e-6:
            turn = np.zeros(4)
            mujoco.mju_axisAngle2Quat(turn, axis / s_, math.atan2(s_, c_))
            out = np.zeros(4)
            mujoco.mju_mulQuat(out, turn, d.qpos[3:7].copy())
            d.qpos[3:7] = out
            mujoco.mj_forward(m, d)
    if mesh_points(m):
        low = min((d.geom_xmat[g].reshape(3, 3) @ v.T)[2].min() + d.geom_xpos[g][2] for g, v in mesh_points(m))
        d.qpos[2] -= low
        mujoco.mj_forward(m, d)




def table(q, cfg):
    rows = []
    for n in cfg['policy_joints'] + cfg.get('extra_joints', []):
        lo, hi = cfg['limits'].get(n, (0.0, 0.39))         # the beak: shut to open, from the spec
        if n not in q:
            continue
        v = q[n]
        flag = '' if lo - 0.02 <= v <= hi + 0.02 else '  OUTSIDE LIMITS'
        rows.append(f'  {n:16s} {math.degrees(v):+7.1f} deg   (limits {math.degrees(lo):+.0f} to {math.degrees(hi):+.0f}){flag}')
    return '\n'.join(rows)


def snapshot(m, d, path):
    """Front, side and three-quarter views, side by side."""
    from PIL import Image
    r = mujoco.Renderer(m, 480, 400)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = d.subtree_com[1]
    cam.distance = 0.55
    shots = []
    for az, el in ((180, -10), (90, -10), (140, -25)):     # front (the duck faces +x), its left side, three-quarter
        cam.azimuth, cam.elevation = az, el
        r.update_scene(d, cam)
        shots.append(r.render())
    Image.fromarray(np.hstack(shots)).save(path)
    print('saved', path)


GREEN, YELLOW, GREY = (0.15, 0.8, 0.25, 1), (1.0, 0.85, 0.0, 1), (0.55, 0.55, 0.58, 1)


class CalibView:
    """While calibrate.py runs it sends {'calib': {now, done, todo, deg, step, hint, warn}}: the joint being calibrated is drawn yellow
    (pulsing), the done ones green, the ones to do grey (each joint's moving part: the body it turns), with what to do written on screen."""

    def __init__(self, m):
        self.m = m
        self.rgba, self.mat = m.geom_rgba.copy(), m.geom_matid.copy()
        self.on = False
        self.geoms = {}
        for j in range(m.njnt):
            n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)
            if n:
                b = m.jnt_bodyid[j]
                self.geoms[n] = [g for g in range(m.ngeom) if m.geom_bodyid[g] == b]

    def show(self, v, c):
        m = self.m
        if not c:
            if self.on:
                m.geom_rgba[:], m.geom_matid[:] = self.rgba, self.mat
                self.on = False
            return []
        self.on = True
        m.geom_rgba[:], m.geom_matid[:] = self.rgba, self.mat
        pulse = 0.6 + 0.4 * abs(math.sin(time.monotonic() * 4))
        for names, col in ((c.get('done', []), GREEN), (c.get('todo', []), GREY), ([c['now']], YELLOW)):
            for n in names:
                for g in self.geoms.get(n, []):
                    m.geom_matid[g] = -1
                    m.geom_rgba[g] = [x * (pulse if col is YELLOW else 1) for x in col[:3]] + [1]
        now = c['now'].replace('_', ' ')
        top = f"CALIBRATING {c.get('step', '')}:  {now.upper()}   {c['deg']:+.1f} deg"
        how = f"put it here: {c.get('hint', '')}.   A = set this as zero,  B = keep the old zero"
        done = 'done: ' + (', '.join(x.replace('_', ' ') for x in c.get('done', [])) or '-')
        todo = 'next: ' + (', '.join(x.replace('_', ' ') for x in c.get('todo', [])) or '-')
        texts = [(mujoco.mjtFontScale.mjFONTSCALE_200, mujoco.mjtGridPos.mjGRID_TOPLEFT, top, how)]
        if c.get('warn'):
            texts.append((mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPRIGHT, 'CHECK', c['warn']))
        texts.append((mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT, done, todo))
        return texts


RED, GHOST = (0.9, 0.15, 0.1, 1), (0.25, 0.6, 1.0, 0.3)


class TargetView:
    """When the script driving the duck sends {'target': {'goal': {joint: rad}, 'tilt': [pitch, roll] deg}}: where it should be beside
    where it is. A see-through blue duck in the goal pose, feet flat (where it should be); the real one from the servos and the IMU;
    each leg and head joint green within TOL of its goal, red past it; the IMU's pitch and roll against the expected, and the joints
    that are off, on screen."""
    TOL = 1.5

    def __init__(self, m, adr, geoms):
        self.m, self.adr, self.geoms = m, adr, geoms
        self.d2 = mujoco.MjData(m)
        self.opt, self.pert = mujoco.MjvOption(), mujoco.MjvPerturb()

    def show(self, v, t, q, grav):
        if not t:
            v.user_scn.ngeom = 0
            return []
        m, goal = self.m, t['goal']
        g0, s0 = GRAV[0], SETTLE[0]
        GRAV[0], SETTLE[0] = None, False                       # the ghost: the goal pose, feet flat on the floor
        try:
            pose(m, self.d2, self.adr, goal)
        finally:
            GRAV[0], SETTLE[0] = g0, s0
        v.user_scn.ngeom = 0
        mujoco.mjv_addGeoms(m, self.d2, self.opt, self.pert, mujoco.mjtCatBit.mjCAT_DYNAMIC, v.user_scn)
        for k in range(v.user_scn.ngeom):
            v.user_scn.geoms[k].rgba[:] = GHOST
            v.user_scn.geoms[k].matid = -1
        off = {n: math.degrees(q[n] - goal[n]) for n in goal if n in q}
        for n, e in off.items():
            for gi in self.geoms.get(n, []):
                m.geom_matid[gi] = -1
                m.geom_rgba[gi] = RED if abs(e) > self.TOL else GREEN
        want = t.get('tilt', [0.0, 0.0])
        if grav:
            p = math.degrees(math.atan2(grav[0], -grav[2]))
            r = math.degrees(math.atan2(-grav[1], -grav[2]))
            ok = abs(p - want[0]) <= 1 and abs(r - want[1]) <= 1
            imu = (f"IMU {'OK' if ok else 'OFF'}",
                   f"pitch now {p:+5.1f}  should be {want[0]:+5.1f}   (+ nose down)\nroll  now {r:+5.1f}  should be {want[1]:+5.1f}   (+ right side down)")
        else:
            imu = ('IMU', 'no reading')
        bad = sorted((n for n in off if abs(off[n]) > self.TOL), key=lambda n: -abs(off[n]))
        lines = '\n'.join(f"{n.replace('_', ' '):16s} goal {math.degrees(goal[n]):+6.1f}  now {math.degrees(q[n]):+6.1f}  off {off[n]:+5.1f}"
                          + (f"  {t['mA'][n]:+5d} mA" if n in t.get('mA', {}) else '') for n in bad)
        return [(mujoco.mjtFontScale.mjFONTSCALE_200, mujoco.mjtGridPos.mjGRID_TOPRIGHT, imu[0], imu[1]),
                (mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT,
                 'JOINTS OFF' if bad else 'JOINTS', lines or f'all within {self.TOL} deg of the goal'),
                (mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPLEFT, 'blue = where it should be',
                 'solid = where it is: green on goal, red off')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--feet-flat', action='store_true', help='with --remote: place the body by its feet, flat on the floor, even when the IMU is sent')
    from duck import env
    env.load()
    ap.add_argument('--remote', nargs='?', const=os.environ.get('DUCK_HOST') or 'duck.local', help="the Pi's address[:port] (alone: DUCK_HOST from the repo root's .env): take the servo readings it sends (duck/telemetry.py) instead of a bus here")
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--snapshot', help='save one picture and exit')
    ap.add_argument('--save-pose', help='save the joint angles (rad) to a JSON and exit: sim/server.py --start takes it')
    ap.add_argument('--hz', type=float, default=30)
    ap.add_argument('--body-level', action='store_true', help='hold the body level, the feet as they fall: for a duck held in the air or on a stand')
    ap.add_argument('--settle', action='store_true', help='rest it as gravity would, on its lowest parts: the duck lying on a table (no IMU needed)')
    ap.add_argument('--no-soles', action='store_true', help='the TPU soles are not fitted: hide them and stand on the bare feet')
    a = ap.parse_args()
    cfg = load_config(a.config)
    FEET_FLAT[0] = not a.body_level
    SETTLE[0] = a.settle
    names = cfg['policy_joints'] + cfg.get('extra_joints', [])
    ids = [cfg['joints'][n]['id'] for n in names]
    extra = {}
    if a.remote:
        from duck.telemetry import Receiver
        src = Receiver(a.remote)
        print('waiting for', a.remote, flush=True)

        class _Bus:
            def close(self):
                pass
        bus = _Bus()

        def remote_ticks(_bus, _ids):                     # the Pi's latest reading, in place of the bus
            t1 = time.monotonic()
            while src.latest is None:
                if time.monotonic() - t1 > 5:
                    raise dxl.DxlError('nothing from ' + a.remote)
                time.sleep(0.05)
            msg = src.latest
            extra.clear()
            extra.update({k: v for k, v in msg.items() if k != 'ticks'})
            GRAV[0] = msg.get('grav') if not a.feet_flat else None
            return {int(k): v for k, v in msg['ticks'].items()}
    else:
        port = find_port() if a.port == 'auto' else a.port
        bus = dxl.Bus(port, timeout=0.05)
    read = remote_ticks if a.remote else read_ticks
    m, d, adr = load_model(cfg, soles=not a.no_soles)
    root_z = cfg['root_z'] + 0.05

    if a.save_pose:
        q = angles(read(bus, ids), cfg, names)
        json.dump({n: round(v, 5) for n, v in q.items()}, open(a.save_pose, 'w'), indent=1)
        print(table(q, cfg)); print('saved', a.save_pose)
        return

    if a.snapshot:
        q = angles(read(bus, ids), cfg, names)
        pose(m, d, adr, q, root_z)
        print(table(q, cfg))
        snapshot(m, d, a.snapshot)
        return

    import mujoco.viewer
    last = 0
    while True:                                          # remote: wait for the duck (the launcher streams while idle, every mode while running)
        try:
            q = angles(read(bus, ids), cfg, names)
            break
        except dxl.DxlError as e:
            if not a.remote:
                raise
            print('waiting for the duck:', e, flush=True)
    pose(m, d, adr, q, root_z)
    calib = CalibView(m)
    target = TargetView(m, adr, calib.geoms)
    shown = [False]
    with mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False) as v:
        v.cam.lookat[:] = d.subtree_com[1]             # the whole duck, from its front-left
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
        while v.is_running():
            try:
                q = angles(read(bus, ids), cfg, names)
            except dxl.DxlError as e:
                print('read failed:', e)
                time.sleep(0.2)
                continue
            with v.lock():
                pose(m, d, adr, q, root_z)
                texts = calib.show(v, extra.get('calib'))
                if extra.get('target') and not extra.get('calib'):
                    m.geom_rgba[:], m.geom_matid[:] = calib.rgba, calib.mat
                texts += target.show(v, extra.get('target'), q, extra.get('grav'))
                if not extra.get('target') and not calib.on and shown[0]:
                    m.geom_rgba[:], m.geom_matid[:] = calib.rgba, calib.mat
                if texts:
                    v.set_texts(texts)
                elif shown[0]:
                    v.clear_texts()
                shown[0] = bool(texts)
                v.cam.lookat[:] = d.subtree_com[1]          # keep the duck in the middle: turn and zoom as you like
            v.sync()
            if time.monotonic() - last > 2:
                last = time.monotonic()
                print(table(q, cfg))
                if 'grav' in extra:
                    g = extra['grav']
                    print(f"IMU gravity {g[0]:+.2f} {g[1]:+.2f} {g[2]:+.2f}  (tilt {math.degrees(math.acos(max(-1, min(1, -g[2])))):.1f} deg)")
                print()
            time.sleep(1 / a.hz)
    bus.close()


if __name__ == '__main__':
    main()
