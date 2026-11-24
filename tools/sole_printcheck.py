"""python -I tools/sole_printcheck.py FILE_on_side.stl ...: slicer-like print check of an STL already in print orientation: downward faces flatter than the slicer's overhang line (a layer sticking out
more than 1/4 of a line past the one below: atan(layer / (line/4)) from horizontal, ~63 deg at 0.2/0.4), and floating islands per layer."""
import sys, math, collections
import numpy as np, trimesh
from shapely.ops import unary_union
LAYER, LINE = 0.2, 0.4
lim = math.degrees(math.atan(LAYER / (LINE / 4)))          # min angle from horizontal for a down-facing face
def check(path):
    m = trimesh.load(path)
    n, c, a = m.face_normals, m.triangles_center, m.area_faces
    down = n[:, 2] < -1e-6
    alpha = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))     # a face's angle from horizontal: 0 a flat ceiling, 90 a vertical wall
    over = down & (c[:, 2] > 0.25) & (alpha < lim - 1)               # flatter than the slicer's line
    print(f'{path.split("/")[-1]}: overhang faces flatter than {lim:.0f} deg: {a[over].sum():.1f} mm2', end='')
    if over.any():
        d = collections.defaultdict(float)
        for p, w in zip(c[over], a[over]): d[tuple((p // 3 * 3).astype(int))] += w
        print('  at', [(k, round(v, 1)) for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:4]], end='')
    prev, isl = None, []
    for z in np.arange(LAYER / 2, m.bounds[1][2], LAYER):
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if s is None: prev = None; continue
        p, _ = s.to_2D(to_2D=np.eye(4))
        regs = [q for q in p.polygons_full if q.area > 1e-4]
        if prev is not None:
            isl += [(round(z, 2), round(q.area, 3)) for q in regs if q.intersection(prev).area < 1e-4]
        prev = unary_union(regs) if regs else None
    print(f'; islands: {len(isl)}', isl[:3])


for f in sys.argv[1:]:
    check(f)
