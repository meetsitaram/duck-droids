"""One STL per printed part, with its screw holes, for slicing: prints/<part>.stl and prints/README.md.

  python -I tools/export_prints.py                every printed part (the left leg's; the right is mirrored in the slicer)
  python -I tools/export_prints.py --test knee    only the one-joint test print

Every screw in the spec cuts its holes: clearance through the part it clamps, a counterbore for its head where it is sunk,
and a pilot in any printed part it threads into (M2 1.6 mm, M3 2.5 mm). Check one print before trusting the fits: printers
differ, so bores may need 0.1-0.2 mm of adjustment. Sizes are as designed, in millimetres.
"""
import argparse
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assembly as A  # noqa: E402
import checks as C  # noqa: E402
import geom as G  # noqa: E402

CLEAR = {'M2': 0.00115, 'M3': 0.0017}
PILOT = {'M2': 0.0008, 'M3': 0.00125}
TEST = {'knee': ['L thigh frame', 'L knee lid', 'L shin']}


def cylinder(p, d, r, a, b):
    """A cylinder from a to b along d from p."""
    T = np.eye(4)
    T[:3, :3] = G._frame_to(np.asarray(d, float))
    T[:3, 3] = np.asarray(p) + np.asarray(d) * (a + b) / 2
    m = trimesh.creation.cylinder(radius=r, height=b - a, sections=32)
    m.apply_transform(T)
    return C.to_manifold(m)


def solid_part(B, part):
    # (a cover prints hollow: its wall)
    def body(n):
        ln, i, g = B.idx[n]
        thin = g['kind'] == 'plate' and g['t'] < 0.0045   # thinner than two walls: solid
        return B.S.geom[(ln, i)] if thin else B.S.wall.get((ln, i), B.S.geom[(ln, i)])
    return C.union([body(n) for n in B.parts[part]['geoms']])


def with_holes(B, part):
    m = solid_part(B, part)
    names = set(B.parts[part]['geoms'])
    for n, (ln, g) in B.screws.items():
        f = g['fast']
        p, d = np.array(f['p']), np.array(f['d'])
        sz = f['size'].split()[0]
        under = [q for q in names if B.idx[q][0] == ln and B.inside(B.idx[q][2], (p + d * 0.0002)[None]).any()]
        ts = np.linspace(0, f['L'], 25)
        on_axis = [q for q in names if B.idx[q][0] == ln and B.inside(B.idx[q][2], p + np.outer(ts, d)).any()]
        if not on_axis:
            continue
        if under:                                  # it clamps this part: a clearance hole, its head's counterbore above
            m = m - cylinder(p, d, CLEAR[sz], -0.0005, f['L'])
            hd = 0.0029 if sz == 'M3' else 0.0021
            m = m - cylinder(p, d, hd, -0.03, 0.0)
        else:
            m = m - cylinder(p, d, PILOT[sz], -0.0005, f['L'] + 0.0005)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test')
    a = ap.parse_args()
    spec = G.load()
    S = C.Solids(spec)
    B = A.Build(spec, S)
    out = os.path.join(G.ROOT, 'prints')
    os.makedirs(out, exist_ok=True)
    want = TEST[a.test] if a.test else [n for n, p in B.parts.items() if p['kind'] == 'P' and not n.startswith('R ')]
    rows = []
    for part in want:
        m = with_holes(B, part)
        mesh = m.to_mesh()
        tm = trimesh.Trimesh(np.asarray(mesh.vert_properties[:, :3], float) * 1000, np.asarray(mesh.tri_verts, int))
        tm.apply_translation(-tm.bounds[0])
        name = part.replace(' ', '_') + '.stl'
        tm.export(os.path.join(out, name))
        e = tm.extents
        n_ = len([p for p in m.decompose() if p.volume() > 1e-9])   # (a negative one is a closed void)
        rows.append((part, name, e, abs(m.volume()) * 1e6, n_))
        print(f'{name:32s} {e[0]:5.0f} x {e[1]:5.0f} x {e[2]:5.0f} mm  {abs(m.volume()) * 1e6:6.1f} cm3  {n_} piece(s)')
    if not a.test:
        L = ['# Printed parts', '', 'From `python -I tools/export_prints.py`, in millimetres, the left side; mirror them for the right. Not yet test printed.', '',
             '| Part | File | Size (mm) | Solid volume (cm3) |', '|---|---|---|---|']
        for part, name, e, v, n_ in rows:
            L.append(f'| {part} | {name} | {e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} | {v:.1f} |')
        L += ['', '## Print one joint first', '', 'Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin` (about 32 cm3 solid), with 1 STS3215-C044, 1 6704ZZ,',
              '6 M2 x 6, 2 M2 x 8 and 4 M3 x 10. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;',
              'how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.']
        open(os.path.join(out, 'README.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
