"""Retarget human motions (Bones-Seed, already retargeted to the AgiBot X2 humanoid) onto milli, the all-Dynamixel duck.

Kinematic reference clips for later imitation training. Nothing here is physics: the checks are kinematic proxies.

    # 1. pickles -> npz (needs joblib, so another venv):  tools/x2_pkl_to_npz.py OUT/src clip.pkl ...
    # 2. retarget, check, preview (pi/.venv):
    pi/.venv/Scripts/python.exe -I tools/retarget_x2.py --src ../milli-motions/src --out ../milli-motions \
        --x2-xml ../gwbc-v6/gear_sonic/data/assets/robot_description/mjcf/x2_ultra.xml \
        --milli-xml ../milli-rl/src/mjlab_microduck/robot/milli_dynamixel_contact/milli.xml \
        --clips Relaxed_walk_forward_001__A057 dance_disco_fever_001__A465 ... --video preview.mp4
    pi/.venv/Scripts/python.exe -I tools/retarget_x2.py --src ... --x2-xml ... --screen   # foot/flight stats of every clip

Mapping (milli has no arms, waist or ankle roll):
- Root: the X2 pelvis path scaled by s = milli / X2 hip-pitch-axis height in each one's bent-knee stance (leg length, ~0.16); heading kept; pelvis tilt kept at half, clamped.
- Legs: each X2 sole's motion about its standing stance, scaled by s, added to milli's own (bent-knee) stance, then solved by IK
  on milli's 5-joint legs (foot position, foot pitch and yaw; roll is left to fall where it may). While an X2 foot is planted
  (low and slow), milli's foot is pinned at that contact's mean spot, flat, at the floor, so planted feet can't slide.
- Head base posture (--neck-base/--head-base): neck leaned back, face level, as the real duck stood (pi/stand_test_log.csv).
- Arms -> head, on top of that base: both hands' elevation in the torso (mean, about its clip mean) nods the head (neck 35 %, head pitch 65 %); the left-right
  difference in hand height rolls it and in hand reach yaws it.
  (head roll soft-saturates inside its +-0.24 rad.) Planted feet keep their spot but swivel with the dancer.
- Wrists -> beak: mean wrist deflection of both hands, above the clip's own 25th percentile, x1.5, opens the beak 0..0.39 rad.
- Everything is clipped to milli's limits (knee stop 1.1 rad) and rate-limited to the XL330's 10.8 rad/s.
Bones-Seed data is under its own licence: the output stays local (default ../milli-motions), never in the repo.
"""
import argparse
import json
import os
import sys

import mujoco
import numpy as np
from scipy.spatial import ConvexHull, Delaunay
from scipy.spatial.transform import Rotation as R, Slerp

FPS = 50.0
VMAX = 10.8                 # rad/s, XL330 no-load at 5 V (the task's limit)
BEAK = (0.0, 0.39)
LEGS = ['hip_yaw', 'hip_roll', 'hip_pitch', 'knee', 'ankle']
HEAD = ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll']
JOINTS = [f'left_{j}' for j in LEGS] + [f'right_{j}' for j in LEGS] + HEAD
X2_SOLE = np.array([0.0225, 0.0, -0.073])           # sole centre in the X2's ankle_roll_link (foot spheres x -0.065..0.11, z -0.068 - r)
CONTACT_Z = 0.025                                    # X2 sole height (m) and speed (m/s) for "planted"
CONTACT_V = 0.6      # generous: a swivel on the ball or heel moves the sole centre quickly without lifting
X2_DEFAULT = {'left_hip_pitch_joint': -0.312, 'right_hip_pitch_joint': -0.312, 'left_knee_joint': 0.669,
              'right_knee_joint': 0.669, 'left_ankle_pitch_joint': -0.363, 'right_ankle_pitch_joint': -0.363}


# ---------------------------------------------------------------- source
def load_clip(path):
    z = np.load(path)
    fps = float(z['fps'])
    pos, quat, dof = z['root_pos'], z['root_quat_xyzw'], z['dof']
    T = len(dof)
    t0 = np.arange(T) / fps
    t1 = np.minimum(np.arange(0, t0[-1] + 1e-9, 1.0 / FPS), t0[-1])
    interp = lambda a: np.stack([np.interp(t1, t0, a[:, i]) for i in range(a.shape[1])], 1)
    rot = Slerp(t0, R.from_quat(quat))(t1)
    return dict(pos=interp(pos), rot=rot, dof=interp(dof), src_fps=fps)


class X2:
    def __init__(self, xml):
        self.m = mujoco.MjModel.from_xml_path(xml)
        self.d = mujoco.MjData(self.m)
        self.b = {n: self.m.body(n).id for n in ['pelvis', 'torso_link', 'left_ankle_roll_link', 'right_ankle_roll_link',
                                                 'left_shoulder_pitch_link', 'right_shoulder_pitch_link',
                                                 'left_wrist_roll_link', 'right_wrist_roll_link']}
        self.jn = [self.m.joint(i).name for i in range(1, self.m.njnt)]   # MuJoCo order = the pickles' dof order
        assert len(self.jn) == 31, self.jn

    def set(self, pos, rot, dof):
        self.d.qpos[:3] = pos
        self.d.qpos[3:7] = np.roll(rot.as_quat(), 1)
        self.d.qpos[7:] = dof
        mujoco.mj_kinematics(self.m, self.d)

    def sole(self, side):
        b = self.b[f'{side}_ankle_roll_link']
        return self.d.xpos[b] + self.d.xmat[b].reshape(3, 3) @ X2_SOLE, self.d.xmat[b].reshape(3, 3).copy()

    def fk(self, clip):
        T = len(clip['dof'])
        out = {k: np.zeros((T, 3)) for k in ['pelvis', 'lsole', 'rsole', 'lhand', 'rhand']}
        out.update(lfoot_R=np.zeros((T, 3, 3)), rfoot_R=np.zeros((T, 3, 3)), torso_R=np.zeros((T, 3, 3)))
        for t in range(T):
            self.set(clip['pos'][t], clip['rot'][t], clip['dof'][t])
            out['pelvis'][t] = self.d.xpos[self.b['pelvis']]
            for s in ('left', 'right'):
                p, Rm = self.sole(s)
                out[s[0] + 'sole'][t], out[s[0] + 'foot_R'][t] = p, Rm
                tR = self.d.xmat[self.b['torso_link']].reshape(3, 3)
                out[s[0] + 'hand'][t] = tR.T @ (self.d.xpos[self.b[f'{s}_wrist_roll_link']] -
                                               self.d.xpos[self.b[f'{s}_shoulder_pitch_link']])
            out['torso_R'][t] = self.d.xmat[self.b['torso_link']].reshape(3, 3)
        floor = np.percentile(np.minimum(out['lsole'][:, 2], out['rsole'][:, 2]), 5)
        for k in ('pelvis', 'lsole', 'rsole'):
            out[k][:, 2] -= floor
        out['floor'] = floor
        for s in 'lr':
            v = np.gradient(out[s + 'sole'][:, :2], 1 / FPS, axis=0)
            out[s + 'contact'] = (out[s + 'sole'][:, 2] < CONTACT_Z) & (np.linalg.norm(v, axis=1) < CONTACT_V)
            out[s + 'contact'] = clean_runs(out[s + 'contact'])
        return out

    def stance(self):
        """X2 default standing pose, pelvis at the origin: sole positions and pelvis height above the soles."""
        dof = np.zeros(31)
        for n, v in X2_DEFAULT.items():
            dof[self.jn.index(n)] = v
        self.set(np.zeros(3), R.identity(), dof)
        l, r = self.sole('left')[0], self.sole('right')[0]
        hip = self.d.xanchor[self.m.joint('left_hip_pitch_joint').id][2]
        return dict(lsole=l, rsole=r, height=-min(l[2], r[2]), hip_height=hip - min(l[2], r[2]))


def clean_runs(c, min_len=4):
    """Drop contact runs and gaps shorter than min_len frames (flicker)."""
    c = c.copy()
    for val in (True, False):
        i = 0
        while i < len(c):
            j = i
            while j < len(c) and c[j] == c[i]:
                j += 1
            if c[i] == val and j - i < min_len and i > 0 and j < len(c):
                c[i:j] = not val
            i = j
    return c


def runs(c):
    out, i = [], 0
    while i < len(c):
        j = i
        while j < len(c) and c[j] == c[i]:
            j += 1
        if c[i]:
            out.append((i, j))
        i = j
    return out


# ---------------------------------------------------------------- milli
class Milli:
    def __init__(self, xml, home_json, scene=False):
        spec = mujoco.MjSpec.from_file(xml)
        jaw = spec.body('jaw')
        if jaw is not None and not jaw.joints:      # the beak, as pi/twin.py adds it
            jaw.add_joint(name='beak', type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 1, 0], range=list(BEAK))
        if scene:
            add_scene(spec)
        self.m = spec.compile()
        self.d = mujoco.MjData(self.m)
        home = json.load(open(home_json))
        self.home = home
        self.names = JOINTS + ['beak']
        self.qadr = np.array([self.m.joint(n).qposadr[0] for n in self.names])
        self.dadr = np.array([self.m.joint(n).dofadr[0] for n in self.names])
        self.lo = np.array([self.m.joint(n).range[0] for n in self.names])
        self.hi = np.array([self.m.joint(n).range[1] for n in self.names])
        self.q_home = np.array([home['joint_pos'].get(n, 0.0) for n in self.names])
        self.root_z = home['root_z']
        self.site = {s: self.m.site(f'{s}_foot').id for s in ('left', 'right')}
        self.foot_box = {s: self.m.geom(f'{s}_foot_collision').id for s in ('left', 'right')}
        self.ankle = {s: self.m.body(f'ankle_{s}').id for s in ('left', 'right')}
        self.set(np.array([0, 0, self.root_z]), np.array([1., 0, 0, 0]), self.q_home)
        self.home_site = {s: self.d.site_xpos[self.site[s]].copy() for s in self.site}
        sole_z = min(self.home_site['left'][2], self.home_site['right'][2])
        self.root_z -= sole_z                     # sit the home pose's soles exactly on z = 0
        self.set(np.array([0, 0, self.root_z]), np.array([1., 0, 0, 0]), self.q_home)
        self.home_site = {s: self.d.site_xpos[self.site[s]].copy() for s in self.site}
        self.home_contacts = self.self_contacts(0.0)
        self.hip_height = self.d.xanchor[self.m.joint('left_hip_pitch').id][2]     # hip pitch axis above the soles
        # IK keeps each knee on its bending side of straight (home's side), so it can't flip through to a backward knee
        self.ik_lo, self.ik_hi = self.lo.copy(), self.hi.copy()
        for side in ('left', 'right'):
            i = self.names.index(f'{side}_knee')
            if self.q_home[i] > 0:
                self.ik_lo[i] = 0.02
            else:
                self.ik_hi[i] = -0.02

    def set(self, pos, quat_wxyz, q):
        self.d.qpos[:3] = pos
        self.d.qpos[3:7] = quat_wxyz
        self.d.qpos[self.qadr] = q
        mujoco.mj_kinematics(self.m, self.d)
        mujoco.mj_comPos(self.m, self.d)

    def ik(self, q0, targets, iters=30):
        """Leg IK: targets[side] = (pos, R_target). Root already set in self.d. Returns q (legs only changed), clamped flags."""
        q = q0.copy()
        legs = {'left': np.arange(0, 5), 'right': np.arange(5, 10)}
        w_rot = np.array([0.6, 1.0, 1.0]) * 0.03        # roll, pitch, yaw (world, near enough): metres vs radians
        for _ in range(iters):
            self.d.qpos[self.qadr] = q
            mujoco.mj_kinematics(self.m, self.d)
            mujoco.mj_comPos(self.m, self.d)
            done = True
            for s, idx in legs.items():
                p_t, R_t = targets[s]
                sid = self.site[s]
                e_p = p_t - self.d.site_xpos[sid]
                R_c = self.d.site_xmat[sid].reshape(3, 3)
                e_r = R.from_matrix(R_t @ R_c.T).as_rotvec()
                # express the rotation error in the target yaw frame so roll/pitch weights mean foot roll/pitch
                yaw = np.arctan2(R_t[1, 0], R_t[0, 0])
                Ry = R.from_euler('z', yaw).as_matrix()
                jp = np.zeros((3, self.m.nv)); jr = np.zeros((3, self.m.nv))
                mujoco.mj_jacSite(self.m, self.d, jp, jr, sid)
                cols = self.dadr[idx]
                J = np.vstack([jp[:, cols], (w_rot[:, None] * (Ry.T @ jr[:, cols]))])
                e = np.concatenate([e_p, w_rot * (Ry.T @ e_r)])
                if np.linalg.norm(e_p) > 2e-4 or np.linalg.norm(e[3:]) > 3e-4:
                    done = False
                lam = 1e-4
                dq = J.T @ np.linalg.solve(J @ J.T + lam * np.eye(6), e)
                q[idx] = np.clip(q[idx] + dq, self.ik_lo[idx], self.ik_hi[idx])
            if done:
                break
        return q

    def self_contacts(self, tol=0.001):
        mujoco.mj_collision(self.m, self.d)
        pairs = {}
        for i in range(self.d.ncon):
            c = self.d.contact[i]
            if c.dist < -tol:
                b1, b2 = self.m.geom_bodyid[c.geom1], self.m.geom_bodyid[c.geom2]
                if b1 == 0 or b2 == 0:
                    continue
                k = tuple(sorted((self.m.body(b1).name, self.m.body(b2).name)))
                pairs[k] = min(pairs.get(k, 0.0), c.dist)
        return pairs      # {(body, body): deepest penetration (m, negative)}

    def foot_corners(self, s):
        g = self.foot_box[s]
        c, Rm, h = self.d.geom_xpos[g], self.d.geom_xmat[g].reshape(3, 3), self.m.geom_size[g]
        return np.array([c + Rm @ np.array([sx * h[0], sy * h[1], -h[2]]) for sx in (-1, 1) for sy in (-1, 1)])


def add_scene(spec, floor=True):
    spec.visual.headlight.ambient = [0.4, 0.4, 0.4]
    spec.visual.headlight.diffuse = [0.6, 0.6, 0.6]
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 960
    if not floor:
        return
    tex = spec.add_texture(name='rt_grid', type=mujoco.mjtTexture.mjTEXTURE_2D, builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                           rgb1=[0.82, 0.84, 0.86], rgb2=[0.70, 0.73, 0.76], width=300, height=300)
    mat = spec.add_material(name='rt_grid', texrepeat=[1, 1], reflectance=0.05)
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = 'rt_grid'
    spec.add_texture(name='rt_sky', type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                     rgb1=[0.85, 0.9, 0.97], rgb2=[0.55, 0.65, 0.8], width=256, height=256)
    spec.worldbody.add_geom(name='rt_floor', type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05], material='rt_grid',
                            contype=0, conaffinity=0)
    spec.worldbody.add_light(pos=[0, 0, 3], dir=[0, 0, -1], diffuse=[0.5, 0.5, 0.5])


# ---------------------------------------------------------------- retarget
def smooth(x, k=5):
    if k <= 1:
        return x
    ker = np.ones(k) / k
    pad = np.pad(x, [(k // 2, k // 2)] + [(0, 0)] * (x.ndim - 1), mode='edge')
    return np.apply_along_axis(lambda a: np.convolve(a, ker, mode='valid'), 0, pad)


def yaw_of(Rm):
    return np.arctan2(Rm[..., 1, 0], Rm[..., 0, 0])


def retarget(name, clip, x2, milli, ref, s, step=0.8, crouch=0.004, head_base=(0.737, 0.749)):
    sh = s * step                       # horizontal scale: shorter steps, milli's crouch leaves little reach
    fk = x2.fk(clip)
    T = len(clip['dof'])
    pel_R = clip['rot'].as_matrix()
    heading = np.unwrap(yaw_of(pel_R))
    # pelvis tilt about its heading frame, half of it, clamped to 0.2 rad
    tilt = np.array([(R.from_euler('z', -h) * clip['rot'][t]).as_euler('xyz')[:2] for t, h in enumerate(heading)])
    tilt = np.clip(0.5 * tilt, -0.2, 0.2)
    root_q = np.array([R.from_euler('zyx', [heading[t], tilt[t, 1], tilt[t, 0]]).as_quat() for t in range(T)])
    root_q = np.roll(root_q, 1, axis=1)                                   # wxyz
    start = fk['pelvis'][0, :2].copy()
    root_p = np.zeros((T, 3))
    root_p[:, :2] = sh * (fk['pelvis'][:, :2] - start)
    # height: milli's own stance height plus the dancer's bob about their usual height; never higher than 4 mm above
    # the stance (milli's crouch has little knee left to straighten)
    root_p[:, 2] = np.minimum(milli.root_z - crouch + s * (fk['pelvis'][:, 2] - np.median(fk['pelvis'][:, 2])), milli.root_z)

    # foot targets: X2 sole about its stance, scaled, added to milli's stance (in the heading frame)
    tgt_p, tgt_yaw, tgt_pitch = {}, {}, {}
    for side in ('left', 'right'):
        k = side[0]
        home_rel = milli.home_site[side] - np.array([0, 0, milli.root_z])
        ref_rel = ref[k + 'sole'] - np.array([0, 0, 0])
        p = np.zeros((T, 3))
        x2_rel = np.array([R.from_euler('z', heading[t]).as_matrix().T @ (fk[k + 'sole'][t] - fk['pelvis'][t])
                           for t in range(T)])
        # sideways: about the dancer's own usual stance width, halved; milli has no ankle roll, so any hip roll tilts its sole
        ref_rel = ref_rel.copy(); ref_rel[1] = np.median(x2_rel[:, 1])
        for t in range(T):
            Rz = R.from_euler('z', heading[t]).as_matrix()
            d = s * (x2_rel[t] - ref_rel)
            d[:2] *= step
            d[1] *= 0.5
            rel = home_rel + d
            rel[2] = 0.0
            p[t, :2] = root_p[t, :2] + (Rz @ rel)[:2]
            p[t, 2] = max(0.0, s * fk[k + 'sole'][t, 2]) + milli.home_site[side][2]
        fyaw = np.unwrap(yaw_of(fk[k + 'foot_R']))
        rel_yaw = fyaw - heading
        fyaw = heading + (rel_yaw - np.median(rel_yaw))          # drop the dancer's habitual toe-out, keep the swivels
        fpitch = np.array([R.from_matrix(Rm).as_euler('zyx')[1] for Rm in fk[k + 'foot_R']])
        # pin planted feet: the contact's mean spot, flat; blend in and out over 6 frames
        c = fk[k + 'contact']
        off = np.zeros((T, 3)); offyaw = np.zeros(T); w = np.zeros(T)
        for a, b in runs(c):
            mp = p[a:b].mean(0)
            off[a:b] = mp - p[a:b]                 # position pinned; yaw follows the dancer (swivels kept)
            w[a:b] = 1
            for i in range(1, 7):
                f = 1 - i / 7
                if a - i >= 0 and not c[a - i]:
                    off[a - i] = f * (mp - p[a - i]) if w[a - i] == 0 else off[a - i]
                if b - 1 + i < T and not c[b - 1 + i]:
                    off[b - 1 + i] = f * (mp - p[b - 1 + i]) if w[b - 1 + i] == 0 else off[b - 1 + i]
        p = p + off
        p[c, 2] = milli.home_site[side][2]
        fpitch = np.where(c, 0.0, np.clip(0.5 * fpitch, -0.3, 0.3))   # swing: half the X2's toe-off/heel pitch, at most 0.3 rad
        tgt_p[side], tgt_yaw[side], tgt_pitch[side] = p, fyaw + offyaw, smooth(fpitch, 3)

    # head and beak from the hands and wrists
    lh, rh = fk['lhand'], fk['rhand']
    arm_len = np.median(np.r_[np.linalg.norm(lh, axis=1), np.linalg.norm(rh, axis=1)])
    elev = lambda h: np.arctan2(h[:, 0], -h[:, 2])            # 0 hanging, +pi/2 reaching forward, ~pi overhead
    elev_l = np.arccos(np.clip(-lh[:, 2] / np.linalg.norm(lh, axis=1), -1, 1))
    elev_r = np.arccos(np.clip(-rh[:, 2] / np.linalg.norm(rh, axis=1), -1, 1))
    nod = 0.35 * (0.5 * (elev_l + elev_r) - 0.35)              # head up as the arms rise (rest ~0.35 rad)
    nod = smooth(nod, 5)
    nod = nod - nod.mean()             # about the base posture: the face is level on average, the nod swings it up and down
    roll = smooth(0.22 * np.tanh(0.3 / 0.22 * (lh[:, 2] - rh[:, 2]) / arm_len), 5)   # soft-saturates inside +-0.24    # left hand higher -> head tilts toward... the higher hand
    yawh = smooth(0.5 * (lh[:, 0] - rh[:, 0]) / arm_len, 5)    # left hand further forward -> look right (turn from it)
    jn = x2.jn
    wl = np.hypot(clip['dof'][:, jn.index('left_wrist_pitch_joint')], clip['dof'][:, jn.index('left_wrist_roll_joint')])
    wr = np.hypot(clip['dof'][:, jn.index('right_wrist_pitch_joint')], clip['dof'][:, jn.index('right_wrist_roll_joint')])
    w = 0.5 * (wl + wr)
    beak = smooth(np.clip(1.5 * (w - np.percentile(w, 25)), *BEAK), 5)   # wrist flicks about the clip's resting bend

    # signs on milli: measure which way each head joint moves the beak tip
    sg = head_signs(milli)
    Q = np.zeros((T, len(milli.names)))
    clamped = np.zeros((T, len(milli.names)), bool)
    q = milli.q_home.copy()
    for t in range(T):
        milli.set(root_p[t], root_q[t], q)
        targets = {}
        for side in ('left', 'right'):
            Rt = R.from_euler('zy', [tgt_yaw[side][t], tgt_pitch[side][t]]).as_matrix()
            targets[side] = (tgt_p[side][t], Rt)
        q = milli.ik(q, targets)
        qh = np.array([head_base[0] + sg['pitch_n'] * 0.35 * nod[t], head_base[1] + sg['pitch_h'] * 0.65 * nod[t], sg['yaw'] * yawh[t],
                       sg['roll'] * roll[t]])
        q[10:14] = qh
        q[14] = beak[t]
        raw = q.copy()
        q = np.clip(q, milli.lo, milli.hi)
        # clipped: a head joint asked past its limit, or a leg joint the IK pinned at a bound (incl. the knee stop)
        clamped[t] = np.abs(raw - q) > 1e-6
        clamped[t, :10] |= (np.abs(q[:10] - milli.ik_lo[:10]) < 1e-3) | (np.abs(q[:10] - milli.ik_hi[:10]) < 1e-3)
        Q[t] = q
    # speed limit
    v_raw = np.abs(np.diff(Q, axis=0)) * FPS
    fast = np.r_[False, (v_raw > VMAX).any(1)]
    Ql = Q.copy()
    for t in range(1, T):
        Ql[t] = Ql[t - 1] + np.clip(Ql[t] - Ql[t - 1], -VMAX / FPS, VMAX / FPS)
    return dict(name=name, q=Ql, root_pos=root_p, root_quat=root_q, clamped=clamped, fast=fast,
                lcontact=fk['lcontact'], rcontact=fk['rcontact'], fk=fk, clip=clip)


def face_pitch(milli, neck, head):
    """Pitch of the head (jaw_soft body's x axis) above horizontal at the home stance with this neck/head pitch."""
    q = milli.q_home.copy()
    q[milli.names.index('neck_pitch')], q[milli.names.index('head_pitch')] = neck, head
    milli.set(np.array([0, 0, milli.root_z]), np.array([1., 0, 0, 0]), q)
    x = milli.d.xmat[milli.m.body('jaw_soft').id].reshape(3, 3)[:, 0]
    return np.arctan2(x[2], np.hypot(x[0], x[1]))


def head_signs(milli):
    tip = milli.m.site('mouth_tip').id
    def tipz(q):
        milli.set(np.array([0, 0, milli.root_z]), np.array([1., 0, 0, 0]), q)
        return milli.d.site_xpos[tip].copy()
    base = tipz(milli.q_home)
    out = {}
    for key, j, axis in (('pitch_n', 'neck_pitch', 2), ('pitch_h', 'head_pitch', 2), ('yaw', 'head_yaw', 1)):
        q = milli.q_home.copy(); q[milli.names.index(j)] += 0.1
        out[key] = 1.0 if tipz(q)[axis] > base[axis] else -1.0     # + = beak up / beak to the left
    # roll: + = head's left ear down (tilt toward the left)
    q = milli.q_home.copy(); q[milli.names.index('head_roll')] += 0.1
    milli.set(np.array([0, 0, milli.root_z]), np.array([1., 0, 0, 0]), q)
    Rh = milli.d.xmat[milli.m.body('jaw_soft').id].reshape(3, 3)
    out['roll'] = 1.0 if Rh[2, 1] < 0 else -1.0
    out['yaw'] *= -1.0      # yawh > 0 means look right
    return out


# ---------------------------------------------------------------- checks
def check(res, milli):
    q, T = res['q'], len(res['q'])
    ok_lim = ~res['clamped'].any(1)
    ok_speed_raw = ~res['fast']
    v = np.r_[np.zeros((1, q.shape[1])), np.abs(np.diff(q, axis=0)) * FPS]
    ok_speed = (v <= VMAX + 1e-6).all(1)
    foot = {s: np.zeros((T, 3)) for s in ('left', 'right')}
    ok_com, ok_col, ok_floor = np.ones(T, bool), np.ones(T, bool), np.ones(T, bool)
    com = np.zeros((T, 3)); support_n = np.zeros(T, int)
    new_pairs = {}
    for t in range(T):
        milli.set(res['root_pos'][t], res['root_quat'][t], q[t])
        corners = []
        for s in foot:
            foot[s][t] = milli.d.site_xpos[milli.site[s]]
            cs = milli.foot_corners(s)
            if cs[:, 2].min() < 0.004:
                corners.append(cs[:, :2])
            if cs[:, 2].min() < -0.003:
                ok_floor[t] = False
        com[t] = milli.d.subtree_com[1]
        support_n[t] = len(corners)
        if not corners:
            ok_com[t] = False
        else:
            pts = np.vstack(corners)
            try:
                ok_com[t] = Delaunay(pts[ConvexHull(pts).vertices]).find_simplex(com[t, :2]) >= 0
            except Exception:
                ok_com[t] = False
        pairs = {k: v for k, v in milli.self_contacts(0.001).items() if k not in milli.home_contacts}
        if pairs:
            ok_col[t] = False
            for p, dep in pairs.items():
                n, d0 = new_pairs.get(p, (0, 0.0))
                new_pairs[p] = (n + 1, min(d0, dep))
    ok_slide = np.ones(T, bool)
    for s in foot:
        vel = np.r_[0, np.linalg.norm(np.diff(foot[s][:, :2], axis=0), axis=1) * FPS]
        down = foot[s][:, 2] < milli.home_site[s][2] + 0.003
        down_prev = np.r_[False, down[:-1]]
        ok_slide &= ~(down & down_prev & (vel > 0.02))     # 0.4 mm per frame
    per_joint_clamp = {n: float(res['clamped'][:, i].mean()) for i, n in enumerate(milli.names) if res['clamped'][:, i].any()}
    knee_stop = float(np.mean((np.abs(q[:, milli.names.index('left_knee')] - 1.1) < 1e-3) |
                              (np.abs(q[:, milli.names.index('right_knee')] + 1.1) < 1e-3)))
    allok = ok_lim & ok_speed_raw & ok_slide & ok_com & ok_col & ok_floor
    return dict(frames=T, seconds=T / FPS, limits=ok_lim.mean(), speed_raw=ok_speed_raw.mean(), speed=ok_speed.mean(),
                slide=ok_slide.mean(), com=ok_com.mean(), collision=ok_col.mean(), floor=ok_floor.mean(), all=allok.mean(),
                flight=float((support_n == 0).mean()), clamp_by_joint=per_joint_clamp, knee_stop=knee_stop,
                collision_pairs={f'{a}/{b}': f'{n} frames, deepest {-d * 1000:.1f} mm' for (a, b), (n, d) in
                                 sorted(new_pairs.items(), key=lambda x: -x[1][0])[:6]},
                vmax=float(v.max()), per_frame=dict(lim=ok_lim, speed=ok_speed_raw, slide=ok_slide, com=ok_com, col=ok_col,
                                                    floor=ok_floor), com_xyz=com)


# ---------------------------------------------------------------- output
def save(res, out):
    np.savez(os.path.join(out, res['name'] + '.npz'), fps=FPS, joint_names=np.array(res['names']), joint_pos=res['q'][:, :14],
             beak=res['q'][:, 14], root_pos=res['root_pos'], root_quat_wxyz=res['root_quat'],
             left_contact=res['lcontact'], right_contact=res['rcontact'], source_clip=res['name'],
             note='kinematic retarget of a Bones-Seed X2 clip; joint_pos in milli.xml joint order/signs; not for redistribution')


def render(results, x2xml, milli, path, w=480, h=480):
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw, ImageFont
    xs = mujoco.MjSpec.from_file(x2xml)
    add_scene(xs, floor=False)
    xm = xs.compile(); xd = mujoco.MjData(xm)
    mm, md = milli.m, milli.d
    rx, rm = mujoco.Renderer(xm, h, w), mujoco.Renderer(mm, h, w)
    opt = mujoco.MjvOption()
    try:
        font = ImageFont.truetype('arial.ttf', 15); big = ImageFont.truetype('arialbd.ttf', 17)
    except OSError:
        font = big = ImageFont.load_default()
    wr = imageio.get_writer(path, fps=int(FPS), codec='libx264', quality=7, macro_block_size=8)
    for res in results:
        clip, chk = res['clip'], res['check']
        cx = mujoco.MjvCamera(); cx.distance, cx.elevation, cx.azimuth = 3.2, -12, 135
        cm = mujoco.MjvCamera(); cm.distance, cm.elevation, cm.azimuth = 0.85, -12, 135
        fx = fm = None
        for t in range(len(res['q'])):
            xd.qpos[:3] = clip['pos'][t]; xd.qpos[2] -= res['fk']['floor']
            xd.qpos[3:7] = np.roll(clip['rot'][t].as_quat(), 1); xd.qpos[7:] = clip['dof'][t]
            mujoco.mj_kinematics(xm, xd)
            milli.set(res['root_pos'][t], res['root_quat'][t], res['q'][t])
            px, pm = xd.qpos[:3].copy(), md.qpos[:3].copy()
            fx = px if fx is None else 0.9 * fx + 0.1 * px      # smooth follow
            fm = pm if fm is None else 0.9 * fm + 0.1 * pm
            cx.lookat[:] = [fx[0], fx[1], 0.75]; cm.lookat[:] = [fm[0], fm[1], 0.15]
            rx.update_scene(xd, cx, opt); rm.update_scene(md, cm, opt)
            img = np.concatenate([rx.render(), rm.render()], axis=1)
            im = Image.fromarray(img); dr = ImageDraw.Draw(im)
            dr.text((10, 8), res['name'], fill=(255, 255, 255), font=big)
            dr.text((10, 30), 'source: Bones-Seed on the X2 (its own scale)', fill=(230, 230, 230), font=font)
            dr.text((w + 10, 8), 'milli (all-Dynamixel), KINEMATIC playback, not physics', fill=(150, 0, 0), font=big)
            pf = chk['per_frame']
            flags = [(k, bool(pf[k][t])) for k in ('lim', 'speed', 'slide', 'com', 'col')]
            x0 = w + 10
            for k, good in flags:
                dr.rectangle([x0, h - 26, x0 + 58, h - 8], fill=(60, 160, 80) if good else (200, 50, 50))
                dr.text((x0 + 6, h - 25), k, fill=(255, 255, 255), font=font)
                x0 += 64
            dr.text((w + 10, h - 46), f'beak {res["q"][t, 14]:.2f} rad   t {t / FPS:5.2f} s', fill=(30, 30, 30), font=font)
            wr.append_data(np.asarray(im))
    wr.close()


def screen(src, x2):
    rows = []
    for f in sorted(os.listdir(src)):
        if not f.endswith('.npz'):
            continue
        c = load_clip(os.path.join(src, f))
        fk = x2.fk(c)
        T = len(c['dof'])
        both_up = ~(fk['lcontact'] | fk['rcontact'])
        rows.append((f[:-4], T / FPS, both_up.mean(), fk['pelvis'][:, 2].min(), fk['pelvis'][:, 2].max(),
                     max(fk['lsole'][:, 2].max(), fk['rsole'][:, 2].max()),
                     np.degrees(np.ptp(np.unwrap(yaw_of(c['rot'].as_matrix()))))))
    print(f'{"clip":58s} {"sec":>5s} {"noContact":>9s} {"pelvZmin":>8s} {"pelvZmax":>8s} {"footZmax":>8s} {"turn°":>6s}')
    for r in rows:
        print(f'{r[0]:58s} {r[1]:5.1f} {r[2]:9.2f} {r[3]:8.2f} {r[4]:8.2f} {r[5]:8.2f} {r[6]:6.0f}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True, help='folder of .npz from tools/x2_pkl_to_npz.py')
    ap.add_argument('--x2-xml', required=True)
    ap.add_argument('--milli-xml')
    ap.add_argument('--home-json', help='default: home.json beside --milli-xml')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'milli-motions'))
    ap.add_argument('--clips', nargs='*')
    ap.add_argument('--video')
    ap.add_argument('--seconds', type=float, default=0, help='trim each clip to this many seconds (0 = whole)')
    ap.add_argument('--screen', action='store_true')
    ap.add_argument('--step', type=float, default=0.8, help='horizontal (step length, root path) scale on top of s')
    ap.add_argument('--crouch', type=float, default=0.004, help='m lower than the home stance, for reach')
    ap.add_argument('--neck-base', type=float, default=0.737,
                    help='rad, base neck_pitch (+ leans back); default: as the real duck stood, pi/stand_test_log.csv')
    ap.add_argument('--head-base', type=float, default=0.749, help='rad, base head_pitch (+ nose down); default levels the face')
    a = ap.parse_args()
    x2 = X2(a.x2_xml)
    if a.screen:
        screen(a.src, x2)
        return
    milli = Milli(a.milli_xml, a.home_json or os.path.join(os.path.dirname(a.milli_xml), 'home.json'), scene=bool(a.video))
    ref = x2.stance()
    s = milli.hip_height / ref['hip_height']
    print(f'scale s = {s:.3f}  (hip pitch axis above the soles in each stance: milli {milli.hip_height:.3f} m / X2 {ref["hip_height"]:.3f} m)')
    os.makedirs(a.out, exist_ok=True)
    print(f'base head posture: neck {a.neck_base:+.3f}, head {a.head_base:+.3f} rad -> face pitch '
          f'{np.degrees(face_pitch(milli, a.neck_base, a.head_base)):+.1f} deg (+ = nose up)')
    results, report = [], {}
    for name in a.clips:
        clip = load_clip(os.path.join(a.src, name + '.npz'))
        if a.seconds:
            n = int(a.seconds * FPS)
            clip = dict(pos=clip['pos'][:n], rot=clip['rot'][:n], dof=clip['dof'][:n], src_fps=clip['src_fps'])
        res = retarget(name, clip, x2, milli, ref, s, a.step, a.crouch, (a.neck_base, a.head_base))
        res['names'] = milli.names[:14]
        res['check'] = check(res, milli)
        save(res, a.out)
        c = res['check']
        report[name] = {k: v for k, v in c.items() if k not in ('per_frame', 'com_xyz')}
        print(f"{name}: {c['seconds']:.1f} s  pass all {c['all']:.0%} | limits {c['limits']:.0%} speed {c['speed_raw']:.0%} "
              f"slide {c['slide']:.0%} CoM {c['com']:.0%} no-collision {c['collision']:.0%} floor {c['floor']:.0%} "
              f"flight {c['flight']:.0%} knee-stop {c['knee_stop']:.0%}\n    clamped: "
              + ', '.join(f'{k} {v:.0%}' for k, v in c['clamp_by_joint'].items()) + f"\n    collisions: {c['collision_pairs']}")
        results.append(res)
    json.dump(dict(scale=s, fps=FPS, clips=report), open(os.path.join(a.out, 'checks.json'), 'w'), indent=1, default=float)
    if a.video:
        render(results, a.x2_xml, milli, a.video)
        print('video', a.video)


if __name__ == '__main__':
    main()
