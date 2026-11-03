"""milli, a microduck-sized biped on Feetech STS3215 legs: the one source of truth for kinematics, servos, masses
and outer shape.

Run `python -I spec/robot.py` to write spec/robot.json, which the offline checks, the robot-file writer and the
Fusion build all read. Never hand-edit robot.json or the Fusion document: change this file and rebuild.

Frame: metres, X forward, Y left, Z up, floor at z = 0. Zero pose: standing with straight legs, head level, beak
shut. All geometry is written in WORLD coordinates at the zero pose. Each link's frame sits at its parent joint's
origin with world-aligned axes. The left leg is written once; the right is its mirror (y -> -y).

The look is Pollen Robotics' microduck (2026-11-02, the user: "looks of microduck for sure"): a big rounded hood
of a head with one eye and an orange bill on a neck of bare servos, a small white body, bare black servos at the
hips and knees, orange shoes on yellow soles. Its joint layout too (leg: hip yaw, roll, pitch, knee, ankle; head:
neck pitch, head pitch, head yaw, head roll, beak). Its servos are not: the hips and knees are Feetech STS3215s,
the SO-101 arm's servo; the ankles and head ROBOTIS XC330/XL330s (spec/actuators.json). The servo cases are the
structure: each sits in its parent link with its horn on the joint axis; printed plates join horn to case.

Geometry roles (as echo's, the repo this method is forked from):
  shell     outer cover (printed PLA). May overlap the shells and parts of ADJACENT links.
  decal     cosmetic surface detail (the eye). Must touch its link.
  struct    rigid internal part (printed bracket, battery, boards). Must not overlap rigid parts of any other link.
  actuator  bought servo case. Rigid. Lives in the joint's PARENT link, its shaft on the joint axis.
"""
import copy
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ACT = {k: v for k, v in json.load(open(os.path.join(HERE, 'actuators.json'), encoding='utf-8')).items()
       if not k.startswith('_')}

# microduck's classic colourway (it ships in four)
WHITE, ORANGE, YELLOW, BLACK, DARK, GREY = '#ECEBE6', '#E8642A', '#F2B233', '#1B1C1F', '#3A3D42', '#9A9C98'
ALU, CELL, LENS, PCB = '#A8ACB0', '#2E3B4E', '#0A1420', '#1F5A36'
AMBER = '#F0A030'                                  # the eye ring

LINKS, JOINTS = {}, []

# Materials (tools/mass_model.py): a part's mass is its material's density times its volume (a shell's wall, a
# bracket's solid times a fill factor by thickness), unless the part gives an explicit 'mass'.
MATERIALS = {
    'pla': dict(density=1240, note='PLA (FDM): shells, brackets and shoes; brackets with a fill factor'),
    'tpu': dict(density=1210, note='TPU 95A: the soles'),
    'cells': dict(density=2500, note='battery: explicit mass'),
    'electronics': dict(density=1500, note='computer, servo hat, regulator, IMU, camera: explicit masses'),
    'steel': dict(density=7800, note='bought ball bearings: explicit masses, half on each race'),
}


def material_of(g):
    if g.get('material'):
        return g['material']
    if g['role'] == 'actuator':
        return 'actuator'
    return 'tpu' if g['color'] == YELLOW else 'pla'


# ---------------------------------------------------------------- primitives (world coords, zero pose)

def cyl(name, c, axis, r, h, color=ALU, role='struct'):
    return dict(kind='cyl', name=name, c=list(c), axis=axis, r=r, h=h, color=color, role=role)


def ell(name, c, r, color=GREY, role='shell'):
    return dict(kind='ellipsoid', name=name, c=list(c), r=list(r), color=color, role=role)


def rbox(name, c, size, fillet, color=ALU, role='struct', exposed=False, **extra):
    """extra: mass-model fields ('mass', 'add_mass', 'add_what', 'material', 'fill'; tools/mass_model.py)."""
    return dict(kind='rbox', name=name, c=list(c), size=list(size), fillet=fillet, color=color, role=role,
                exposed=exposed, **extra)


def cap(name, p0, p1, r, color=BLACK, role='shell'):
    return dict(kind='capsule', name=name, p0=list(p0), p1=list(p1), r=r, color=color, role=role)


def loft(name, sections, color=GREY, role='shell', open=('top', 'bottom'), clip=None, keep=None, along='z'):
    """sections: (z, cx, cy, a, b, n): superellipse |dx/a|^n + |dy/b|^n = 1 in the plane z, bottom to top or
    top to bottom. n = 2 is an ellipse, larger n is squarer. open: ends where the skin is a sleeve (no cap).
    clip: (point, normal): keep only the part in front of this plane (a visor cut from a head shape); or a list of
    them: keep the part in front of every one (a shoe collar, a band between two planes).
    keep: (centre, radius): keep only the part inside this sphere (a domed top, round about the vertical through
    the centre, so a yaw joint on that line turns it in place)."""
    secs = [dict(z=z, cx=cx, cy=cy, a=a, b=b, n=n) for z, cx, cy, a, b, n in sections]
    g = dict(kind='loft', name=name, sections=sorted(secs, key=lambda s: s['z']), color=color, role=role,
             open=list(open))
    if along == 'x':          # sections are front-view slices stacked back to front: (x, cz, cy, a (half height), b, n)
        g['along'] = 'x'
    if clip:
        planes = [dict(p=list(c[0]), n=list(c[1]), **({'r': c[2]} if len(c) > 2 else {}))
                  for c in (clip if isinstance(clip, list) else [clip])]
        g['clip'] = planes if isinstance(clip, list) else planes[0]
    if keep:
        g['keep'] = dict(c=list(keep[0]), r=keep[1])
    return g


def rounded(plane, r):
    """A clip plane whose cut rim is rounded with radius r (in Fusion; the checks keep the sharp, larger shape)."""
    return plane[0], plane[1], r


def cut(g, *targets):
    """g removed from the named geoms of the same link (a window through a shoe): role 'cut', no body of its own."""
    return dict(g, role='cut', targets=list(targets))


def below(p, q):
    """Clip plane through the side-view points p = (x, z) and q, keeping what is below the line pq (any y)."""
    dx, dz = q[0] - p[0], q[1] - p[1]
    n = (dz, 0.0, -dx) if dx > 0 else (-dz, 0.0, dx)        # the normal pointing down
    return (p[0], 0.0, p[1]), n


def above(p, q):
    pt, n = below(p, q)
    return pt, tuple(-v for v in n)


def ahead(x):
    """Clip plane keeping x > x0 (in front)."""
    return (x, 0.0, 0.0), (1.0, 0.0, 0.0)


def behind(x):
    return (x, 0.0, 0.0), (-1.0, 0.0, 0.0)


LENS = '#0A1420'


def front_x(sections, y, z):
    """x of a loft's front surface at (y, z), interpolated between sections the way the loft is (PCHIP; a straight
    line between sections left the face mark buried 2-3 mm in Fusion, 2026-10-31)."""
    from scipy.interpolate import PchipInterpolator
    s = sorted(sections)
    f = [PchipInterpolator([q[0] for q in s], [q[k] for q in s]) for k in (1, 2, 3, 4, 5)]
    cx, cy, a, b, n = (float(g(z)) for g in f)
    return cx + a * (1 - abs((y - cy) / b) ** n) ** (1 / n)


def camera_port(name, sections, z, r):
    """A camera port on the centre line of a loft's front, square to the surface (the face slopes): dark ring
    0.6 mm proud, glossy lens 1.5 mm proud."""
    xs = front_x(sections, 0, z)
    slope = (front_x(sections, 0, z + 0.002) - front_x(sections, 0, z - 0.002)) / 0.004
    n = (1.0 / (1 + slope * slope) ** 0.5, 0.0, -slope / (1 + slope * slope) ** 0.5)     # outward normal
    at = lambda d: (xs + n[0] * d, 0.0, z + n[2] * d)
    return [cyl(f'{name} ring', at(0.0006 - 0.003), list(n), r, 0.006, '#2A2C30', 'decal'),
            cyl(f'{name} lens', at(0.0015 - 0.003), list(n), 0.5 * r, 0.006, LENS, 'decal')]


def revolve(name, axis, c, profile, color=GREY, role='shell'):
    """Solid of revolution about the axis-aligned line through c; profile (t, r) with t the coordinate along the
    axis (first and last r = 0). Round about its axis, so it never sweeps as a joint on that axis turns."""
    return dict(kind='revolve', name=name, axis=axis, c=list(c), profile=[list(p) for p in profile], color=color,
                role=role)


def prism(name, x0, t, pts, color, role='decal'):
    """A flat convex polygon in the plane x = x0, points (y, z), extruded t along +x."""
    return dict(kind='prism', name=name, x0=x0, t=t, pts=[list(p) for p in pts], color=color, role=role)




def plate(name, y0, t, circles, color=WHITE, role='shell', n=24, axis='y', **extra):
    """A flat plate in the side view, from y0 to y0 + t: the convex hull of circles ((x, z, r), ...) -- a rounded
    triangle round two pivots and a corner, as microduck's thigh covers and jaw tabs. axis 'x': circles (y, z, r),
    from x = y0; axis 'z': circles (x, y, r), from z = y0."""
    import math as _m
    pts = [(x + r * _m.cos(2 * _m.pi * k / n), z + r * _m.sin(2 * _m.pi * k / n)) for x, z, r in circles
           for k in range(n)]
    pts = sorted(set(pts))
    lower, upper = [], []
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if axis != 'y':
        extra['axis'] = axis
    return dict(kind='plate', name=name, y0=y0, t=t, pts=[list(p) for p in hull], color=color, role=role, **extra)


def link(name, budget, geoms, note=''):
    """budget: a hand estimate of the link's mass (kg), kept for comparison; the real mass comes from the parts'
    materials (tools/mass_model.py)."""
    LINKS[name] = dict(name=name, budget=budget, geoms=list(geoms), note=note)


# The bearings, as microduck's (2026-11-02, the user: "add the bearings like micro"; measured by slicing its model).
# A thin bearing on the joint's axis, its bore round the servo's horn: the inner race half on the horn and half on a boss
# of the horn's link, which shoulders on it; the outer race on a thin floor over the case's face, so a tilt goes straight
# into the case instead of bending the servo's shaft. Round about the axis, so the turning case never meets it: no post
# round the case (a post has to clear the case's corners, 24 mm out on an STS3215, whatever the range). The bore is the
# horn's size: STS3215 20 mm (SO-101's mesh), XL/XC330 16 mm (microduck's). floor + w + clear: the case's face to the
# horn link's plate. Unlike microduck's, the outer race also sits in a printed seat. The STS3215's face steps down 2.5 mm
# round its horn (mesh: 14.5 against 17), which the box model does not show: the real seat's floor fills that step and
# takes 2 M2 x 6 in the near holes, under the bearing. The boss makes the horn screws M3 x 10. Masses: 6704ZZ 6.9 g (EZO
# F6704ZZ listing; others list 5-10 g), the others scaled from it by volume: confirm before ordering.
BEARINGS = {
    'STS3215': dict(part='6704ZZ', d=0.020, D=0.027, w=0.004, floor=0.00045, clear=0.00055, wall=0.002, mass=0.0069),
    'XL330': dict(part='MR2216ZZ', d=0.016, D=0.022, w=0.004, floor=0.001, clear=0.0005, wall=0.0015, mass=0.0048),
    'ankle': dict(part='6700ZZ', d=0.010, D=0.015, w=0.004, mass=0.0026),
}
RACE = 0.00125                                     # a race's radial thickness as drawn (the shield between them)


def bearing_of(act):
    return BEARINGS['STS3215' if act.startswith('STS') else 'XL330']


def stack_of(act, bearing):
    """The case's face to the horn link's plate."""
    b = bearing_of(act)
    return b['floor'] + b['w'] + b['clear'] if bearing else ACT[act]['horn_h']


def joint(name, parent, child, origin, axis, lim, act, out=+1, long='-x', exposed=True, remote_at=None,
          case_in='parent', fork_at=None, fork_r=None, post=True, fork=True, sides=(1, -1), faces=('horn', 'rear'),
          bearing=(), face_t=None):
    """A servo-driven joint. origin: the centre of the horn's outer face, on the axis. act: the servo model, its
    case in `parent`: the shaft along `axis`, the horn facing `out` (+1 / -1 along the axis) toward the child, the
    case's long side running `long` ('+x' .. '-z') from the shaft (the shaft sits shaft_x off the case's middle).
    The horn (with a 0.5 mm overlap into the child's bracket) goes on the child. act_c: the shaft at the case's
    mid-depth, on the axis (tools/checks.py 'axis'). remote_at: the servo's horn face somewhere else (a parallel
    axis): it drives the joint through a rod, as microduck's jaw; no horn on the child. The mount (mount_geoms):
    fork_at (deg) / fork_r (m) fix where the fork's post goes; post=False when the link's own plates join the fork's
    two plates; fork=False: the driven horn only, no rear horn, its screws in the link's own plate. sides: which of the
    cradle's side walls (+1 / -1 along the servo frame's w) to build; faces: which face plates; bearing: on which faces a
    bearing sits ('horn', 'rear'; BEARINGS); face_t: a thinner horn face plate than MT."""
    a = ACT[act]
    ax = {'x': 0, 'y': 1, 'z': 2}[axis]
    act_c = list(remote_at or origin)
    stack = stack_of(act, bearing)
    act_c[ax] -= out * (stack + a['box'][2] / 2)
    j = dict(name=name, parent=parent, child=child, origin=list(origin), axis=axis, lower=lim[0], upper=lim[1],
             act=act, act_c=act_c, out=out, long=long, exposed=exposed, remote=bool(remote_at), case_in=case_in,
             fork_at=fork_at, fork_r=fork_r, post=post, fork=fork, sides=list(sides), faces=list(faces),
             bearing=list(bearing), stack=stack, face_t=face_t,
             capacity=dict(model=act, count=1, ratio=1.0))
    JOINTS.append(j)
    return j


def servo_geoms(j, color=BLACK):
    """The servo case (in the parent) and its horn (in the child) for joint j."""
    a = ACT[j['act']]
    L, W, H = a['box']
    ax = {'x': 0, 'y': 1, 'z': 2}[j['axis']]
    lx = {'x': 0, 'y': 1, 'z': 2}[j['long'][1]]
    ls = 1 if j['long'][0] == '+' else -1
    c = list(j['act_c'])
    c[lx] += ls * a['shaft_x']
    size = [W, W, W]
    size[ax], size[lx] = H, L
    case = rbox(f"{j['name']} actuator (buy) {j['act']}", c, size, 0.0015, color, 'actuator')
    hc = list(j['origin'])
    hc[ax] -= j['out'] * (j['stack'] - 0.0005) / 2
    horn = cyl(f"{j['name']} flange", hc, j['axis'], 0.4 * W, j['stack'] + 0.0005, ALU, 'struct')
    return case, horn


def fast(g, size, L, p, d, **extra):
    """g, a bought screw: size, length L, p under its head, d the way it goes in (tools/assembly.py checks them)."""
    return dict(g, fast=dict(size=size, L=L, p=[float(v) for v in p], d=[float(v) for v in d], **extra))


def box(name, lo, hi, color=DARK, role='struct', fillet=0.001, **extra):
    """An rbox from its corners."""
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    s = [b - a for a, b in zip(lo, hi)]
    return rbox(name, c, s, min(fillet, min(s) / 2 - 1e-4), color, role, **extra)


# ---------------------------------------------------------------- servo mounts (the LeRobot SO-101's way)
# (2026-11-02, the user: "refer to lerobot assembly guide so101"; "skip the sleeve"). Every servo slides into a
# CRADLE on the link that carries its case: a plate on each face over the case's far end, side walls, and an end wall
# with a window for the 3-pin cables; it takes 2 screws per face at the far pilot holes (STS3215: M2 x 6 self-tapping;
# XL/XC330: M2 x 8 through the case's frame holes). The other link is a FORK on both horns (the driven horn and the
# passive rear horn, 4 screws each; a centre screw on the driven horn only), its bridge round the case's short end,
# outside the case's reach. Hole positions: spec/actuators.json (measured on the makers' STEP files and meshes).
MT = 0.003                                         # printed plate thickness

def servo_frame(j):
    """(c, u, w, a): the case's middle, and unit axes: u along the case from the shaft to its far end, a from the
    case toward the horn face, w the third."""
    a = ACT[j['act']]
    ax = {'x': 0, 'y': 1, 'z': 2}[j['axis']]
    lx = {'x': 0, 'y': 1, 'z': 2}[j['long'][1]]
    wx = 3 - ax - lx
    e = lambda i, sg: [sg if k == i else 0.0 for k in range(3)]
    c = list(j['act_c'])
    c[lx] += (1 if j['long'][0] == '+' else -1) * a['shaft_x']
    return c, e(lx, 1 if j['long'][0] == '+' else -1), e(wx, 1.0), e(ax, j['out'])


def at(f, u, w, a):
    c, U, W_, A_ = f
    return [c[k] + u * U[k] + w * W_[k] + a * A_[k] for k in range(3)]


def lbox(name, f, ur, wr, ar, color=DARK, role='struct', **extra):
    """A box given by local ranges (u, w, a) in the servo frame f."""
    p, q = at(f, ur[0], wr[0], ar[0]), at(f, ur[1], wr[1], ar[1])
    return box(name, [min(x, y) for x, y in zip(p, q)], [max(x, y) for x, y in zip(p, q)], color, role, **extra)


def lcyl(name, f, u, w, a, r, h, color, role):
    ax = 'xyz'[[abs(v) for v in f[3]].index(1.0)]
    return cyl(name, at(f, u, w, a), ax, r, h, color, role)


def rot(v, k, q):
    """v rotated by q about the unit vector k (Rodrigues)."""
    c, s_ = math.cos(q), math.sin(q)
    kv = sum(a * b for a, b in zip(k, v))
    kx = [k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2], k[0] * v[1] - k[1] * v[0]]
    return [v[i] * c + kx[i] * s_ + k[i] * kv * (1 - c) for i in range(3)]


def post_r(A):
    return 0.005 if 'case_holes_horn' in A else 0.004


def fork_post(j, u0):
    """(psi, rho): where the fork's post goes round the shaft in the servo frame (psi from +u toward +w), at the
    smallest distance where it clears the case and its cradle at every angle of the joint's range (GAP between).
    The case's link turns against the fork's: by -q when the case is in the parent, +q when in the child.
    j['fork_at'] (degrees) fixes psi, for a joint whose nearest clear direction is taken by its neighbours."""
    if j.get('fork_r') is not None:
        return math.radians(j['fork_at']), j['fork_r']
    A = ACT[j['act']]
    L, W, H = A['box']
    sx = A['shaft_x']
    pr = post_r(A)
    _, U, Wv, _ = servo_frame(j)
    k = [0.0, 0.0, 0.0]
    k['xyz'.index(j['axis'])] = 1.0
    sg = 1 if j['case_in'] == 'child' else -1
    rects = [(-(L / 2 - sx), L / 2 + sx, W / 2), (u0 + sx, L / 2 + sx + MT, W / 2 + MT)]   # (u from shaft), |w|
    qs = [j['lower'] + (j['upper'] - j['lower']) * i / 40 for i in range(41)]

    def clear(psi, rho):
        v = [rho * (math.cos(psi) * U[i] + math.sin(psi) * Wv[i]) for i in range(3)]
        for q in qs:
            r = rot(v, k, -sg * q)                 # the post in the case's frame
            u, w = sum(a * b for a, b in zip(r, U)), sum(a * b for a, b in zip(r, Wv))
            for a0, a1, hw in rects:
                du = max(a0 - u, 0, u - a1)
                dw = max(abs(w) - hw, 0)
                if math.hypot(du, dw) < pr + GAP:
                    return False
        return True

    best = None
    for deg in ([j['fork_at']] if j.get('fork_at') is not None else range(0, 360, 3)):
        psi = math.radians(deg)
        rho = A['horn_r'] + pr
        while not clear(psi, rho) and rho < 0.08:
            rho += 0.0005
        if best is None or rho < best[1] - 1e-9:
            best = (psi, rho)
    return best


def mount_geoms(j):
    """(parts for the case's link, parts for the horn's link) for joint j."""
    A = ACT[j['act']]
    L, W, H = A['box']
    sx, hh = A['shaft_x'], j['stack']
    f = servo_frame(j)
    n, ex = j['name'].replace('_', ' '), dict(exposed=j['exposed'])
    sts = 'case_holes_horn' in A
    holes_h = A['case_holes_horn'] if sts else A['case_holes_through']
    holes_r = A['case_holes_rear'] if sts else A['case_holes_through']
    # far holes: the two furthest from the shaft (the tables give them from the case's middle, the far end at -x)
    far_h = sorted(holes_h, key=lambda p: p[0])[:2]
    far_r = sorted(holes_r, key=lambda p: p[0])[:2]
    head = 0.0019                                  # M2 pan head radius
    u0 = min(-p[0] for p in far_h + far_r) - head - 0.0006
    win = 0.012 if W > 0.022 else 0.010            # cable window in the end wall
    cmt = j.get('face_t') or min(MT, hh - 0.0005)  # face plates under the horn's height (the fork turns over them);
    #                                                XL/XC330 screws sit in counterbores
    fc, sd, bg = j.get('faces', ('horn', 'rear')), j.get('sides', (1, -1)), j.get('bearing', ())
    wl = (-W / 2 - (MT if -1 in sd else 0), W / 2 + (MT if 1 in sd else 0))      # the cradle's width
    ax = j['axis']
    ai = 'xyz'.index(ax)
    d = {'x': (1, 2), 'y': (0, 2), 'z': (0, 1)}[ax]

    def pp(u, w):
        q = at(f, u, w, 0)
        return q[d[0]], q[d[1]]

    def axial(a0, a1):
        return min(at(f, 0, 0, a0)[ai], at(f, 0, 0, a1)[ai]), abs(a1 - a0)

    def ring(name, sg, a0, a1, r, bore, color=DARK, **extra):
        """A ring on the shaft, a0 to a1 from the case's face sg, and the cut that hollows it."""
        mid = sg * (H / 2 + (a0 + a1) / 2)
        return [dict(lcyl(name, f, -sx, 0, mid, r, a1 - a0, color, 'struct'), **ex, **extra),
                cut(lcyl(f'{name} bore', f, -sx, 0, mid, bore, a1 - a0 + 0.002, color, 'struct'), name)]

    def seat(nm, side, sg):
        """A face plate from the far end to a seat round the shaft, and the bearing's outer race in it."""
        b = bearing_of(j['act'])
        r_d, r_o, fl = b['d'] / 2, b['D'] / 2, b['floor']
        R, e = r_o + b['wall'], 0.001
        clear_in = r_d + RACE + 0.0002             # the inner race turns free of the floor
        out = [plate(nm, *axial(sg * H / 2, sg * (H / 2 + cmt)),
                     [(*pp(-sx, 0), R), (*pp(L / 2 - e, wl[0] + e), e), (*pp(L / 2 - e, wl[1] - e), e)], DARK, 'struct',
                     axis=ax, **ex)]
        if cmt > fl + 1e-9:                        # a thick plate: the bore, and a floor ring under the bearing
            out += [cut(lcyl(f'{nm} bore', f, -sx, 0, sg * (H / 2 + cmt / 2), r_o - 0.00005, cmt + 0.002, DARK, 'struct'), nm)]
            out += ring(f'{n} {side} seat floor', sg, 0, fl, r_o, clear_in)
        else:                                      # a thin sheet is the floor; a wall round the bearing on it
            out += [cut(lcyl(f'{nm} bore', f, -sx, 0, sg * (H / 2 + cmt / 2), clear_in, cmt + 0.002, DARK, 'struct'), nm)]
            out += ring(f'{n} {side} seat wall', sg, 0, fl + 0.003, R, r_o - 0.00005)
        for g_ in (1, -1):                         # no cradle wall on this side: nothing past the bearing either
            if g_ not in sd:
                out.append(cut(lbox(f'{nm} trim {g_}', f, (-sx - R - 0.001, L / 2 + 0.001),
                                    sorted((g_ * (r_o + 0.0001), g_ * (R + 0.001))),
                                    (min(sg * H / 2, sg * (H / 2 + cmt)) - 0.001, max(sg * H / 2, sg * (H / 2 + cmt)) + 0.001)), nm))
        if sts and side == 'horn':                 # the near holes, under the bearing (BEARINGS)
            for k, (x, y) in enumerate(sorted(holes_h, key=lambda p: p[0])[2:]):
                out.append(fast(lcyl(f'{n} cradle screw near {k}', f, -x, y, sg * (H / 2 + fl / 2), head, fl, DARK, 'decal'),
                                'M2', 0.006, at(f, -x, y, sg * (H / 2 + fl)), [-sg * v for v in f[3]]))
        out += ring(f'{n} {side} bearing outer race', sg, fl, fl + b['w'], r_o, r_o - RACE, ALU, material='steel',
                    mass=b['mass'] / 2, on_joint=j['name'])
        return out

    cr = []
    for side, sg in (('horn', 1), ('rear', -1)):
        if side not in fc:
            continue
        nm = f'{n} cradle {side} face'
        if side in bg:
            cr += seat(nm, side, sg)
        else:
            cr.append(lbox(nm, f, (u0, L / 2), wl, sorted((sg * H / 2, sg * (H / 2 + cmt))), **ex))
    ea = (-H / 2 - (cmt if 'rear' in fc else 0), H / 2 + (cmt if 'horn' in fc else 0))   # the end wall's height
    cr += [lbox(f'{n} cradle end +', f, (L / 2, L / 2 + MT), (win / 2, wl[1]), ea, **ex),
           lbox(f'{n} cradle end -', f, (L / 2, L / 2 + MT), (wl[0], -win / 2), ea, **ex)]
    for sg in sd:
        cr.append(lbox(f"{n} cradle side {'+' if sg > 0 else '-'}", f, (u0, L / 2),
                       (W / 2, W / 2 + MT) if sg > 0 else (-W / 2 - MT, -W / 2), (-H / 2, H / 2), **ex))
    for side, holes, a0 in (('horn face', far_h, H / 2 + cmt), ('rear face', far_r, -H / 2 - cmt)):
        if side.split()[0] not in fc:
            continue
        sg = 1 if a0 > 0 else -1
        for k, (x, y) in enumerate(holes):
            cr.append(fast(lcyl(f'{n} cradle screw {side} {k}', f, -x, y, a0 + sg * 0.00075, head, 0.0015, DARK, 'decal'),
                           'M2', 0.006 if sts else 0.008, at(f, -x, y, a0), [-sg * v for v in f[3]]))
    if j['remote']:
        return cr, []
    hr, hd = A['horn_hole_r'], A['horn_hole_deg']
    sh = 0.0027 if sts else head                   # M3 (STS3215 horns) or M2 (XL/XC330 horns) pan head
    top, bot = H / 2 + hh, -H / 2 - hh
    fk = [lcyl(f'{n} horn centre screw', f, -sx, 0, top + MT + 0.00075, sh, 0.0015, DARK, 'decal')]
    for side, sg in (('horn', 1), ('rear', -1)):   # the inner race on the horn and its boss, the boss's shoulder on it
        if side in bg:
            b = bearing_of(j['act'])
            fl, r_i = b['floor'], b['d'] / 2 + RACE
            fk += ring(f'{n} {side} bearing inner race', sg, fl, fl + b['w'], r_i, 0.4 * W - 0.00005, ALU, material='steel',
                       mass=b['mass'] / 2, on_joint=j['name'])
            fk.append(dict(lcyl(f'{n} {side} boss shoulder', f, -sx, 0, sg * (H / 2 + fl + b['w'] + b['clear'] / 2), r_i,
                                b['clear'], DARK, 'struct'), **ex))
    faces_ = [(top + MT, 1, 'horn')]
    if j.get('fork', True):
        # the fork: a plate on each horn, joined by a post where the case and its cradle never go over the joint's range
        faces_.append((bot - MT, -1, 'rear'))
        fw, pr = hr + sh + 0.001, post_r(A)
        if j.get('post', True) or j.get('fork_r') is not None:
            psi, rho = fork_post(j, u0)
        else:
            psi, rho = 0.0, 0.0                    # discs on the horns: the link's own plates join them
        pr = pr if j.get('post', True) else MT
        pu, pw = -sx + rho * math.cos(psi), rho * math.sin(psi)
        circ = [(*pp(-sx, 0), fw), (*pp(pu, pw), pr)]
        fk += [plate(f'{n} fork horn plate', *axial(top, top + MT), circ, DARK, 'struct', axis=ax, **ex),
               plate(f'{n} fork rear plate', *axial(bot - MT, bot), circ, DARK, 'struct', axis=ax, **ex),
               dict(lcyl(f'{n} rear horn', f, -sx, 0, -H / 2 - hh / 2 - 0.00025, A['horn_r'], hh + 0.0005, ALU, 'struct'),
                    **ex)]
        if j.get('post', True):
            fk.append(plate(f'{n} fork post', *axial(bot - MT, top + MT), [(*pp(pu, pw), pr)], DARK, 'struct', axis=ax,
                            **ex))
    for a0, sg, nm in faces_:
        for k, dg in enumerate(hd):
            t = math.radians(dg)
            u_, w_ = -sx + hr * math.cos(t), hr * math.sin(t)
            fk.append(fast(lcyl(f'{n} fork screw {nm} {k}', f, u_, w_, a0 + sg * 0.00075, sh, 0.0015, DARK, 'decal'),
                           'M3' if sts else 'M2', 0.010 if sts else (0.008 if nm in bg else 0.006), at(f, u_, w_, a0),
                           [-sg * v for v in f[3]]))
    return cr, fk


# ---------------------------------------------------------------- servo sizes

STS, XL, XC = ACT['STS3215_C044'], ACT['XL330_M288'], ACT['XC330_M288']
SL, SW, SH = STS['box']                    # 45.2 x 24.7 x 35 mm (long, wide, along the shaft)
SX = STS['shaft_x']                        # shaft 12.5 mm off the case's middle
SHH = stack_of('STS3215_C044', True)       # the case's face to the plate on its horn, over the bearing (5 mm)
XLL, XLW, XLH = XL['box']                  # 34 x 20 x 26 mm
XLX, XLHH = XL['shaft_x'], XL['horn_h']
XLS = stack_of('XL330_M288', True)         # the same on the head's XL330s that carry a bearing (5.5 mm)
GAP = 0.003                                # clearance between parts of different links that move against each other

# ---------------------------------------------------------------- proportions (iterate here)

# Leg (round 9, 2026-11-02; the user: "something is wrong with joint positioning... get the microduck urdf and check
# joints... why so much gap between legs and main body"). microduck's own joints, measured on its model, set the
# layout; the zero pose IS microduck's stance (as its model's), so every servo case is square to the axes in it:
#   hip yaw   in the body, horn down;
#   hip roll  standing right under the yaw servo, horn forward (microduck's roll horns face front at the hip's middle);
#   hip pitch at the roll axis' height, out to the side on the roll bracket: its servo lies flat in the thigh, horn in
#             (the case rides in the thigh, as microduck's);
#   knee      behind and below the hip (the thigh slopes back 58 deg); its servo stands upright in the thigh's back;
#             one cover wraps both thigh servos (microduck's rounded triangle);
#   ankle     straight under the knee; its servo stands in the shin, between the shoe's two ears.
STANCE = 1.02                                      # microduck's thigh angle back from upright (its model: 58.4 deg)
ZA = 0.0295                                        # ankle: microduck's 25 mm at 1.18; its case's lower end clears the shoe
#   knee: microduck's 42 mm shin at milli's scale; the ankle case's top stays clear of the knee case's 16 mm circle
ZK = ZA + 0.053
#   hip pitch: the knee servo just behind the hip pitch servo's back end, both in the thigh
XK = -(SL / 2 + SX) - SW / 2 - 0.0035              # -0.051: the knee behind the hip, one cradle wall (3 mm) between
#                                                    the hip pitch case's end and the knee case (2026-11-02, mounts)
THIGH = -XK / math.sin(STANCE)                     # 57 mm (microduck's 42 at 1.36)
ZP = ZK - XK / math.tan(STANCE)                    # 0.111
ZR = ZP                                            # hip roll: at the hip pitch axis' height, as microduck's
#   hip yaw: its horn on a plate on the roll case's top (the roll shaft 10 mm below that top): 13 mm above the roll
#            axis (microduck's: 12.5)
ZY = ZR + SL / 2 - SX + 0.010                      # a 10 mm spacer: room under the body for the thigh covers to roll

# Lateral (left leg, y > 0), from the middle out
YY = 0.016                                         # hip yaw and roll: the two yaw cases side by side, 7 mm apart
# hip roll 2.5 mm outboard of the yaw axis: its bearing is wider than its case, and the two would meet as a leg yaws in
YR = YY + 0.0025
XRH = SH / 2 + SHH                                 # hip roll horn face, in front of the roll case (0.022)
YRS = (YR + SW / 2 + 0.0061, YR + SW / 2 + 0.0091)  # the roll bracket's side plate, clear of the rolling roll case
YT_CASE = (YRS[1] + SHH, YRS[1] + SHH + SH)        # the thigh's two servo cases (0.042 .. 0.077)
YP = YRS[1]                                        # hip pitch horn face, inward onto the roll bracket
YK = YRS[1]                                        # knee horn face, inward onto the shin plate
YS = (YRS[0], YRS[1])                              # the shin plate
YA_CASE = (YS[1], YS[1] + XC['box'][2])            # the ankle case, outside the shin plate
YA = YA_CASE[1] + XC['horn_h']                     # ankle horn face, outward (0.0665)
XP_FRONT = SL / 2 - SX                             # hip pitch case's front end (0.0101; it runs back)
# microduck's shoe at 1.18 (its foot_left, sole_left and ankle_left meshes): a 13 mm yellow sole (15 here), the orange
# upper rising at the toe and heel to 22 mm, the ears round the ankle; low in the middle, where the ankle servo swings
FOOT = dict(x=(XK - 0.024, XK + 0.040), y=(0.029, 0.078), sole=0.0154, shoe=0.0160, rim=0.0225)   # sole 12.9 and upper 6 mm on microduck
THIGH_Y = (YT_CASE[0] - 0.002, YT_CASE[1] + 0.0061)  # the thigh cover, wrapping both thigh servos

# Body (round 2): the two hip yaw servos side by side; behind them the battery on edge and the Pi Zero 2 W with its
# servo hat, upright; the 5 V regulator and the IMU on the top plate. The battery is the smallest that runs it (user,
# 2026-11-02): a 2S LiPo of about 800 mAh, 60 x 30 x 14 mm, 45 g (7.4 V straight to the STS3215s; confirm a part
# before ordering). The neck servo stands bare in front of the body, as microduck's does (round 1 had it on a block
# on the body's top: 5 cm taller).
YAW_TOP = ZY + SHH + SH                            # top of the hip yaw cases (0.218)
PLATE = (YAW_TOP, YAW_TOP + 0.0035)                # the body's top plate
# round 9: the lower edge 10 mm over the yaw horns and tucked in (the hip yaw cases' feet show under it, as microduck's
# dark band), so the thigh covers can roll up under it
# round 10 (the user: "the box is also big, do we need that?"): no. The Pi Zero goes in the head, behind the face, as
# microduck's; the body holds the yaw servos, the battery and a thin servo-bus board behind it, and its front is flush
# with the neck servo's (microduck's neck column stands at its body's front edge): 98 mm long (microduck's: 96 at 1.18)
BODY = dict(x=(-0.058, 0.040), top=PLATE[1] + 0.004, bottom=ZY + 0.003)
XN = 0.028                                         # neck pitch axis: its case in the body's front, as microduck's
ZN = ZY + SHH - 0.001 + XLL / 2 + XLX              # its case's foot level with the yaw cases' (0.207)
ZH = ZN + 0.0514                                   # head pitch: straight above, the neck one column (round 6)
# head yaw: its case forward of the head pitch case (clear of its 13 mm circle), so it can sit low
# head yaw (round 6, the user: "neck needs improvement"): microduck's neck is one straight column of servos, the head
# yaw servo on top of it inside the head's underside. Its case straight over the head pitch servo, clear of its 13 mm
# circle (round 5 had it 14 mm ahead: an L-shaped neck)
YAW_FOOT = ZH + 0.0131 + GAP + 0.004               # the head pitch U's bridge: clear of its servo's 13 mm circle
XHY, ZHY = XN + XLX, YAW_FOOT + XLH + XLS
XHR, ZHR = XHY + XLH / 2 + XLS, ZHY + XLHH + XLW / 2            # head roll horn face and axis height
HEAD_Z = ZHY - 0.008                               # the head's lower edge: the yaw horn 8 mm up inside it
HEAD_CX = XN + 0.006                               # the head reaches as far behind the neck as in front, as microduck's


# ---------------------------------------------------------------- body (root)

link('trunk', 0.40, [
    box('top plate', (-0.052, -0.025, PLATE[0]), (XP_FRONT, 0.025, PLATE[1])),
    box('battery 2S 800 mAh', (-0.052, -0.030, PLATE[0] - 0.030), (-0.038, 0.030, PLATE[0]), CELL,
        material='cells', mass=0.045),
    box('servo bus board', (-0.0552, -0.025, PLATE[0] - 0.030), (-0.0515, 0.025, PLATE[0]), PCB,
        material='electronics', mass=0.010),
    box('5 V regulator and IMU', (-0.030, -0.012, PLATE[1]), (0.000, 0.012, PLATE[1] + 0.0025), PCB,
        material='electronics', mass=0.008),
    box('battery strap', (-0.0525, -0.010, PLATE[0] - 0.030), (-0.0351 + 0.0005, 0.010, PLATE[0] - 0.026)),
    # the neck servo rides in the neck; the body holds it on both sides (round 7, the user: "one sided joints are
    # bad"): a bracket on its horn, a bracket with an idler on its other face, on a block clear of its 13 mm circle
    box('neck mount', (XP_FRONT - 0.0005, -0.0225, ZY + SHH + 0.0005), (XN + XLW / 2, 0.0165, ZN - 0.016), DARK,
        exposed=True),
    box('neck bracket', (XN - XLW / 2, 0.0130, ZN - 0.0165), (XN + XLW / 2, 0.0165, ZN + 0.012), DARK, exposed=True),
    box('neck idler bracket', (XN - XLW / 2, -0.0225, ZN - 0.0165), (XN + XLW / 2, -0.0190, ZN + 0.012), DARK,
        exposed=True),
    # a superellipse of power 5 round the yaw cases' front corners (power 3.2 cut through them, round 2), as narrow
    # as microduck's body in proportion (round 5)
    loft('body', [(BODY['bottom'], -0.009, 0, 0.047, 0.031, 6.0), (BODY['bottom'] + 0.010, -0.009, 0, 0.049, 0.040, 8.0),
                  (BODY['top'] - 0.008, -0.009, 0, 0.049, 0.040, 8.0), (BODY['top'] - 0.003, -0.010, 0, 0.045, 0.036, 5.0),
                  (BODY['top'], -0.011, 0, 0.038, 0.028, 3.5)], WHITE, open=('bottom',)),
    # the neck comes up out of the body through a slot in its top, as microduck's (the user, round 6)
    # down through the front too: the neck folds forward 1.6 rad to tuck the head in (Pollen's desk photo)
    *[fast(cyl(f'body screw {k}', (x_, 0, BODY['top'] + 0.0003), 'z', 0.0019, 0.0012, DARK, 'decal'), 'M2', 0.006,
           (x_, 0, BODY['top']), (0, 0, -1)) for k, x_ in enumerate((-0.040, 0.005))],
    cut(box('neck slot', (XN - 0.017, -0.026, ZN - 0.014), (XN + 0.040, 0.0195, BODY['top'] + 0.01), WHITE, 'shell'),
        'body'),
], 'the body: hip yaw servos, battery, Pi Zero 2 W and servo hat, regulator, IMU; the neck servo in front')

# ---------------------------------------------------------------- left leg (bare servos and brackets, as microduck's)

link('L_hip_yaw_link', 0.07, [
    box('L hip yaw plate', (-SH / 2, YY - SW / 2, ZR + SL / 2 - SX), (SH / 2, YR + SW / 2, ZY + 0.0005), exposed=True),
])
link('L_hip_roll_link', 0.07, [
    # microduck's hip_l: from the roll horn at the front, out to the side, where the hip pitch horn turns
    box('L hip roll front', (XRH - 0.0005, YR - 0.011, ZR - 0.010), (XRH + 0.003, YRS[1], ZR + 0.010), exposed=True),
    box('L hip roll side', (-0.012, YRS[0], ZR - 0.010), (XRH + MT, YRS[1], ZR + 0.010), exposed=True),
])
link('L_hip_pitch_link', 0.10, [
    # the thigh: the hip pitch servo lying flat (from the joint, case in the thigh) and the knee servo standing at
    # its back end, joined by a plate on their outer faces and wrapped by microduck's cover
    # the cover's outline, 3 mm in (a rectangle's corner stuck out of the cover: the user, 2026-11-02)
    plate('L thigh plate', YT_CASE[1] - 0.0002, MT + 0.0002,
          [(0.0, ZP, 0.29 * THIGH - 0.003), (XK, ZK, 0.29 * THIGH - 0.003),
           (-0.868 * THIGH, ZP + 0.018 * THIGH, 0.29 * THIGH - 0.003)], DARK, 'struct'),
    # microduck's thigh cover, its outline from its upper_leg mesh: the hull of three circles of 0.29 x the thigh's
    # length, round the hip pivot, round the knee pivot and at the top back corner (-0.868 L, +0.018 L from the hip)
    plate('L thigh cover', THIGH_Y[0], THIGH_Y[1] - THIGH_Y[0],
          [(0.0, ZP, 0.29 * THIGH), (XK, ZK, 0.29 * THIGH), (-0.868 * THIGH, ZP + 0.018 * THIGH, 0.29 * THIGH)],
          WHITE),
    # 2 screws from outside on the pivots, into the thigh plate (microduck's two marks there)
    fast(cyl('L thigh cover screw hip', (0, THIGH_Y[1] + 0.0003, ZP), 'y', 0.0019, 0.0012, DARK, 'decal'), 'M2', 0.006,
         (0, THIGH_Y[1], ZP), (0, -1, 0)),
    fast(cyl('L thigh cover screw knee', (XK, THIGH_Y[1] + 0.0003, ZK), 'y', 0.0019, 0.0012, DARK, 'decal'), 'M2', 0.006,
         (XK, THIGH_Y[1], ZK), (0, -1, 0)),
    # open on the inside, where the two servos and their horns come out
    cut(box('L thigh cover slot', (XK - SW / 2 - 0.001, YS[0] - 0.004, ZK - (SL / 2 - SX) - 0.0015),
            (XP_FRONT + 0.0015, YT_CASE[1] - 0.0003, ZP + SW / 2 + 0.0012), WHITE, 'shell'), 'L thigh cover'),
])
YB = YA_CASE[0] - XC['horn_h']                     # the top of the ankle servo's rear boss
XCHH, ANK = XC['horn_h'], BEARINGS['ankle']
link('L_knee_link', 0.05, [
    box('L shin plate', (XK - 0.011, YS[0], ZA + XC['box'][0] / 2 + XC['shaft_x'] - 0.001), (XK + 0.011, YS[1],
                                                                                           ZK + 0.011), exposed=True),
    box('L shin cap', (XK - 0.010, YS[0], ZA + XC['box'][0] / 2 + XC['shaft_x'] - 0.0005),
        (XK + 0.010, YA_CASE[1], ZA + XC['box'][0] / 2 + XC['shaft_x'] + 0.003), exposed=True),
    # the ankle's far side, as microduck's: a plate on the servo's rear boss (4 M2 x 6), up to the shin plate, and a stub
    # from it through a small bearing in the shoe's inner ear
    dict(cyl('L ankle rear boss', (XK, YB + XCHH / 2, ZA), 'y', XC['horn_r'], XCHH, ALU), exposed=True),
    plate('L ankle stub plate', YB - 0.002, 0.0021, [(XK, ZA, 0.0095), (XK, ZA + XC['box'][0] / 2 + XC['shaft_x'] + 0.002, 0.0095)],
          DARK, 'struct', exposed=True),
    dict(cyl('L ankle stub', (XK, YB - 0.0041, ZA), 'y', ANK['d'] / 2, 0.0042, DARK), exposed=True),
    # flat heads, flush: the bearing's race turns 0.2 mm off this plate
    *[fast(cyl(f'L ankle boss screw {k}', (XK + XC['horn_hole_r'] * math.cos(k * math.pi / 2), YB - 0.00175,
                                           ZA + XC['horn_hole_r'] * math.sin(k * math.pi / 2)), 'y', 0.0019, 0.0005, DARK, 'decal'),
           'M2 flat', 0.006, (XK + XC['horn_hole_r'] * math.cos(k * math.pi / 2), YB - 0.002,
                              ZA + XC['horn_hole_r'] * math.sin(k * math.pi / 2)), (0, 1, 0)) for k in range(4)],
    dict(cyl('L ankle bearing inner race', (XK, YB - 0.0042, ZA), 'y', ANK['d'] / 2 + RACE, ANK['w'], ALU), exposed=True,
         material='steel', mass=ANK['mass'] / 2, on_joint='L_ankle_pitch'),
    cut(cyl('L ankle bearing inner race bore', (XK, YB - 0.0042, ZA), 'y', ANK['d'] / 2 - 0.00005, ANK['w'] + 0.002),
        'L ankle bearing inner race'),
])
SOLE_C = ((FOOT['x'][0] + FOOT['x'][1]) / 2, (FOOT['y'][0] + FOOT['y'][1]) / 2)
SOLE_A, SOLE_B = (FOOT['x'][1] - FOOT['x'][0]) / 2 + 0.0005, (FOOT['y'][1] - FOOT['y'][0]) / 2 + 0.0005
EAR = [(XK, ZA, 0.011), (XK - 0.016, FOOT['rim'] - 0.006, 0.006), (XK + 0.020, FOOT['rim'] - 0.006, 0.006)]
link('L_foot', 0.05, [
    # the shoe's ears (microduck's): orange, rising either side of the ankle servo to round tops on its axis; the
    # outer one on the horn, the inner one on a bearing round the shin's stub (the shoe joins them: no post). The inner
    # ear is its own part: a one-piece shoe cannot go on, its two ears fixed either side of a servo with a stub (found
    # tracing the assembly order). The shoe rises onto the servo, then this ear slides onto the stub, its two lobes in a
    # recess in the shoe, 2 screws into the shoe.
    plate('L ankle ear out', YA - 0.0005, 0.0035, EAR, ORANGE, 'struct', exposed=True),
    plate('L ankle ear in', YB - 0.0067, 0.004, EAR, ORANGE, 'struct', exposed=True),
    cut(cyl('L ankle ear bore', (XK, YB - 0.0047, ZA), 'y', ANK['D'] / 2 - 0.00005, 0.006, ORANGE), 'L ankle ear in'),
    cut(plate('L ankle ear recess', FOOT['y'][0] - 0.001, YB - 0.0028 - FOOT['y'][0] + 0.001, EAR, ORANGE, 'struct'), 'L shoe'),
    *[fast(cyl(f'L ankle ear screw {k}', (XK + dx, YB - 0.0073, FOOT['rim'] - 0.006), 'y', 0.0019, 0.0012, DARK, 'decal'),
           'M2', 0.008, (XK + dx, YB - 0.0067, FOOT['rim'] - 0.006), (0, 1, 0)) for k, dx in enumerate((-0.016, 0.020))],
    dict(cyl('L ankle bearing outer race', (XK, YB - 0.0042, ZA), 'y', ANK['D'] / 2, ANK['w'], ALU), exposed=True,
         material='steel', mass=ANK['mass'] / 2, on_joint='L_ankle_pitch'),
    cut(cyl('L ankle bearing outer race bore', (XK, YB - 0.0042, ZA), 'y', ANK['D'] / 2 - RACE, ANK['w'] + 0.002),
        'L ankle bearing outer race'),
    # microduck's shoe is one rounded block (round 11, the user's side-by-side): the orange upper on the yellow sole,
    # big round edges, the ears rising out of it; the ankle servo sits down in a pocket between the ears
    # (the upper has the sole's outline exactly, so the two read as one block split by colour; it rounds over on top)
    dict(loft('L shoe', [(FOOT['sole'] - 0.001, SOLE_C[0], SOLE_C[1], SOLE_A - 0.0004, SOLE_B - 0.0004, 4.5),
                         (FOOT['sole'], SOLE_C[0], SOLE_C[1], SOLE_A, SOLE_B, 4.5),
                         (FOOT['rim'] - 0.004, SOLE_C[0], SOLE_C[1], SOLE_A, SOLE_B, 4.5),
                         (FOOT['rim'] - 0.0012, SOLE_C[0], SOLE_C[1], SOLE_A - 0.0025, SOLE_B - 0.0025, 4.0),
                         (FOOT['rim'], SOLE_C[0], SOLE_C[1], SOLE_A - 0.0045, SOLE_B - 0.0045, 3.5)], ORANGE, 'struct',
              open=()), exposed=True),
    cut(cyl('L shoe pocket', (XK, (YB - 0.0025 + YA_CASE[1]) / 2, ZA), 'y', 0.017, YA_CASE[1] - YB + 0.0025,
            ORANGE, 'shell'), 'L shoe'),
    # two pieces, as microduck's shoe (its foot and sole meshes) and Open Duck's (a TPU bottom, screwed on from below). The
    # foot switch (2026-11-02, the user: an input to the walking policy, as Open Duck's GPIO foot switches): a subminiature
    # microswitch pressed into the shoe's underside ahead of the ankle pocket, its plunger on the TPU sole, which gives
    # as the foot takes weight. Its travel against this TPU is untested: try it before printing all four
    cut(box('L foot switch pocket', (XK + 0.024 - 0.0063, SOLE_C[1] - 0.00285, FOOT['sole'] - 0.002),
            (XK + 0.024 + 0.0063, SOLE_C[1] + 0.00285, FOOT['sole'] + 0.0048), ORANGE, 'struct'), 'L shoe'),
    box('L foot switch', (XK + 0.024 - 0.0064, SOLE_C[1] - 0.0029, FOOT['sole'] - 0.0015),
        (XK + 0.024 + 0.0064, SOLE_C[1] + 0.0029, FOOT['sole'] + 0.005), DARK, material='electronics', mass=0.001, exposed=True),
    *[fast(cyl(f'L shoe bottom screw {k}', (XK + dx, SOLE_C[1], 0.0078), 'z', 0.0027, 0.0015, DARK, 'decal'), 'M3', 0.012,
           (XK + dx, SOLE_C[1], 0.008), (0, 0, 1)) for k, dx in enumerate((-0.019, 0.036))],
    # the sole curls up all round underneath, toe and heel most (microduck's, round 11): sections from a smaller
    # rounder footprint on the floor out to the full one 5 mm up; it stands on the flat middle ('contact')
    dict(loft('L sole', [(0.0, SOLE_C[0], SOLE_C[1], SOLE_A - 0.009, SOLE_B - 0.005, 2.6),
                         (0.0015, SOLE_C[0], SOLE_C[1], SOLE_A - 0.004, SOLE_B - 0.0022, 3.2),
                         (0.0040, SOLE_C[0], SOLE_C[1], SOLE_A - 0.0008, SOLE_B - 0.0004, 4.0),
                         (0.0065, SOLE_C[0], SOLE_C[1], SOLE_A, SOLE_B, 4.5),
                         (FOOT['sole'], SOLE_C[0], SOLE_C[1], SOLE_A, SOLE_B, 4.5)], YELLOW, 'struct', open=()),
         exposed=True, contact=dict(c=[SOLE_C[0], SOLE_C[1], 0.002], size=[2 * SOLE_A - 0.020, 2 * SOLE_B - 0.010, 0.004])),
])

# ranges in microduck's stance (the zero pose): the hip folds forward 1.3 and back 0.43, the knee 1.1 each way
# the driven horn and a bearing, as microduck's (BEARINGS); no rear horns, forks or posts
joint('L_hip_yaw', 'trunk', 'L_hip_yaw_link', (0, YY, ZY), 'z', (-0.45, 0.45), 'STS3215_C046', out=-1, long='-x',
      fork=False, bearing=('horn',))
joint('L_hip_roll', 'L_hip_yaw_link', 'L_hip_roll_link', (XRH, YR, ZR), 'x', (-0.33, 0.33), 'STS3215_C044', out=+1,
      long='-z', fork=False, bearing=('horn',), sides=(1,))   # no inner cradle wall (the two roll cradles face each other)
joint('L_hip_pitch', 'L_hip_roll_link', 'L_hip_pitch_link', (0, YP, ZP), 'y', (-1.3, 0.43), 'STS3215_C044', out=-1,
      long='-x', case_in='child', fork=False, bearing=('horn',))
joint('L_knee', 'L_hip_pitch_link', 'L_knee_link', (XK, YK, ZK), 'y', (-1.1, 1.05), 'STS3215_C044', out=-1,
      long='+z', fork=False, bearing=('horn',))
# the bearing on the far side, in the shoe's inner ear (spelled out in the links); no side walls: they dip into the shoe
joint('L_ankle_pitch', 'L_knee_link', 'L_foot', (XK, YA, ZA), 'y', (-1.4, 1.4), 'XC330_M288', out=+1, long='+z',
      fork=False, sides=())

# ---------------------------------------------------------------- neck and head (bare servos, as microduck's)

# microduck's head (round 5, 2026-11-02; the user: "check the inner groove vs ours flat... match the sharp straight
# front with rounded-to-back curves... did you even add a grid?"). Measured on microduck's top_head_shell, face_part,
# noenoeil and jaw meshes in 5 mm steps (tools/compare.py --head prints the grid; the meshes stay outside the repo),
# then scaled by HK, milli's height over microduck's. The hood is a loft of front-view arches stacked from back to
# front (a superellipse of power 3 standing on the hood's lower edge): its top rises gently to a sharp, straight,
# upright front; the hood is widest at the front and narrows and rounds down toward the back. The face is a grey
# arch set 20 mm into the hood's open front, the same arch shrunk by the rim; one big amber eye ring in its middle.
HK = 1.18                                          # the head at the scale the STS3215 body sets (milli / microduck)
# (distance back from the front, height above the hood's lower edge, half width) on microduck, metres
# (the heights from the front back to 92 mm smoothed to the straight slope they scatter about: raw, they left a dip)
HOOD_MD = [(0.1227, 0.0141, 0.0229), (0.1173, 0.0241, 0.0280), (0.1123, 0.0295, 0.0331), (0.1023, 0.0357, 0.0364),
           (0.0923, 0.0381, 0.0388), (0.0623, 0.0408, 0.0407), (0.0323, 0.0435, 0.0440), (0.0123, 0.0453, 0.0459),
           (0.0, 0.0464, 0.0458)]
HEAD_FRONT = HEAD_CX + 0.085
HEAD_BACK = HEAD_FRONT - HK * HOOD_MD[0][0]
RIM = 0.0025                                       # the hood's rim round the face


def hood(grow=0.0, n_front=3.0, n_back=2.4):
    """The hood's sections along x, back to front: (x, lower edge, 0, height, half width, power)."""
    z0 = HEAD_Z + BILL_H                           # the hood stands on the upper bill (round 5: it overlapped it)
    out = [(HEAD_BACK - 0.004, z0, 0, 0.006 + grow, 0.014 + grow, n_back)]
    for k, (d, h, w) in enumerate(HOOD_MD):
        n = n_back + (n_front - n_back) * k / (len(HOOD_MD) - 1)
        out.append((HEAD_FRONT - HK * d, z0, 0, HK * h + grow, HK * w + grow, n))
    out.append((HEAD_FRONT + 0.012,) + out[-1][1:])   # past the front: the leaning front plane cuts it
    return out


def arch_front(x0, x1, shrink, z_low=None):
    """The front arch (the hood's front section shrunk by `shrink`) as a slab from x0 to x1."""
    _, cz, _, a, b, n = hood()[-1]
    return [(x0, cz, 0, a - shrink, b - shrink, n), (x1, cz, 0, a - shrink, b - shrink, n)]


BILL_H = 0.005                                     # the upper bill: an orange band round the hood's lower edge
UNDER = box('head underside', (HEAD_BACK - 0.01, -0.08, HEAD_Z - 0.09), (HEAD_FRONT + 0.03, 0.08, HEAD_Z), WHITE,
            'shell')
ABOVE_BILL = box('above the bill', (HEAD_BACK - 0.01, -0.08, HEAD_Z + BILL_H), (HEAD_FRONT + 0.03, 0.08,
                                                                                   HEAD_Z + 0.09), WHITE, 'shell')
FACE_X = HEAD_FRONT - HK * 0.011                   # the face's plane (microduck's face_part: 11 mm in at its edges)
# the hood's front leans forward 6 deg toward the top, over the face (microduck's, on the grid)
FRONT_LEAN = 0.105
FRONT = ((HEAD_FRONT, 0, HEAD_Z), (-1.0, 0, FRONT_LEAN))
EYE = dict(y=0.0, z=HEAD_Z + HK * 0.020, r=HK * 0.015)
HEAD_PLATE_Z = HEAD_Z + 0.029                      # the head's top plate, on the beak servo, under the hood's back

YAW_R = math.hypot(XLL / 2 + XLX, XLW / 2) + GAP   # what turns under the head with its yaw: the yaw case's reach
link('neck_link', 0.02, [
    box('neck front plate', (XN + XLW / 2 - 0.0005, -0.010, ZN + 0.008), (XN + XLW / 2 + 0.0025, 0.010, ZH - 0.008),
        exposed=True),
    box('neck back plate', (XN - XLW / 2 - 0.0025, -0.010, ZN + 0.008), (XN - XLW / 2 + 0.0005, 0.010, ZH - 0.008),
        exposed=True),
])
link('head_pitch_link', 0.03, [
    box('head pitch plate', (XN - 0.010, -0.019, ZH - 0.011), (XN + 0.010, -0.0155, YAW_FOOT), exposed=True),
    box('head pitch idler plate', (XN - 0.010, 0.0165, ZH - 0.011), (XN + 0.010, 0.020, YAW_FOOT), exposed=True),
    box('head pitch bridge', (XN - XLL / 2, -0.019, YAW_FOOT - 0.003), (XN + XLL / 2, 0.020, YAW_FOOT),
        exposed=True),
])
link('head_yaw_link', 0.02, [
    box('head yaw plate', (XHY - XLH / 2, -0.009, ZHY - 0.0005), (XHY + XLH / 2, 0.0255, ZHY + XLHH), exposed=True),
])
# the beak servo: inside the head over the neck, its horn on the jaw's hinge at mid-head, as microduck's side tab
# the beak servo lies flat behind the head yaw and roll servos, its top under the top plate (round 9: the head at
# milli's smaller scale is too low at the back for it standing)
XBK, ZBK = XN - 0.039, HEAD_Z + 0.019              # over the head yaw case; behind the head roll's rear bearing
def interp(x, xs, ys):
    """Linear interpolation, ends held."""
    if x <= xs[0]:
        return ys[0]
    for k in range(1, len(xs)):
        if x <= xs[k]:
            return ys[k - 1] + (ys[k] - ys[k - 1]) * (x - xs[k - 1]) / (xs[k] - xs[k - 1])
    return ys[-1]


JAW_Z = (HEAD_Z - 0.0115, HEAD_Z - 0.0010)       # with the upper bill, microduck's 16.5 mm band
# the jaw's hinge (round 6): on the side tabs at mid-head, over the neck, as microduck's; the beak servo behind the
# head yaw servo turns it through a rod (microduck's jaw is driven through a linkage too)
XJ, ZJ = XHY, ZBK
JAW_X0 = XJ - 0.002                                # the jaw's sides start at the hinge: behind it they rise into the bill


def band_secs(x0, x1):
    """The hood's outline (grown 0.6 mm, as the upper bill) as a 12.5 mm band under the hood, from x0 to x1."""
    out = [(x, sum(JAW_Z) / 2, 0, (JAW_Z[1] - JAW_Z[0]) / 2, b + 0.0006, 8.0) for x, _, _, a, b, n in hood()]
    xs = [o[0] for o in out]
    bx = lambda x: interp(x, xs, [o[4] for o in out])
    mid = [o for o in out if x0 < o[0] < x1]
    return [(x0, out[0][1], 0, out[0][3], bx(x0), 8.0)] + mid + [(x1, out[0][1], 0, out[0][3], bx(x1), 8.0)]


def hood_b(x):
    h = hood()
    return interp(x, [o[0] for o in h], [o[4] for o in h])


TAB_Y_ = max(hood_b(XJ - 0.014), hood_b(XJ + 0.014)) + 0.0006 + GAP      # the hinge tab, just outside the hood
link('head', 0.12, [
    # the head's frame: a plate in front of the head roll servo, a plate on the beak servo behind it, two rails
    # past it either side (outside the roll servo's 27 mm reach as the head rolls)
    box('head frame', (XHR - 0.0005, -0.034, ZHY + 0.004), (XHR + 0.003, 0.034, HEAD_PLATE_Z + 0.003)),
    # narrow at the hood's low back, wide beside the roll servo, where the rails pass it (round 9)
    box('head top plate', (XBK - 0.008, -0.020, HEAD_PLATE_Z), (XHR - XLH - XLS - 0.0065, 0.020, HEAD_PLATE_Z + 0.003)),
    # (the rails stop short of the beak servo, which goes in from the side between them)
    box('head top plate wide', (XHR - XLH - XLS - 0.0085, -0.034, HEAD_PLATE_Z), (XHR - XLH - XLS - 0.0065, 0.034,
                                                                                   HEAD_PLATE_Z + 0.003)),
    box('L head rail', (XHR - XLH - XLS - 0.0085, 0.031, HEAD_Z + 0.006), (XHR + 0.003, 0.034, HEAD_PLATE_Z + 0.003)),
    box('R head rail', (XHR - XLH - XLS - 0.0085, -0.034, HEAD_Z + 0.006), (XHR + 0.003, -0.031, HEAD_PLATE_Z + 0.003)),
    # the jaw's hinge screws go through the hood's wall (a spacer each, for the tab to turn on) into these bosses, and
    # are what holds the hood on
    *[g for sy in (1, -1) for g in (
        box(f"{'L' if sy > 0 else 'R'} head hinge boss", (XJ - 0.005, min(sy * 0.033, sy * (hood_b(XJ) - 0.0015)), ZJ - 0.003),
            (XJ + 0.005, max(sy * 0.033, sy * (hood_b(XJ) - 0.0015)), ZJ + 0.007)),
        fast(cyl(f"{'L' if sy > 0 else 'R'} hinge screw", (XJ, sy * (TAB_Y_ + hood_b(XJ) + 0.0015) / 2, ZJ + 0.002), 'y', 0.0015, TAB_Y_ + 0.0035 - hood_b(XJ) + 0.0035, DARK, 'decal'),
             'M3', 0.014, (XJ, sy * (TAB_Y_ + 0.003), ZJ + 0.002), (0, -sy, 0), pivot=True))],
    box('camera mount', (XHR + 0.0025, -0.006, EYE['z'] - 0.005), (FACE_X - 0.0105, 0.006, EYE['z'] + 0.005)),
    box('Pi Zero 2 W', (FACE_X - 0.024, -0.0325, HEAD_Z + 0.006), (FACE_X - 0.018, 0.0325, HEAD_Z + 0.036), PCB,
        material='electronics', mass=0.011),
    box('camera', (FACE_X - 0.011, EYE['y'] - 0.012, EYE['z'] - 0.012), (FACE_X - 0.0005, EYE['y'] + 0.012,
                                                                         EYE['z'] + 0.012),
        PCB, material='electronics', mass=0.004),
    loft('head', hood(), WHITE, open=(), along='x', clip=FRONT),
    cut(UNDER, 'head', 'upper bill'),
    cut(loft('face recess', arch_front(FACE_X, HEAD_FRONT + 0.01, RIM), WHITE, open=(), along='x'), 'head'),
    loft('upper bill', hood(grow=0.0006), ORANGE, open=(), along='x', clip=FRONT),
    cut(ABOVE_BILL, 'upper bill'),
    loft('face', arch_front(FACE_X - 0.0015, FACE_X + 0.0005, RIM - 0.0005), GREY, 'decal', open=(), along='x',
         clip=((0, 0, HEAD_Z + BILL_H), (0, 0, 1))),
    dict(loft('lower shell', band_secs(HEAD_BACK - 0.004, JAW_X0 - 0.011), ORANGE, 'struct', open=(), along='x'),
         exposed=True),
    cut(box('lower shell opening', (HEAD_BACK + 0.010, -0.033, JAW_Z[0] - 0.01), (JAW_X0 - 0.010, 0.033, JAW_Z[1] + 0.01),
            WHITE, 'shell'), 'lower shell'),
    # (beside the beak servo, on its cradle's rear plate: 2026-11-02, they ran through its case)
    box('lower shell post', (HEAD_BACK + 0.006, -0.019, JAW_Z[1] - 0.0005), (HEAD_BACK + 0.016, -0.0124, HEAD_Z + 0.010),
        exposed=True),
    box('lower shell beam', (HEAD_BACK + 0.006, -0.019, HEAD_Z + 0.008), (XBK + XLX + 0.014, -0.012, HEAD_Z + 0.011)),
    cyl('eye ring', (FACE_X + HK * 0.005, EYE['y'], EYE['z']), 'x', EYE['r'], HK * 0.0095, AMBER, 'decal'),
    cyl('eye lens', (FACE_X + HK * 0.0075, EYE['y'], EYE['z']), 'x', HK * 0.0086, HK * 0.008, LENS, 'decal'),
    box('sensor', (FACE_X, 0.030, EYE['z'] - 0.003), (FACE_X + 0.002, 0.042, EYE['z'] + 0.004), LENS, 'decal',
        fillet=0.0009),
])
# the lower band (round 5, the 10 mm grid): microduck's band runs flush all round under the upper bill:
# the jaw at the front (it opens), a fixed lower shell behind it; an orange tab on each side of the head carries the
# jaw's hinge
TAB_X = (XJ - 0.014, XJ + 0.014)
TAB_Y = max(hood_b(TAB_X[0]), hood_b(TAB_X[1])) + 0.0006 + GAP      # the hinge tab, just outside the hood
link('beak_link', 0.03, [
    dict(loft('jaw', band_secs(JAW_X0, HEAD_FRONT - 0.0005), ORANGE, 'struct', open=(), along='x'), exposed=True),
    cut(box('jaw opening', (JAW_X0 - 0.01, -0.041, JAW_Z[0] - 0.01), (HEAD_FRONT - 0.019, 0.041, JAW_Z[1] + 0.01),
            WHITE, 'shell'), 'jaw'),
    *[g for sy in (1, -1) for g in (
        # microduck's hinge tab: a rounded triangle standing on the band, its hub at the top on the hinge
        plate(f"{'L' if sy > 0 else 'R'} hinge tab", TAB_Y if sy > 0 else -TAB_Y - 0.003, 0.003,
              [(XJ, ZJ + 0.002, 0.011), (TAB_X[0] - 0.004, JAW_Z[0] + 0.004, 0.004),
               (TAB_X[1] + 0.004, JAW_Z[0] + 0.004, 0.004)], ORANGE, 'struct', exposed=True),
        box(f"{'L' if sy > 0 else 'R'} tab foot", (JAW_X0, min(sy * (TAB_Y + 0.0005), sy * (hood_b(TAB_X[0]) - 0.002)),
                                                    JAW_Z[0]),
            (TAB_X[1], max(sy * (TAB_Y + 0.0005), sy * (hood_b(TAB_X[0]) - 0.002)), JAW_Z[1]), ORANGE, exposed=True),
        cyl(f"{'L' if sy > 0 else 'R'} tab hub", (XJ, sy * (TAB_Y + 0.0035), ZBK + 0.002), 'y', 0.0045, 0.002, DARK,
            'decal'),
        *[cyl(f"{'L' if sy > 0 else 'R'} tab screw {k}",
              (XJ + 0.0075 * math.cos(math.pi / 4 + k * math.pi / 2), sy * (TAB_Y + 0.0035),
               ZBK + 0.002 + 0.0075 * math.sin(math.pi / 4 + k * math.pi / 2)), 'y', 0.0011, 0.002, DARK, 'decal')
          for k in range(4)])],
])
joint('neck_pitch', 'trunk', 'neck_link', (XN, 0.013, ZN), 'y', (-0.15, 1.6), 'XC330_M288', out=+1, long='+z',
      case_in='child')
joint('head_pitch', 'neck_link', 'head_pitch_link', (XN, -0.016, ZH), 'y', (-1.6, 1.6), 'XL330_M288', out=-1,
      long='-z', post=False)                       # the head pitch bridge joins the fork's plates
joint('head_yaw', 'head_pitch_link', 'head_yaw_link', (XHY, 0, ZHY), 'z', (-2.5, 2.5), 'XL330_M288', out=+1,
      long='-x', fork=False, bearing=('horn',), face_t=0.001)   # a 1 mm sheet to the far holes, as microduck's: the
#                                                    beak servo turns over it
joint('head_roll', 'head_yaw_link', 'head', (XHR, 0, ZHR), 'x', (-0.44, 0.44), 'XL330_M288', out=+1, long='+y',
      bearing=('horn', 'rear'))                    # a bearing each side, as microduck's
joint('beak', 'head', 'beak_link', (XJ, 0.0, ZJ), 'y', (0.0, 0.4), 'XL330_M288', out=+1, long='+x',
      remote_at=(XBK, 0.019, ZBK), sides=(1,))     # no lower cradle wall: the head yaw case is 1 mm under it


# ---------------------------------------------------------------- mirror, servos

def mirror_geom(g):
    g = copy.deepcopy(g)
    g['name'] = g['name'].replace('L ', 'R ', 1) if g['name'].startswith('L ') else g['name']
    if 'targets' in g:
        g['targets'] = [t.replace('L ', 'R ', 1) if t.startswith('L ') else t for t in g['targets']]
    if 'contact' in g:
        g['contact']['c'][1] = -g['contact']['c'][1]
    if 'fast' in g:
        g['fast']['p'][1], g['fast']['d'][1] = -g['fast']['p'][1], -g['fast']['d'][1]
    if 'on_joint' in g:
        g['on_joint'] = mirror_name(g['on_joint'])
    for k in ('c', 'p0', 'p1'):
        if k in g:
            g[k][1] = -g[k][1]
    if g['kind'] == 'plate' and g.get('axis', 'y') == 'y':
        g['y0'] = -(g['y0'] + g['t'])
    elif g['kind'] == 'plate':                       # the outline's y: its first dim about x, its second about z
        k = 0 if g['axis'] == 'x' else 1
        for q in g['pts']:
            q[k] = -q[k]
    if g['kind'] == 'cyl' and not isinstance(g['axis'], str):
        g['axis'][1] = -g['axis'][1]
    if g['kind'] == 'loft':
        for s in g['sections']:
            s['cy'] = -s['cy']
    return g


def mirror_name(n):
    return 'R_' + n[2:] if n.startswith('L_') else n


def build():
    links, joints = {}, []
    for n, l in LINKS.items():
        links[n] = copy.deepcopy(l)
        if n.startswith('L_'):
            m = copy.deepcopy(l)
            m['name'] = mirror_name(n)
            m['geoms'] = [mirror_geom(g) for g in l['geoms']]
            links[m['name']] = m
    for j in JOINTS:
        joints.append(copy.deepcopy(j))
        if j['name'].startswith('L_'):
            m = copy.deepcopy(j)
            m['name'], m['parent'], m['child'] = mirror_name(j['name']), mirror_name(j['parent']), mirror_name(j['child'])
            m['origin'][1] = -m['origin'][1]
            m['act_c'][1] = -m['act_c'][1]
            if m['axis'] in ('x', 'z'):                    # roll and yaw limits flip with the mirror
                m['lower'], m['upper'] = -j['upper'], -j['lower']
            if j['axis'] == 'y':                          # a horn facing +y on the left faces -y on the right
                m['out'] = -j['out']
            if j['long'][1] == 'y':
                m['long'] = ('-' if j['long'][0] == '+' else '+') + 'y'
            if 'y' not in (j['axis'], j['long'][1]):      # the servo frame's w is y: mirrored
                if j.get('fork_at') is not None:
                    m['fork_at'] = -j['fork_at']
                m['sides'] = [-v for v in j['sides']]
            joints.append(m)
    for j in joints:                                     # servo cases into the parent, horns onto the child
        case, horn = servo_geoms(j, BLACK if j['exposed'] else DARK)
        case_link, horn_link = (j['child'], j['parent']) if j.get('case_in') == 'child' else (j['parent'], j['child'])
        links[case_link]['geoms'].append(case)
        if not j['remote']:
            links[horn_link]['geoms'].append(horn)
        cradle, fork = mount_geoms(j)
        links[case_link]['geoms'] += cradle
        links[horn_link]['geoms'] += fork
    for l in links.values():
        for g in l['geoms']:
            if g['role'] != 'cut':
                g['material'] = material_of(g)
    return dict(frame='metres; X forward, Y left, Z up; floor z=0; zero pose standing, legs straight, head level',
                actuators=ACT, bearings=BEARINGS, materials=MATERIALS, links=links, joints=joints, root='trunk')


if __name__ == '__main__':
    robot = build()
    out = os.path.join(HERE, 'robot.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(robot, f, indent=1)
    print(f"{len(robot['links'])} links, {len(robot['joints'])} joints -> {out} (masses: python -I tools/mass_model.py)")
