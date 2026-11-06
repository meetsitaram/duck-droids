"""Does a duck look like its family? Its head's silhouette, front and side, against a sibling's at the same head size: python -I tools/family_compare.py [--sibling dynamixel] [--spec FILE] [--png OUT]

(2026-11-06: the nano duck, built overnight from its own spec, passed every check with a dome for a hood, a box for a bill and an eye on the
dome's curve, when the family's measured head was already in spec/robot_dynamixel.json. The user: "get the nano head looking like others".
No check looked at the look against the family. This one does.)

The head is everything on the head and beak links but servos, electronics, wires and screws, at the zero pose. Each view is projected
(front: y-z, side: x-z), scaled to its own head width (front) or length (side) and anchored at the head's top and front, then rasterised on a
200-pixel grid. The overlap (intersection over union) with the sibling's must be at least MIN_IOU in both views. A side-by-side picture of
both heads, and of both ducks whole, goes to reports/<recipe>/family_compare.png, for the eye: numbers can pass on an ugly head (rule 4).

--spec checks another spec file (a broken design, to prove the check: the nano duck's head before 2026-11-06 must fail).
Exits 1 when a view is under MIN_IOU.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geom as G  # noqa: E402

MIN_IOU = 0.75
N = 200
HEAD_LINKS = ('head', 'beak_link')
SKIP_ROLES = ('cut', 'actuator')


def head_triangles(spec):
    """World triangles of the head's visible parts at the zero pose."""
    R = G.Robot(spec)
    M = R.fk({})
    tris = []
    for ln in HEAD_LINKS:
        if ln not in spec['links']:
            continue
        for g in spec['links'][ln]['geoms']:
            if g['role'] in SKIP_ROLES or g.get('material') == 'electronics' or g.get('wire') or 'fast' in g:
                continue
            try:
                m = G.mesh_of(g)
            except Exception:
                continue
            v = G.apply(M[ln], np.asarray(m.vertices)) if ln in M else np.asarray(m.vertices)
            tris.append(v[np.asarray(m.faces)])
    return np.concatenate(tris) if tris else np.zeros((0, 3, 3))


def silhouette(tris, axes, span_axis):
    """A binary N x N image of the triangles projected on `axes` (u, v), scaled by the extent along span_axis, anchored at max v and max u."""
    P = tris[:, :, axes]
    span = tris[:, :, span_axis].max() - tris[:, :, span_axis].min()
    u0, v1 = P[:, :, 0].max(), P[:, :, 1].max()
    Q = np.stack([(u0 - P[:, :, 0]) / span, (v1 - P[:, :, 1]) / span], -1)        # 0 at the front/top, 1 a head's span away
    im = Image.new('1', (N, N), 0)
    d = ImageDraw.Draw(im)
    for t in Q:
        d.polygon([(float(a) * N * 0.8 + N * 0.1, float(b) * N * 0.8 + N * 0.1) for a, b in t], fill=1)
    return np.asarray(im, bool)


def iou(a, b):
    return float((a & b).sum()) / max(1, float((a | b).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sibling', default='dynamixel')
    ap.add_argument('--spec')
    ap.add_argument('--png')
    a = ap.parse_args()
    recipe = os.environ.get('MILLI_RECIPE', 'hybrid')
    spec = json.load(open(a.spec, encoding='utf-8')) if a.spec else G.load()
    sib = json.load(open(os.path.join(G.ROOT, 'spec', f'robot_{a.sibling}.json'), encoding='utf-8'))
    A, B = head_triangles(spec), head_triangles(sib)
    views = {'front (y-z, to the head\'s width)': ((1, 2), 1), 'side (x-z, to the head\'s length)': ((0, 2), 0)}
    bad, row = 0, []
    for name, (axes, span) in views.items():
        sa, sb = silhouette(A, axes, span), silhouette(B, axes, span)
        k = iou(sa, sb)
        ok = k >= MIN_IOU
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} family head {name}: overlap {k:.2f} with the {a.sibling} duck's (at least {MIN_IOU})")
        pic = np.full((N, N, 3), 255, np.uint8)
        pic[sb] = (190, 190, 190)
        pic[sa & ~sb] = (232, 100, 42)
        pic[sa & sb] = (60, 60, 60)
        row.append(pic)
    out = a.png or G.out_path('reports', 'family_compare.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(np.hstack(row)).resize((4 * N, 2 * N), Image.NEAREST).save(out)
    print(f'{out}: dark both, grey only the {a.sibling} duck, orange only this one')
    print(f'{len(views)} family checks, {bad} failing')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
