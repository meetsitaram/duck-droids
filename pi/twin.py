"""The digital twin: the real duck's pose, read from its servos, shown on the MuJoCo model. Read only: it never writes to a servo,
so nothing moves and torque stays as it is. Pose the duck by hand, torque off, and compare.

  python twin.py                     a MuJoCo window, following the duck live, and a table of joint angles every 2 s
  python twin.py --snapshot pose.png  one picture from three sides, then exit
  python twin.py --port COM3          the bus board's port, if more than one is found
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
FEET_FLAT = [True]   # turn the model so its feet are flat; --body-level holds the body level instead (the duck held in the air)


def angles(raw, cfg, names):
    """Joint angles (rad) from raw ticks. A reading with torque off can be more than a turn off: wrap it to the turn nearest the centre."""
    q = {}
    for n in names:
        j = cfg['joints'][n]
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
    if free:
        rest_on_floor(m, d, FEET_FLAT[0])


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--snapshot', help='save one picture and exit')
    ap.add_argument('--save-pose', help='save the joint angles (rad) to a JSON and exit: sim/server.py --start takes it')
    ap.add_argument('--hz', type=float, default=30)
    ap.add_argument('--body-level', action='store_true', help='hold the body level, the feet as they fall: for a duck held in the air or on a stand')
    ap.add_argument('--no-soles', action='store_true', help='the TPU soles are not fitted: hide them and stand on the bare feet')
    a = ap.parse_args()
    cfg = load_config(a.config)
    FEET_FLAT[0] = not a.body_level
    port = find_port() if a.port == 'auto' else a.port
    bus = dxl.Bus(port, timeout=0.05)
    names = cfg['policy_joints'] + cfg.get('extra_joints', [])
    ids = [cfg['joints'][n]['id'] for n in names]
    m, d, adr = load_model(cfg, soles=not a.no_soles)
    root_z = cfg['root_z'] + 0.05

    if a.save_pose:
        q = angles(read_ticks(bus, ids), cfg, names)
        json.dump({n: round(v, 5) for n, v in q.items()}, open(a.save_pose, 'w'), indent=1)
        print(table(q, cfg)); print('saved', a.save_pose)
        return

    if a.snapshot:
        q = angles(read_ticks(bus, ids), cfg, names)
        pose(m, d, adr, q, root_z)
        print(table(q, cfg))
        snapshot(m, d, a.snapshot)
        return

    import mujoco.viewer
    last = 0
    q = angles(read_ticks(bus, ids), cfg, names)
    pose(m, d, adr, q, root_z)
    with mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False) as v:
        v.cam.lookat[:] = d.subtree_com[1]             # the whole duck, from its front-left
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
        while v.is_running():
            try:
                q = angles(read_ticks(bus, ids), cfg, names)
            except dxl.DxlError as e:
                print('read failed:', e)
                time.sleep(0.2)
                continue
            with v.lock():
                pose(m, d, adr, q, root_z)
                v.cam.lookat[:] = d.subtree_com[1]          # keep the duck in the middle: turn and zoom as you like
            v.sync()
            if time.monotonic() - last > 2:
                last = time.monotonic()
                print(table(q, cfg), '\n')
            time.sleep(1 / a.hz)
    bus.close()


if __name__ == '__main__':
    main()
