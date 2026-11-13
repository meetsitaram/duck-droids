"""Can each exported part really be printed, and how? tools/buildable.py asks about walls and load; this looks at the STL a slicer gets.

  python -I tools/printable.py             the checks; report in reports/printable.md, exit 1 on any FAIL
  python -I tools/printable.py --bad CASE  break a part on purpose and show the check FAIL (big void hole mate heads skin)

  ORIENT  the square orientation with the least overhang to support (faces past 45 degrees that aren't on the bed)
  PIECES  it exports as one piece, with no sealed void a slicer would fill or trap supports in
  BED     it fits a 220 mm bed that way, and enough of it touches the bed to stay down
  HOLES   every pilot and clearance hole is at least 1.5 mm across: smaller doesn't print round. No hole is sliced open by its edge
  SUPPORT the part as exported (its print file's orientation) needs at most 300 mm2 of real support: overhangs past 45 degrees, less its first 2 mm off the bed
          and flat ceilings up to 12 mm wide (bridges). A part printed already, with supports, is named in PRINTED_WITH_SUPPORT: a warning until it is redesigned
  MATE    two exported parts of a link never share space, nor a part and a bought part: what a printer makes has to go together. Horn seats excepted (drawn 0.5 mm into their plates)
  HEADS   no screw's head stands inside a servo or a board, once fitted
  SKIN    a cover has holes only for its own screws: nothing else drills through what shows
  NECK    no section under 12 mm2 is all that holds 150 mm3 or more to the rest of the part, holes and counterbores cut: it snaps there. Fit, not a load case

A part's overhangs are found from its faces, not by slicing. ORIENT's area counts bridges too; SUPPORT leaves them out.
(2026-11-11: SUPPORT was a warning, and it judged the orientation this file liked best, not the one export_prints wrote. The one-piece head frame passed with
5,900 mm2 of real support under a floor 14.5 mm off the bed, and the print failed after 2 hours of tree supports.)
"""
import argparse
import itertools
import os
import sys

import numpy as np
from scipy import ndimage
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BED = 220.0                                        # mm
MIN_CONTACT = 40.0                                 # mm2 on the bed, or it comes loose
MIN_HOLE = 0.0015                                  # m
OVERHANG = np.cos(np.radians(45))
SUPPORT_WARN = 250.0                               # mm2
NECK_AREA, NECK_CARRY = 12.0, 150.0                # mm2, mm3 (2026-11-13: the head yaw bracket's arm, 5.5 x 2.5 mm less a counterbore at its root, broke off printed)
SUPPORT_LIMIT = 300.0                              # mm2 of real support (bridges and the first 2 mm left out)
NEAR_BED, BRIDGE_W = 2.0, 12.0                     # mm
# printed with supports in the 2026-11-09 batch, before SUPPORT failed: redesign before they are printed again
PRINTED_WITH_SUPPORT = {'dynamixel': {'L thigh frame', 'R thigh frame', 'body shell'}}


def orientations():
    """The 6 ways of laying a part on a face of its bounding box (turns about the vertical don't matter)."""
    out = []
    for ax, sg in itertools.product(range(3), (1, -1)):
        d = np.zeros(3)
        d[ax] = sg
        T = trimesh.geometry.align_vectors(d, [0, 0, -1])     # this direction points down
        out.append((('x', 'y', 'z')[ax], sg, T))
    return out


def score(tm, T):
    m = tm.copy()
    m.apply_transform(T)
    z0 = m.bounds[0][2]
    n, a = m.face_normals, m.area_faces
    low = m.triangles[:, :, 2].max(axis=1) < z0 + 0.3
    over = (n[:, 2] < -OVERHANG) & ~low
    contact = a[(n[:, 2] < -0.99) & low].sum()
    return dict(overhang=float(a[over].sum()), contact=float(contact), height=float(m.extents[2]), extents=m.extents.copy(), T=T)


def real_support(tm):
    """mm2 a slicer would hold up, the mesh as it lies on the bed: (total, [(area, lowest corner, size), ...] the 3 biggest)."""
    n, z = tm.face_normals, tm.triangles[:, :, 2]
    idx = np.where((n[:, 2] < -OVERHANG) & (z.max(axis=1) > tm.bounds[0][2] + NEAR_BED))[0]
    if not len(idx):
        return 0.0, []
    s_ = np.zeros(len(tm.faces), bool)
    s_[idx] = True
    adj = tm.face_adjacency[s_[tm.face_adjacency].all(axis=1)]
    tot, big = 0.0, []
    for c in trimesh.graph.connected_components(adj, nodes=idx, min_len=1):
        c = np.asarray(c)
        A = tm.area_faces[c].sum()
        v = tm.vertices[tm.faces[c].reshape(-1)]
        ext = v.max(0) - v.min(0)
        flat = ext[2] <= 1.5 or tm.area_faces[c][n[c, 2] < -0.98].sum() > 0.6 * A
        if flat and min(ext[0], ext[1]) <= BRIDGE_W:   # a bridge between two walls: it prints without support
            continue
        tot += A
        big.append((float(A), v.min(0), ext))
    return float(tot), sorted(big, key=lambda b: -b[0])[:3]


def necks(tm, pitch=0.5, area_max=NECK_AREA, carry_min=NECK_CARRY, merge=1.5):
    """Sections under area_max mm2 that are the only thing holding carry_min mm3 to the rest: [(area, carried, axis, at mm)]."""
    g = tm.voxelized(pitch).fill().matrix
    g = np.pad(g, 1)
    out = []
    total = int(g.sum())
    for ax in range(3):
        st = np.ones((3, 3, 3), bool)
        idx = [slice(None)] * 3
        idx[ax] = [0, 2]
        st[tuple(idx)] = False                     # joined within a slice only
        k = int(round(merge / pitch))
        fat = ndimage.binary_dilation(g, np.broadcast_to(st, (3, 3, 3)), iterations=k)   # slivers either side of a hole count as one section
        lab, n = ndimage.label(fat, st)
        lab = np.where(g, lab, 0)
        w = np.bincount(lab.ravel(), minlength=n + 1).astype(np.int64)
        a = np.moveaxis(lab, ax, 0)
        lo_, hi_ = a[:-1].ravel(), a[1:].ravel()
        m = (lo_ > 0) & (hi_ > 0)
        e = np.unique(np.stack([lo_[m], hi_[m]], 1), axis=0)
        adj = [[] for _ in range(n + 1)]
        for u, v in e:
            adj[u].append(v); adj[v].append(u)
        pos = np.zeros(n + 1, int)
        first = ndimage.find_objects(lab)
        disc = np.zeros(n + 1, int); low = np.zeros(n + 1, int); sub = w.copy(); t = 0
        for root in range(1, n + 1):
            if disc[root] or not w[root]:
                continue
            t += 1; disc[root] = low[root] = t
            stack = [(root, 0, iter(adj[root]))]
            comp_nodes = [root]
            cuts = []                              # (node, child subtree weight)
            while stack:
                u, par, it = stack[-1]
                adv = False
                for v in it:
                    if not disc[v]:
                        t += 1; disc[v] = low[v] = t
                        stack.append((v, u, iter(adj[v]))); comp_nodes.append(v); adv = True
                        break
                    elif v != par:
                        low[u] = min(low[u], disc[v])
                if adv:
                    continue
                stack.pop()
                if par:
                    low[par] = min(low[par], low[u]); sub[par] += sub[u]
                    if low[u] >= disc[par]:
                        cuts.append((par, int(sub[u])))
            tot = int(sub[root])
            for v, cw in cuts:
                rest = tot - cw - int(w[v])
                A = w[v] * pitch ** 2
                carried = min(cw, rest) * pitch ** 3
                if A < area_max and carried > carry_min:
                    sl = first[v - 1]
                    out.append((float(A), float(carried), 'xyz'[ax], float(sl[ax].start * pitch)))
    best = {}
    for A, c, ax, at in out:                       # one row for each run of slices through the same neck
        key = (ax, round(c / 20))
        if key not in best or A < best[key][0]:
            best[key] = (A, c, ax, at)
    return sorted(best.values())


def best_orientation(tm):
    """The least real support (SUPPORT); a low print breaks a tie; a part that wouldn't stay down loses."""
    opts = []
    for _, _, T in orientations():
        o = score(tm, T)
        m = tm.copy()
        m.apply_transform(T)
        o['support'] = real_support(m)[0]
        opts.append(o)
    fine = [o for o in opts if o['contact'] >= MIN_CONTACT] or opts
    return min(fine, key=lambda o: (round(o['support'] / 50), o['height']))


def check(rep):
    import assembly as A
    import checks as C
    import export_prints as E
    import geom as G
    spec = G.load()
    S = C.Solids(spec)
    B = A.Build(spec, S)
    solids = {}
    for part, p in B.parts.items():
        if p['kind'] != 'P':
            continue
        m = E.with_holes(B, part)
        solids[part] = m
        check_part(B, part, m, E, rep)
    check_mate(B, solids, rep)


LIMIT_MATE = 0.003e-6                              # 3 mm3 in a part: rounding where two curved skins pass


def check_mate(B, solids, rep):
    import checks as C
    links = {n: {B.idx[g][0] for g in p['geoms']} for n, p in B.parts.items()}
    bad = 0
    names = list(solids)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not links[a] & links[b]:
                continue
            v = C.overlap(solids[a], solids[b])
            if v > LIMIT_MATE:
                bad += 1
                rep.add('MATE', f'{a} / {b}', False, f'{v * 1e9:.0f} mm3 in the same place')
        for name, p in B.parts.items():
            if p['kind'] != 'B' or not links[a] & links[name] or name.endswith((' horn', 'bearing', 'bearing inner')):
                continue
            for g in p['geoms']:
                ln, k, gg = B.idx[g]
                if gg['role'] == 'cut' or g.endswith(('flange', 'rear boss', 'rear horn')) or 'race' in g:
                    continue
                v = C.overlap(solids[a], B.S.geom[(ln, k)])
                if v > LIMIT_MATE:
                    bad += 1
                    rep.add('MATE', f'{a} / {g}', False, f'{v * 1e9:.0f} mm3 in the same place')
    rep.add('MATE', 'parts that share a link', True, f'{len(names)} parts: {bad} clashes')
    import export_prints as E
    hard = [(n, ln, S_) for n, (ln, i, g) in B.idx.items() if (S_ := B.S.geom.get((ln, i))) is not None and (g['role'] == 'actuator' or n in ('battery 2S 850 mAh', 'servo bus board', 'Waveshare bus board', 'U2D2', 'IMU', 'camera') or n.endswith('5 V regulator'))]
    for n, (ln, g) in B.screws.items():
        f = g['fast']
        sz = f['size'].split()[0]
        tool = E.cylinder(np.array(f['p']), np.array(f['d']), E.HEAD_R[sz], *((0.00005, 0.0012) if f['size'].endswith('flat') else (-0.0015, -0.00005)))   # (a flat head's p is its top: the head is below it, in its seat)
        hit = [h for h, l2, m in hard if l2 == ln and C.overlap(tool, m) > 1e-10]
        rep.add('HEADS', n, not hit, f'its head stands inside {hit}' if hit else '')


def check_part(B, part, m, E, rep):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties[:, :3], float) * 1000, np.asarray(mesh.tri_verts, int))
    import json
    import geom as G
    try:                                           # as export_prints laid it: what the printer gets
        T = np.asarray(json.load(open(G.parts_path('parts'), encoding='utf-8'))['parts'][part]['print_T'], float)
        b = score(tm, T)
    except (OSError, KeyError):
        b = best_orientation(tm)
        T = b['T']
    rep.add('ORIENT', part, True, f"{b['overhang']:.0f} mm2 overhang, {b['contact']:.0f} mm2 on the bed, {b['height']:.0f} mm tall")
    ps = m.decompose()
    n_, voids = len([q for q in ps if q.volume() > 1e-9]), [q for q in ps if q.volume() < -1e-10]
    rep.add('PIECES', part, n_ == 1 and not voids, f'{n_} pieces, {len(voids)} sealed voids' if n_ != 1 or voids else '')
    e = b['extents']
    rep.add('BED', part, e.max() <= BED and b['contact'] >= MIN_CONTACT, f'{e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} mm, {b["contact"]:.0f} mm2 on the bed')
    if any(B.idx[n][2]['role'] == 'shell' for n in B.parts[part]['geoms']):
        names = sorted({c[5] for c in E.hole_list(B, part)})
        own = [n for n in names if not any(k in n for k in ('cradle', 'fork', 'boss', 'crank', 'Pi '))]
        rep.add('SKIN', part, len(own) == len(names) and len(names) <= 6, f'{len(names)} screws drill it: {names[:6]}')
    bad = [f"{c[5]} {2 * c[2] * 1000:.1f} mm" for c in E.hole_list(B, part) if 2 * c[2] < MIN_HOLE]
    rep.add('HOLES', part, not bad, ', '.join(bad[:3]))
    nk = necks(tm)
    rep.add('NECK', part, not nk, '; '.join(f"{a_:.0f} mm2 holds {c_:.0f} mm3, across {ax_}" for a_, c_, ax_, _ in nk[:3]))
    lying = tm.copy()
    lying.apply_transform(T)
    sup, big = real_support(lying)
    where = '; '.join(f"{a:.0f} mm2 {e[0]:.0f} x {e[1]:.0f} mm, {lo[2] - lying.bounds[0][2]:.0f} mm up" for a, lo, e in big)
    if sup > SUPPORT_LIMIT and part in PRINTED_WITH_SUPPORT.get(G.RECIPE, ()):
        rep.add('SUPPORT', part, False, f"{sup:.0f} mm2 of real support ({where}): printed already, redesign before printing it again", warn=True)
    else:
        rep.add('SUPPORT', part, sup <= SUPPORT_LIMIT, f"{sup:.0f} mm2 of real support" + (f": {where}" if sup > SUPPORT_LIMIT else ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bad')
    a = ap.parse_args()
    import checks as C
    import geom as G
    rep = C.Report()
    if a.bad:
        import assembly as A
        import export_prints as E
        spec = G.load()
        B = A.Build(spec, C.Solids(spec))
        m = E.with_holes(B, 'L shin')
        if a.bad == 'void':                        # a sealed cavity inside the shin's cap
            ln, i, g = B.idx['L shin rib']
            c = np.array(g['c'])
            m = m - C.to_manifold(trimesh.creation.box(extents=(0.003, 0.002, 0.003), transform=trimesh.transformations.translation_matrix(c)))
        if a.bad == 'hole':                        # a pilot hole too small to print
            real = E.hole_list
            E.hole_list = lambda B_, p_: [h[:2] + (0.0005,) + h[3:] for h in real(B_, p_)] or [(np.zeros(3), np.array([0, 0, 1.0]), 0.0005, 0, 0.001, 'test')]
        if a.bad == 'big':                         # too big for the bed
            m = m.scale([4.0, 4.0, 4.0])
        if a.bad == 'skin':                        # a shell taken as solid again
            G_in = G.inner_of
            G.inner_of = lambda g, t: dict(g, sections=[dict(s_, a=1e-4, b=1e-4) for s_ in g.get('sections', [])]) if g['kind'] == 'loft' else G_in(g, t)
            check_part(B, 'body shell', E.with_holes(B, 'body shell'), E, rep)
        if a.bad == 'heads':                       # the head yaw horn screws as they were, under the roll servo
            for g in spec['links']['head_yaw_link']['geoms']:
                if g['name'].startswith('head yaw fork screw') and 'fast' in g:
                    g['fast']['p'][2] += 0.0016
            check_mate(B, {'L shin': m}, rep)
        if a.bad == 'mate':                        # the sole as drawn, 1 mm into its shoe, its recess not cut
            E.pockets = lambda *a_: []
            check_mate(B, {p: E.with_holes(B, p) for p in ('L shoe', 'L sole')}, rep)
        check_part(B, 'L shin', m, E, rep)
        fails = rep.failing()
        print(f"--bad {a.bad}: {'CAUGHT' if fails else 'NOT CAUGHT'} ({len(fails)} failing)")
        for r in fails[:3]:
            print('  ', r['group'], r['item'], r['detail'])
        return 0 if fails else 1
    check(rep)
    rep.write(G.out_path('reports', 'printable.md'), 'From tools/printable.py. Overhang from faces, not a slicer: none of this has been printed.')
    for r in rep.rows:
        if r['status'] != 'PASS':
            print(r['status'], r['group'], r['item'], r['detail'])
    print(f"{len(rep.rows)} printable checks, {len(rep.failing())} failing")
    return 1 if rep.failing() else 0


if __name__ == '__main__':
    sys.exit(main())
