"""Other ways for the sprung sole to squish, beside the hexagons (the user, 2026-11-23: hexagons are the bestagons, too strong; try swirls
and what others use). Each is a 2D pattern in the sole's side profile, run straight through its width, so it prints on its side like the hex
sole (tools/suspension_sole.py builds the rest: plates, screw bosses and bores, flat sides, end cuts).

  wave   S-shaped struts (one full sine over the height), neighbours mirrored: an S bends along its whole length instead of bracing like a straight wall
  bow    C-shaped struts bowed alternately left and right, ( ) ( ): pressed, they bow further, as a leaf spring or the curved ribs of a fin ray
  ring   elliptical rings standing between the plates: a ring squeezed across its height flexes all round (O-ring and wave-spring style)

Stiffness comes from a small 2D beam-frame model of the actual strut centrelines (Euler-Bernoulli beams, the floor end clamped, the top pushed
down without turning or sliding), times the width. Better than the hex sole's hand formula, still not FEA: say so when quoting it. Each
pattern's wall is sized by bisection to land on the same stiffness, so they compare like for like.

  python -I tools/sole_patterns.py            writes prints/dynamixel/suspension/{L,R}_sole_{pattern}_on_side.stl and patterns.png
"""
import math
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suspension_sole as SS  # noqa: E402

TARGET = 6.5         # N/mm per sole: near the hex soft (5) and medium (7) estimates
T_RANGE = (0.45, 1.6)
PITCH = {'wave': 10.0, 'bow': 12.0, 'ring': 13.5}    # mm between strut centres: few, deep curves (a frame-model sweep, 2026-11-23)
AMP = {'wave': 3.5, 'bow': 4.5}                      # mm sideways
RING_A = 6.0         # mm, a ring's half width (its half height is the layer's): wide, flat rings flex more
CLEAR = 6.2          # mm from a screw's centre to the first strut: clear of the boss (a 4 mm-circle diamond, 5.7 mm to its tip)
N_SEG = 48


def centrelines(kind, x0, x1, z0, z1):
    """[(points (N, 2) in (x, z), closed)] for the struts between x0 and x1, from the floor plate z0 to the top plate z1."""
    H = z1 - z0
    p = PITCH[kind]
    n = int((x1 - x0) // p)
    xs = x0 + (x1 - x0 - (n - 1) * p) / 2 + p * np.arange(n)
    s = np.linspace(0, 1, N_SEG + 1)
    out = []
    for i, xc in enumerate(xs):
        sg = 1 if i % 2 == 0 else -1
        if kind == 'wave':
            out.append((np.c_[xc + sg * AMP['wave'] * np.sin(2 * math.pi * s), z0 + H * s], False))
        elif kind == 'bow':
            out.append((np.c_[xc + sg * AMP['bow'] * np.sin(math.pi * s), z0 + H * s], False))
        elif kind == 'ring':
            a = np.linspace(-math.pi / 2, 1.5 * math.pi, 2 * N_SEG + 1)[:-1]       # starts at the bottom point, so it and the top are nodes
            out.append((np.c_[xc + RING_A * np.cos(a), (z0 + z1) / 2 + H / 2 * np.sin(a)], True))
    return out


def ribbon(pts, closed, t):
    """A polyline thickened to t, as CrossSection contours."""
    P = np.asarray(pts, float)
    if closed:
        P2 = np.vstack([P[-1], P, P[0]])
    else:
        P2 = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    tang = P2[2:] - P2[:-2]
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.c_[-tang[:, 1], tang[:, 0]] * t / 2
    if closed:
        return mf.CrossSection([P + nrm, (P - nrm)[::-1]], mf.FillRule.EvenOdd)
    ext = 0.4                                               # into the plates, so the ends are buried
    P = P.copy()
    P[0] += (P[0] - P[1]) / np.linalg.norm(P[0] - P[1]) * ext
    P[-1] += (P[-1] - P[-2]) / np.linalg.norm(P[-1] - P[-2]) * ext
    return mf.CrossSection([np.vstack([P + nrm, (P - nrm)[::-1]])], mf.FillRule.EvenOdd)        # either winding


def frame_k(lines, z0, z1, t, width, E=SS.E_TPU):
    """Vertical stiffness N/mm of the struts: a 2D Euler-Bernoulli frame, floor nodes clamped, top nodes pushed down 1 mm without turning or
    sliding (the top plate), the reaction summed. Section width x t, so I = width t^3 / 12."""
    key = {}
    nodes, elems = [], []

    def node(pt):
        k = (round(pt[0], 6), round(pt[1], 6))
        if k not in key:
            key[k] = len(nodes)
            nodes.append(pt)
        return key[k]
    for P, closed in lines:
        ids = [node(p) for p in P]
        pairs = list(zip(ids, ids[1:])) + ([(ids[-1], ids[0])] if closed else [])
        elems += pairs
    X = np.array(nodes)
    nd = len(X)
    A, I = width * t, width * t ** 3 / 12
    K = np.zeros((3 * nd, 3 * nd))
    for i, j in elems:
        d = X[j] - X[i]
        L = float(np.hypot(*d))
        c, s = d / L
        k = np.array([[E * A / L, 0, 0, -E * A / L, 0, 0],
                      [0, 12 * E * I / L ** 3, 6 * E * I / L ** 2, 0, -12 * E * I / L ** 3, 6 * E * I / L ** 2],
                      [0, 6 * E * I / L ** 2, 4 * E * I / L, 0, -6 * E * I / L ** 2, 2 * E * I / L],
                      [-E * A / L, 0, 0, E * A / L, 0, 0],
                      [0, -12 * E * I / L ** 3, -6 * E * I / L ** 2, 0, 12 * E * I / L ** 3, -6 * E * I / L ** 2],
                      [0, 6 * E * I / L ** 2, 2 * E * I / L, 0, -6 * E * I / L ** 2, 4 * E * I / L]])
        T = np.zeros((6, 6))
        T[:3, :3] = T[3:, 3:] = [[c, s, 0], [-s, c, 0], [0, 0, 1]]
        kg = T.T @ k @ T
        idx = [3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2]
        K[np.ix_(idx, idx)] += kg
    bot = np.where(np.abs(X[:, 1] - z0) < 1e-6)[0]
    top = np.where(np.abs(X[:, 1] - z1) < 1e-6)[0]
    u = np.zeros(3 * nd)
    fixed = np.zeros(3 * nd, bool)
    for b in bot:
        fixed[3 * b:3 * b + 3] = True
    for tp in top:
        fixed[3 * tp:3 * tp + 3] = True
        u[3 * tp + 1] = -1.0                                 # 1 mm down; x and the turn held at 0
    f = ~fixed
    u[f] = np.linalg.solve(K[np.ix_(f, f)], -K[np.ix_(f, fixed)] @ u[fixed])
    R = K @ u
    return -sum(R[3 * tp + 1] for tp in top)


def pattern_fn(kind):
    def fn(x0, x1, z0, z1, screws, t):
        xa, xb = screws[0][0] + CLEAR, screws[1][0] - CLEAR
        struts = None
        for P, closed in centrelines(kind, xa, xb, z0, z1):
            r = ribbon(P, closed, t)
            struts = r if struts is None else struts + r
        layer = mf.CrossSection([np.array([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], float)])
        return layer - struts
    return fn


def size_wall(kind, xa, xb, z0, z1, width):
    lines = centrelines(kind, xa, xb, z0, z1)
    lo, hi = T_RANGE
    if frame_k(lines, z0, z1, lo, width) > TARGET or frame_k(lines, z0, z1, hi, width) < TARGET:
        t = lo if frame_k(lines, z0, z1, lo, width) > TARGET else hi
        return t, frame_k(lines, z0, z1, t, width), len(lines)
    for _ in range(30):
        mid = (lo + hi) / 2
        if frame_k(lines, z0, z1, mid, width) < TARGET:
            lo = mid
        else:
            hi = mid
    t = round((lo + hi) / 2, 2)
    return t, frame_k(lines, z0, z1, t, width), len(lines)


def main():
    tm = trimesh.load(os.path.join(SS.SRC, 'L_sole.stl'))
    lo, hi = tm.bounds
    z0, z1 = SS.TOP, hi[2] - SS.TREAD
    sec = tm.section(plane_origin=[0, 0, 1.0], plane_normal=[0, 0, 1])
    screws = sorted([np.asarray(sec.vertices[e.points]).mean(0)[:2] for e in sec.entities if np.ptp(np.asarray(sec.vertices[e.points])[:, 0]) < 10], key=lambda p: p[0])
    mid = tm.section(plane_origin=[0, 0, (z0 + z1) / 2], plane_normal=[0, 0, 1])
    width = (float(np.ptp(mid.vertices[:, 1])) - 2 * SS.SIDE_CUT) * 0.85
    xa, xb = screws[0][0] + CLEAR, screws[1][0] - CLEAR
    # the hex soft sole through the same frame model, for comparison with its hand estimate
    shown = []
    for kind in ('wave', 'bow', 'ring'):
        t, k, n = size_wall(kind, xa, xb, z0, z1, width)
        for side in ('L', 'R'):
            m, _ = SS.build(side, t, pattern=pattern_fn(kind))
            lay = m.copy()
            lay.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
            lay.apply_translation(-lay.bounds[0])
            path = os.path.join(SS.OUT, f'{side}_sole_{kind}_on_side.stl')
            lay.export(path)
            if side == 'L':
                shown.append((kind, m))
                w = 0.94 * 9.81
                print(f'{kind}: {n} struts, wall {t} mm, about {k:.1f} N/mm (frame model, E {SS.E_TPU:.0f}); one foot {w / k:.1f} mm, a step\'s peak ~{2 * w / k:.1f} mm; '
                      f'{m.volume * SS.DENSITY:.1f} g, watertight {m.is_watertight}, {len(m.split(only_watertight=False))} piece(s) -> {os.path.relpath(path, SS.ROOT)}')
    render(shown, os.path.join(SS.OUT, 'patterns.png'))


def render(meshes, path):
    import mujoco
    from PIL import Image
    tiles = []
    for name, m in meshes:
        v = m.copy()
        v.apply_transform(np.diag([1, -1, -1, 1]))
        v.apply_translation(-v.bounds[0])
        f = os.path.join(SS.OUT, '_p.stl')
        v.export(f)
        xml = (f'<mujoco><visual><global offwidth="900" offheight="420"/><headlight ambient="0.4 0.4 0.4"/></visual><asset><mesh name="s" file="{f}" scale="0.001 0.001 0.001"/></asset>'
               '<worldbody><light pos="0 -0.3 0.4" dir="0 0.6 -0.8"/><geom type="plane" size="0.3 0.3 0.01" rgba="0.2 0.22 0.25 1"/>'
               '<geom type="mesh" mesh="s" rgba="0.95 0.70 0.20 1"/></worldbody></mujoco>')
        mm = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(mm)
        mujoco.mj_forward(mm, d)
        r = mujoco.Renderer(mm, 420, 900)
        c = mujoco.MjvCamera()
        c.lookat[:] = [0.029, 0.021, 0.006]
        c.azimuth, c.elevation, c.distance = 90, -3, 0.075
        r.update_scene(d, c)
        im = Image.fromarray(r.render())
        from PIL import ImageDraw
        ImageDraw.Draw(im).text((14, 10), name, fill=(255, 255, 255))
        tiles.append(im)
        os.remove(f)
    sheet = Image.new('RGB', (900, 420 * len(tiles)))
    for i, im in enumerate(tiles):
        sheet.paste(im, (0, 420 * i))
    sheet.save(path)
    print('render', os.path.relpath(path, SS.ROOT))


if __name__ == '__main__':
    sys.exit(main())
