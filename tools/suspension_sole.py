"""A sprung sole for the all-Dynamixel duck: the TPU sole with a hexagon lattice through its width (the user's sketch and fin-ray and
hex-gripper references, 2026-11-23), so it gives a little under each step. Solid TPU at this size barely gives: a 0.94 kg duck squeezes a 12 mm solid 95A sole
by about a micron. Thin ribs in bending give about 0.5-1 mm.

From the exported sole (prints/dynamixel/{L,R}_sole.stl, its print frame: mounting face at z=0, floor at the top):
  - top plate, the mounting face and its two M3 clearance holes, kept solid
  - a lattice layer of flat-topped hexagon cells running across the sole (open on both sides), 2 staggered rows, walls of thickness T,
    the whole length: toe and heel take the hardest landings, so they're sprung too (the user: rigid ends wouldn't help)
  - the tread, the floor, kept, with shallow U-grooves across it between the lattice's nodes so it flexes too
  - the two M3s: each head seats on a boss hanging from the top plate (the same clamp length as before, so the same M3 x 12), reached
    through a bore up through the tread and the lattice; nothing joins the boss to the tread, so no rigid post
Stiffness is a beam estimate (each rib a fixed-guided beam, rows in series, ribs in a row in parallel), not FEA: say so when quoting it.

  python -I tools/suspension_sole.py            writes prints/dynamixel/suspension/{L,R}_sole_{soft,medium}.stl and a render
Print it ON ITS SIDE (a long side on the bed, brim on): the lattice is then in the layers' plane, every rib a wall, no bridges or supports.
"""
import math
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'prints', 'dynamixel')
OUT = os.path.join(SRC, 'suspension')

TOP = 2.0            # mm, the mounting plate (z from 0)
TREAD = 1.6          # mm, the floor plate under the lattice (at the sole's middle)
HEX_ROWS = 1         # one row of big cells: a wall's stiffness goes as (t/L)^3, so longer walls flex far more (the user: too many small hexagons)
HEX_FLAT = 3.0       # mm, a hexagon's flat top and bottom walls (flat-topped cells: the slanted walls bend, as a fin-ray's ribs)
HEX_ANGLE = 28.0     # deg, the slanted walls from horizontal: flatter is softer
FILLET = 0.4         # mm, the cells' corners rounded
BOSS_R, BOSS_Z = 4.0, 5.0     # mm: each screw's boss (a tall rhombus holding this circle, faces at STEEP) round its hole, from the top plate down to the old head seat (z 5)
SIDE_CUT = 1.0       # mm off each long side, flat: it prints on a side (the user), 8.9 x 41.5 mm on the bed, the foot 2 mm narrower
TIP = 1.0            # mm at the very heel and toe tips kept free of cells: walls grazing the curl there left specks the slicer calls floating
STEEP = 65.0         # deg from horizontal, at least, for every face that looks down in print. The slicer flags a perimeter once a layer sticks out
                     # more than ~1/4 line past the one below: at 0.2 mm layers and 0.4 mm lines that is anything flatter than ~63 deg (the user saw
                     # the 45 deg faces flagged, 2026-11-23)
END_CUT = False      # the 65 deg cut beyond each screw: off. At 65 deg it ran into the screw's boss and plate (a quarter of the head's seat gone,
                     # the user's print, 2026-11-23); seat_check() below now fails any sole like that
CORNER_MARGIN = 1.2  # mm between the teardrop's tip and the 45 deg end cut above it
CORNER_X = 1.0       # mm past the screw's centre that end cut reaches toward the middle
BORE_R = 3.1         # mm: the head and driver's way in (a tall rhombus holding this circle, faces at STEEP), through the tread and the lattice
GROOVE_W, GROOVE_D = 1.4, 0.7  # mm, the tread's U-grooves
E_TPU = 150.0        # N/mm^2: Bambu TPU for AMS (about 68D), the filament the duck's soles are printed in. An estimate (100-250), not a datasheet figure.
                     # TPU 95A is about 26: in 95A every variant here is about 6x softer
VARIANTS = {'soft': 0.60, 'medium': 0.70, 'firm': 0.80}     # wall thickness, mm: two 0.4-nozzle lines and up, long walls (the user: fewer hexagons, longer sides)
DENSITY = 1.21e-3    # g/mm^3


def to_manifold(tm):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))


def to_trimesh(m):
    me = m.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return mf.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def hex_geometry(height):
    """HEX_ROWS rows of flat-topped hexagons in the layer's height, columns staggered by half a cell: (cell height, slanted run, column pitch, wall length)."""
    ch = height / HEX_ROWS
    run = (ch / 2) / math.tan(math.radians(HEX_ANGLE))
    return ch, run, HEX_FLAT + run, (ch / 2) / math.sin(math.radians(HEX_ANGLE))


def holes_xz(x0, x1, z0, z1, t):
    """The lattice's cells as a cross-section in (x, z): flat-topped hexagons tiling the layer, shrunk so walls are t thick, corners rounded."""
    ch, run, pitch, _ = hex_geometry(z1 - z0)
    hx = HEX_FLAT / 2
    span = x1 - x0
    n = int(span // pitch)
    xs0 = x0 + (span - n * pitch) / 2
    polys = []
    for k in range(-2, n + 3):
        x = xs0 + k * pitch
        for m in range(-1, 4):
            z = z0 + m * ch + (ch / 2 if k % 2 else 0.0)
            polys.append([(x + hx + run, z), (x + hx, z + ch / 2), (x - hx, z + ch / 2), (x - hx - run, z), (x - hx, z - ch / 2), (x + hx, z - ch / 2)])
    out = None
    for p in polys:                       # each cell shrunk on its own (they tile exactly, so a union would leave no walls)
        c = mf.CrossSection([np.array(p, float)]).offset(-t / 2, mf.JoinType.Miter).offset(-FILLET, mf.JoinType.Round).offset(FILLET, mf.JoinType.Round)
        out = c if out is None else out + c
    return out, xs0, n, 2 * HEX_ROWS


def stiffness(t, span, height, width):
    """Vertical N/mm of the lattice layer: each slanted wall a fixed-guided beam, one per column pitch in each of the 4 half-rows, the half-rows in series.
    The flat walls let the nodes turn a little, so the real thing is somewhat softer."""
    ch, run, pitch, L = hex_geometry(height)
    th = math.radians(HEX_ANGLE)
    I = width * t ** 3 / 12
    kb = 12 * E_TPU * I / L ** 3
    ka = E_TPU * width * t / L
    kv = 1 / (math.cos(th) ** 2 / kb + math.sin(th) ** 2 / ka)
    return kv * (span / pitch) / (2 * HEX_ROWS), HEX_ANGLE


def build(side, t, pattern=None):
    """pattern: a function (x0, x1, z0, z1, screws, t) -> the voids' CrossSection in (x, z), in place of the hexagons (tools/sole_patterns.py)."""
    tm = trimesh.load(os.path.join(SRC, f'{side}_sole.stl'))
    lo, hi = tm.bounds
    S = to_manifold(tm) ^ box([lo[0] - 1, lo[1] + SIDE_CUT, lo[2] - 1], [hi[0] + 1, hi[1] - SIDE_CUT, hi[2] + 1])
    # the side it prints on (y low): above the flat face nothing may flare out faster than 45 deg, or the toe and heel corners overhang
    # in the first layers. Clip to the hull of the flat face and that face grown outward at STEEP.
    y0 = lo[1] + SIDE_CUT
    face = tm.section(plane_origin=[0, y0 + 0.01, 0], plane_normal=[0, 1, 0])
    fp = np.asarray(face.vertices)[:, [0, 2]]
    G = 60.0                                                  # past the far side (the sole is 42 mm wide)
    gr = G / math.tan(math.radians(STEEP))                    # how far out it may grow over that height
    pts = [(x, y0 - 0.01, z) for x, z in fp] + [(x + gr * math.cos(a), y0 + G, z + gr * math.sin(a)) for x, z in fp[::max(1, len(fp) // 64)] for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    S = S ^ mf.Manifold.hull_points(np.array(pts, float))
    zmax = hi[2]
    sec = tm.section(plane_origin=[0, 0, 1.0], plane_normal=[0, 0, 1])
    screws = sorted([np.asarray(sec.vertices[e.points]).mean(0)[:2] for e in sec.entities if np.ptp(np.asarray(sec.vertices[e.points])[:, 0]) < 10], key=lambda p: p[0])
    assert len(screws) == 2, screws
    x0, x1 = lo[0] - 1.0, hi[0] + 1.0                         # the whole length
    z0, z1 = TOP, zmax - TREAD
    if pattern is None:
        cs, xs0, n, rows = holes_xz(x0, x1, z0, z1, t)
    else:
        cs, xs0, n, rows = pattern(x0, x1, z0, z1, screws, t), 0.0, -9, 0      # no hex columns: no tread grooves either
    # extrude the (x, z) section along y: CrossSection is in (x, y), extruded along z; rotate so its y is our z and its extrusion is our y
    W = hi[1] - lo[1] + 2
    cells = mf.Manifold.extrude(cs, W).rotate([90, 0, 0]).translate([0, hi[1] + 1, 0])
    tip = TIP if pattern is None else -1.0                    # strut patterns: nothing kept at the tips (1 mm end-wall fins hung there, the user's screenshot)
    cells = cells ^ box([lo[0] + tip, lo[1] - 2, z0], [hi[0] - tip, hi[1] + 2, z1])     # within the lattice layer
    out = S - cells
    # Printed on its side (+y up), anything round about z would overhang at its top. So the boss and the head's bore are tall rhombi in (x, y)
    # (every face 45 deg to the print's vertical) and the clearance hole a teardrop pointing up (the user, 2026-11-23).
    def prism_z(pts, z0_, z1_):
        return mf.Manifold.extrude(mf.CrossSection([np.array(pts, float)]), z1_ - z0_).translate([0, 0, z0_])

    def rhombus(cx, cy, r):
        """A rhombus holding the circle r, its faces STEEP from horizontal (tall in print, +y up)."""
        a = math.radians(STEEP)
        hx, hy = r / math.sin(a), r / math.cos(a)
        return [(cx + hx, cy), (cx, cy + hy), (cx - hx, cy), (cx, cy - hy)]

    def teardrop(cx, cy, r, n=32):
        """A circle with a pointed top whose flanks are STEEP from horizontal."""
        a = math.radians(STEEP)
        t0, t1 = math.pi / 2 + a, (math.pi / 2 - a) + 2 * math.pi        # flanks leave the circle where its own slope reaches STEEP
        pts = [(cx + r * math.cos(u), cy + r * math.sin(u)) for u in np.linspace(t0, t1, n)]
        return pts + [(cx, cy + r / math.cos(a))]

    for sx, sy in screws:                                     # a boss under the top plate for each head, the bore below it, the clearance through it
        out = out + (prism_z(rhombus(sx, sy, BOSS_R), TOP - 0.1, BOSS_Z) ^ S)
        out = out - prism_z(rhombus(sx, sy, BORE_R), BOSS_Z, zmax + 2)
        out = out - prism_z(teardrop(sx, sy, 1.8), -0.5, BOSS_Z + 0.5)     # 1.8, not 1.7: it swallows the old round hole whole (no slivers)
    # the end beyond each screw, above the teardrop's tip (in print), cut off at STEEP (the user, 2026-11-23): where the bore meets the curled
    # floor there it left specks the slicer called floating. Only out to CORNER_X past the screw's centre: the heel and toe are curled off the
    # floor there, so no contact is lost. The 45 deg face looks up and the inner face is vertical, so neither needs support.
    top = hi[1] + 5
    for k, (sx, sy) in enumerate(screws if END_CUT else []):
        ya = sy + 1.8 / math.cos(math.radians(STEEP)) + CORNER_MARGIN
        m_ = math.tan(math.radians(STEEP))
        if k == 0:                                            # heel end (x low): above-left of a line rising to the right
            quad = [(lo[0] - 5, ya - (sx - lo[0] + 5) * m_), (sx + CORNER_X, ya + CORNER_X * m_), (sx + CORNER_X, top), (lo[0] - 5, top)]
        else:                                                 # toe end (x high): above-right of a line rising to the left
            quad = [(hi[0] + 5, ya - (hi[0] + 5 - sx) * m_), (hi[0] + 5, top), (sx - CORNER_X, top), (sx - CORNER_X, ya + CORNER_X * m_)]
        out = out - prism_z(quad, lo[2] - 1, hi[2] + 1)
    # the tread's U-grooves across the floor, between the nodes where the ribs meet it (over the cells of the last row)
    ch, run, pitch, _ = hex_geometry(z1 - z0)
    grooves = None
    for i in range(-1, n + 2):
        x = xs0 + i * pitch                                    # the columns whose cells are cut in half by the tread
        if x0 + 1 < x < x1 - 1:
            g = mf.Manifold.cylinder(W, GROOVE_W / 2, GROOVE_W / 2, 24).rotate([90, 0, 0]).translate([x, hi[1] + 1, zmax])
            g = g + box([x - GROOVE_W / 2, lo[1] - 2, zmax], [x + GROOVE_W / 2, hi[1] + 2, zmax + 2])
            g = g.translate([0, 0, -GROOVE_D + GROOVE_W / 2]) if GROOVE_D > GROOVE_W / 2 else g.translate([0, 0, -(GROOVE_D - GROOVE_W / 2)])
            grooves = g if grooves is None else grooves + g
    if grooves is not None:
        out = out - grooves
    # the lattice width at mid height, for the estimate
    mid = tm.section(plane_origin=[0, 0, (z0 + z1) / 2], plane_normal=[0, 0, 1])
    width = float(np.ptp(mid.vertices[:, 1])) * 0.85            # the plan's rounded ends: about 85 % of the full width on average
    span = float(np.ptp(mid.vertices[:, 0])) - 2 * 2 * BORE_R    # the length at mid height, less the walls the two bores cut
    k, th = stiffness(t, span, z1 - z0, width)
    res = to_trimesh(out)
    res = max(res.split(only_watertight=False), key=lambda q: q.volume)      # drop slivers (0.05 mm3 bits where cells graze the curled ends)
    seat_check(res, screws)
    return res, dict(k=k, rib_angle=th, span=span, height=z1 - z0, rows=rows, cells=n, screws=[p.round(2).tolist() for p in screws])


def seat_check(m, screws, need=0.90):
    """Each screw: the ring its head and clamp bear on (1.8 to 4 mm round the hole) must be solid from the mounting face to the boss's
    underside. The teardrop's point (it prints on its side) takes about 8 %, by design. Prints the worst fraction; returns False if any is under
    `need`. (The printing checks alone missed a cut through the seat, 2026-11-23.)"""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    worst = 1.0
    for sx, sy in screws:
        ring = Point(sx, sy).buffer(4.0).difference(Point(sx, sy).buffer(1.8))
        for z in np.linspace(0.3, BOSS_Z - 0.2, 6):
            sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if sec is None:
                return False
            p, _ = sec.to_2D(to_2D=np.eye(4))
            worst = min(worst, unary_union(p.polygons_full).intersection(ring).area / ring.area)
    print(f'   screw seats: worst {worst * 100:.0f} % solid (need {need * 100:.0f})' + ('' if worst >= need else '  FAIL'))
    return worst >= need


def render(meshes, path):
    import mujoco
    from PIL import Image
    xml = ['<mujoco><visual><global offwidth="1600" offheight="900"/><headlight ambient="0.35 0.35 0.35"/></visual><asset>']
    for k, (name, m) in enumerate(meshes):
        f = os.path.join(OUT, f'_r{k}.stl')
        m = m.copy()
        m.apply_transform(np.diag([1, -1, -1, 1]))            # as worn: the floor down, the mounting face up
        m.apply_translation([0, m.bounds[1][1] - m.bounds[0][1], -m.bounds[0][2]])
        m.export(f)
        xml.append(f'<mesh name="m{k}" file="{f}" scale="0.001 0.001 0.001"/>')
    xml.append('</asset><worldbody><light pos="0 -0.3 0.4" dir="0 0.6 -0.8"/><light pos="0.2 0.3 0.3" dir="-0.4 -0.6 -0.6"/>')
    for k, _ in enumerate(meshes):
        xml.append(f'<geom type="mesh" mesh="m{k}" pos="{k * 0.075} 0 0" rgba="0.95 0.70 0.20 1"/>')
    xml.append('<geom type="plane" size="0.3 0.3 0.01" rgba="0.25 0.27 0.30 1"/>')
    xml.append('</worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_string(''.join(xml))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 450, 800)
    tiles = []
    for az, el, k in ((90, -5, 0), (120, -30, 0), (90, -5, 1), (60, -30, 1)):
        cam = mujoco.MjvCamera()
        cam.lookat[:] = [0.075 * k + 0.029, 0.022, 0.006]
        cam.azimuth, cam.elevation, cam.distance = az, el, 0.095
        r.update_scene(d, cam)
        tiles.append(Image.fromarray(r.render()))
    sheet = Image.new('RGB', (1600, 900))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * 800, (i // 2) * 450))
    sheet.save(path)
    for k in range(len(meshes)):
        os.remove(os.path.join(OUT, f'_r{k}.stl'))


def main():
    os.makedirs(OUT, exist_ok=True)
    shown = []
    for name, t in VARIANTS.items():
        for side in ('L', 'R'):
            m, info = build(side, t)
            path = os.path.join(OUT, f'{side}_sole_{name}.stl')
            m.export(path)
            lay = m.copy()                                     # the same, lying on its flat long side, ready for the slicer
            lay.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
            lay.apply_translation(-lay.bounds[0])
            lay.export(os.path.join(OUT, f'{side}_sole_{name}_on_side.stl'))
            pieces = m.split(only_watertight=False)
            print(f'{side} {name}: hex walls {t} mm, {HEX_ROWS} row(s), {info["cells"]} columns over {info["span"]:.0f} mm, slanted walls at {info["rib_angle"]:.0f} deg; '
                  f'about {info["k"]:.0f} N/mm (TPU for AMS at E 150, beam estimate), {m.volume * DENSITY:.1f} g, watertight {m.is_watertight}, {len(pieces)} piece(s) -> {os.path.relpath(path, ROOT)}')
            if side == 'L':
                shown.append((name, m))
                # what the duck does on it: 0.94 kg on two feet, on one, and a step's peak at about twice that
                w = 0.94 * 9.81
                print(f'   compresses ~{w / 2 / info["k"]:.2f} mm standing on two feet, {w / info["k"]:.2f} on one, ~{2 * w / info["k"]:.2f} at a step\'s peak')
    render(shown, os.path.join(OUT, 'suspension_soles.png'))
    print('render', os.path.relpath(os.path.join(OUT, 'suspension_soles.png'), ROOT))


if __name__ == '__main__':
    sys.exit(main())
