"""How milli goes together: every part and screw, in the order a person can do it, and the checks on that order.
(CDX-3R's lessons: "every check looked only at the finished assembly"; a collar that could not go on, screw heads sealed
inside a grip.) Nothing here is drawn: the parts are spec/robot.py's geoms, grouped into what you print or buy.

  python -I tools/assembly.py              the checks; report in reports/assembly.md, exit 1 on any FAIL
  python -I tools/assembly.py --bad CASE   break the order on purpose and show the check FAIL (seal thread order path hold apart window)

The checks, at the zero pose:
  ALL     every rigid part and every screw is fitted exactly once
  HOLD    every printed part is really held: by screws not all on one axis (it would turn about them), or named as glued or as a pivot
  APART   no two parts of the robot share space: not even two parts of one link, except what is meant to seat or thread
  PATH    each part slides in along its path without cutting into parts already on
  THREAD  a screw's tip half bites 2 mm into something it is not clamping: a servo, a horn or a printed part
  HELD    under its head, the screw clamps a printed part
  ACCESS  a key reaches the head: 15 mm straight out from it clear of everything already on (CDX-3R's KEY_REACH)
"""
import argparse
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks as C  # noqa: E402
import geom as G  # noqa: E402

# Printed parts that are glued or that turn on their screws, on purpose
GLUED = {'jaw soft insert', 'mouth roof', 'face', 'eye ring', 'eye iris'}
PIVOTS = {'jaw', 'beak rod'}
KEY_REACH, KEY_R = 0.015, 0.0012                   # a hex key's short arm, and its radius
MIN_BITE = 0.002
TRAVEL = 0.020                                     # how far a part is checked along its path

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
NEG = lambda v: tuple(-a for a in v)


class Past(tuple):
    """A way of travel with parts held out of the path for this step: Past(Z, ['jaw']), the jaw hanging on its rod."""

    def __new__(cls, way, aside):
        o = super().__new__(cls, way)
        o.aside = aside
        return o


def tray(n, sides='+-', rear=True):
    return ([f'{n} cradle rear face'] if rear else []) + [f'{n} cradle end +', f'{n} cradle end -'] + \
        [f'{n} cradle side {s}' for s in sides]


def lid(n, seat='seat floor'):
    return [f'{n} cradle horn face', f'{n} horn {seat}']


def races(n, side='horn'):
    return [f'{n} {side} bearing outer race', f'{n} {side} bearing inner race']


# (name, kind, geoms): printed (P), bought (B). Written for the left leg; the right is its mirror.
def leg_parts(s):
    y, r, p, k, a = (f'{s} hip yaw', f'{s} hip roll', f'{s} hip pitch', f'{s} knee', f'{s} ankle pitch')
    return [
        (f'{s} hip yaw servo', 'B', [f'{s}_hip_yaw actuator (buy) STS3215_C046', f'{y} cable plugs']),
        (f'{s} hip yaw lid', 'P', lid(y)),
        (f'{s} hip yaw bearing', 'B', races(y)),
        (f'{s} hip yaw horn', 'B', [f'{s}_hip_yaw flange']),
        (f'{s} yaw bracket', 'P', [f'{s} hip yaw plate', f'{y} horn boss shoulder'] + tray(r, '+' if s == 'L' else '-')),
        (f'{s} hip roll servo', 'B', [f'{s}_hip_roll actuator (buy) STS3215_C044', f'{r} cable plugs']),
        (f'{s} hip roll lid', 'P', lid(r)),
        (f'{s} hip roll bearing', 'B', races(r)),
        (f'{s} hip roll horn', 'B', [f'{s}_hip_roll flange']),
        (f'{s} roll bracket', 'P', [f'{s} hip roll front', f'{s} hip roll side', f'{s} hip roll arm', f'{r} horn boss shoulder',
                                    f'{p} horn boss shoulder']),
        (f'{s} thigh frame', 'P', [f'{s} thigh plate', f'{s} thigh post hip', f'{s} thigh post knee'] + tray(p) + tray(k)),
        (f'{s} hip pitch servo', 'B', [f'{s}_hip_pitch actuator (buy) STS3215_C044', f'{p} cable plugs']),
        (f'{s} knee servo', 'B', [f'{s}_knee actuator (buy) STS3215_C044', f'{k} cable plugs']),
        (f'{s} hip pitch lid', 'P', lid(p)),
        (f'{s} knee lid', 'P', lid(k)),
        (f'{s} hip pitch bearing', 'B', races(p)),
        (f'{s} knee bearing', 'B', races(k)),
        (f'{s} hip pitch horn', 'B', [f'{s}_hip_pitch flange']),
        (f'{s} knee horn', 'B', [f'{s}_knee flange']),
        (f'{s} thigh cover', 'P', [f'{s} thigh cover']),
        (f'{s} shin', 'P', [f'{s} shin plate', f'{s} shin rib', f'{s} shin gusset', f'{s} shin collar 0', f'{s} shin collar 1', f'{s} shin cap', f'{s} ankle stub plate', f'{s} ankle rail 0', f'{s} ankle rail 1', f'{s} ankle stub',
                            f'{k} horn boss shoulder', f'{a} cradle rear face', f'{a} cradle end +', f'{a} cradle end -']),
        (f'{s} ankle servo', 'B', [f'{s}_ankle_pitch actuator (buy) STS3215_C044', f'{s} ankle rear boss', f'{a} cable plugs']),
        (f'{s} ankle lid', 'P', [f'{a} cradle horn face']),
        (f'{s} ankle horn', 'B', [f'{s}_ankle_pitch flange']),
        (f'{s} ankle bearing inner', 'B', [f'{s} ankle bearing inner race']),
        (f'{s} shoe', 'P', [f'{s} shoe', f'{s} ankle ear out']),
        (f'{s} sole', 'P', [f'{s} sole']),
        (f'{s} foot switch', 'B', [f'{s} foot switch']),
        (f'{s} inner ear', 'P', [f'{s} ankle ear in', f'{s} ankle ear hub', f'{s} ankle bearing outer race']),
    ]


PARTS = leg_parts('L') + leg_parts('R') + [
    ('chassis', 'P', ['top plate', 'neck wall', 'neck wall tab', 'neck mount', 'neck bracket', 'neck idler bracket', 'battery strap',
                      'neck pitch fork horn plate', 'neck pitch fork rear plate', 'neck pitch fork post', 'body post 0', 'body post 1', 'L regulator arm 0', 'L regulator arm 1', 'R regulator arm 0', 'R regulator arm 1', 'L regulator drop 0', 'L regulator drop 1', 'R regulator drop 0', 'R regulator drop 1']
     + tray('L hip yaw') + tray('R hip yaw')),
    ('battery', 'B', ['battery 2S 850 mAh']),
    ('L 5 V regulator', 'B', ['L 5 V regulator']),
    ('R 5 V regulator', 'B', ['R 5 V regulator']),
    ('IMU', 'B', ['IMU']),
    ('body shell', 'P', ['body']),
    ('neck servo', 'B', ['neck_pitch actuator (buy) XC330_M288', 'neck_pitch flange', 'neck pitch rear horn']),
    ('neck column', 'P', ['neck front plate', 'neck back plate', 'neck pitch cradle rear face', 'neck pitch cradle end +',
                          'neck pitch cradle end -', 'neck pitch cradle side +', 'neck pitch cradle side -',
                          'head pitch cradle rear face', 'head pitch cradle end +', 'head pitch cradle end -',
                          'head pitch cradle side +', 'head pitch cradle side -']),
    ('neck lid', 'P', ['neck pitch cradle horn face']),
    ('head pitch servo', 'B', ['head_pitch actuator (buy) XL330_M288', 'head_pitch flange', 'head pitch rear horn']),
    ('head pitch lid', 'P', ['head pitch cradle horn face']),
    ('head fork', 'P', ['head pitch plate', 'head pitch idler plate', 'head pitch bridge', 'head pitch fork horn plate',
                        'head pitch fork rear plate'] + tray('head yaw')),
    ('head yaw servo', 'B', ['head_yaw actuator (buy) XL330_M288']),
    ('head yaw sheet', 'P', lid('head yaw', 'seat wall')),
    ('head yaw bearing', 'B', races('head yaw')),
    ('head yaw horn', 'B', ['head_yaw flange']),
    ('head yaw bracket', 'P', ['head yaw plate', 'head yaw horn boss shoulder', 'head roll cradle end +', 'head roll cradle end -',
                               'head roll cradle side +', 'head roll cradle side -', 'head roll cradle rear face',
                               'head roll rear seat floor']),
    ('head roll servo', 'B', ['head_roll actuator (buy) XL330_M288']),
    ('head roll rear bearing', 'B', races('head roll', 'rear')),
    ('head roll rear horn', 'B', ['head roll rear horn']),
    ('head roll lid', 'P', lid('head roll')),
    ('head roll bearing', 'B', races('head roll')),
    ('head roll horn', 'B', ['head_roll flange']),
    ('head frame', 'P', ['head frame', 'head top plate', 'head top plate wide', 'L head rail', 'R head rail',
                         'L head hinge boss', 'R head hinge boss', 'Pi mount', 'Pi plate', 'Pi boss 0', 'Pi boss 1', 'Pi boss 2', 'Pi boss 3', 'bus board rail 0', 'bus board rail 1', 'bus board post 0', 'bus board post 1', 'lower shell', 'lower shell post', 'lower shell beam',
                         'head roll horn boss shoulder', 'head roll rear boss shoulder', 'head roll fork horn plate',
                         'head roll fork rear plate', 'head roll fork post', 'beak cradle rear face', 'beak cradle end +',
                         'beak cradle end -', 'beak cradle side +']),
    ('beak servo', 'B', ['beak actuator (buy) XL330_M288', 'beak flange']),
    ('beak lid', 'P', ['beak cradle horn face']),
    ('beak crank', 'P', ['beak crank', 'beak crank pin']),
    ('beak rod', 'P', ['beak rod']),
    ('Pi Zero 2 W', 'B', ['Pi Zero 2 W']),
    ('camera', 'B', ['camera']),
    ('servo bus board', 'B', ['servo bus board']),
    ('U2D2', 'B', ['U2D2']),
    ('hood', 'P', ['head', 'upper bill', 'hood rear tab 0', 'hood rear tab 1']),
    ('jaw', 'P', ['jaw', 'L hinge tab', 'R hinge tab', 'L tab foot', 'R tab foot', 'jaw lever', 'L tab hub', 'R tab hub']),
    ('jaw soft insert', 'P', ['jaw soft']),
    ('mouth roof', 'P', ['mouth roof']),
    ('face', 'P', ['face', 'sensor']),
    ('eye ring', 'P', ['eye ring']),
    ('eye iris', 'P', ['eye lens']),
]


def mir(v, s):
    return (v[0], v[1] if s == 'L' else -v[1], v[2])


def sections():
    """The build, in order. on: sections already together when this one starts (the rest of the robot is elsewhere:
    a bench job). Each step: (caption, [(part or @section, the way it travels into place)], [screw name patterns])."""
    out = []
    for s, nm in (('L', 'left'), ('R', 'right')):
        y, r, p, k, a = (f'{s} hip yaw', f'{s} hip roll', f'{s} hip pitch', f'{s} knee', f'{s} ankle pitch')
        OUT, IN = mir(Y, s), mir(NEG(Y), s)
        out += [dict(key=f'thigh_{s}', title=f'The {nm} thigh', on=[], steps=[
            ('The thigh frame', [(f'{s} thigh frame', None)], []),
            ('Plug in the cables, then drop in both servos', [(f'{s} hip pitch servo', OUT), (f'{s} knee servo', OUT)], []),
            ('2 screws each, from the outside', [], [rf'^{p} cradle screw rear', rf'^{k} cradle screw rear']),
            ('The lids', [(f'{s} hip pitch lid', OUT), (f'{s} knee lid', OUT)], []),
            ('4 screws each: 2 far, 2 near the shaft', [], [rf'^{p} cradle screw (horn|near)', rf'^{k} cradle screw (horn|near)']),
            ('Press in the bearings', [(f'{s} hip pitch bearing', OUT), (f'{s} knee bearing', OUT)], []),
            ('Horns on, servos at mid-range', [(f'{s} hip pitch horn', OUT), (f'{s} knee horn', OUT)], []),
            ('The cover, 2 screws', [(f'{s} thigh cover', IN)], [rf'^{s} thigh cover screw']),
        ]), dict(key=f'shin_{s}', title=f'The {nm} shin', on=[], steps=[
            ('The shin', [(f'{s} shin', None)], []),
            ('Plug in the cable, slide in the ankle servo', [(f'{s} ankle servo', IN)], []),
            ('Screws: 4 flat-head into the rear horn, 2 at the far end', [], [rf'^{s} ankle boss screw', rf'^{a} cradle screw rear']),
            ('The lid, 2 screws', [(f'{s} ankle lid', IN)], [rf'^{a} cradle screw horn']),
            ('Press the small bearing onto the stub', [(f'{s} ankle bearing inner', OUT)], []),
            ('Horn on, servo at mid-range', [(f'{s} ankle horn', IN)], []),
        ]), dict(key=f'shoe_{s}', title=f'The {nm} shoe', on=[], steps=[
            ('The shoe', [(f'{s} shoe', None)], []),
            ('Press in the foot switch, its wires soldered first', [(f'{s} foot switch', Z)], []),
            ('The TPU sole, 2 screws from below', [(f'{s} sole', Z)], [rf'^{s} shoe bottom screw']),
        ]), dict(key=f'leg_{s}', title=f'The {nm} leg', on=[f'thigh_{s}'], steps=[
            ('The shin onto the knee horn', [(f'@shin_{s}', OUT)], []),
            ('4 screws from the inside', [], [rf'^{k} fork screw']),
            ('Lift the shoe onto the ankle servo', [(f'@shoe_{s}', Z)], []),
            ('4 screws through the outer ear', [], [rf'^{a} fork screw']),
            ('The inner ear onto the stub, 2 screws', [(f'{s} inner ear', OUT)], [rf'^{s} ankle ear screw']),
            ('The roll bracket onto the hip horn, 4 screws', [(f'{s} roll bracket', OUT)], [rf'^{p} fork screw']),
        ])]
    out += [dict(key='body', title='The chassis and hips', on=[], steps=[
        ('The chassis, upside down', [('chassis', None)], []),
        ('Plug in the cables, push in the hip yaw servos', [('L hip yaw servo', Z), ('R hip yaw servo', Z)], []),
        ('2 screws each, from the top', [], [r'^[LR] hip yaw cradle screw rear']),
        ('The lids, 4 screws each', [('L hip yaw lid', Z), ('R hip yaw lid', Z)], [r'^[LR] hip yaw cradle screw (horn|near)']),
        ('Press in the bearings', [('L hip yaw bearing', Z), ('R hip yaw bearing', Z)], []),
        ('Horns on, servos at mid-range', [('L hip yaw horn', Z), ('R hip yaw horn', Z)], []),
        ('The yaw brackets, 4 screws each, before the roll servos', [('L yaw bracket', Z), ('R yaw bracket', Z)], [r'^[LR] hip yaw fork screw']),
        ('Plug in the cables, slide in the hip roll servos', [('L hip roll servo', NEG(X)), ('R hip roll servo', NEG(X))], []),
        ('2 screws each, from behind', [], [r'^[LR] hip roll cradle screw rear']),
        ('The lids, 4 screws each', [('L hip roll lid', NEG(X)), ('R hip roll lid', NEG(X))], [r'^[LR] hip roll cradle screw (horn|near)']),
        ('Press in the bearings', [('L hip roll bearing', NEG(X)), ('R hip roll bearing', NEG(X))], []),
        ('Horns on, servos at mid-range', [('L hip roll horn', NEG(X)), ('R hip roll horn', NEG(X))], []),
    ]), dict(key='legs', title='Legs onto the hips', on=['body'], steps=[
        ('The left leg onto the roll horn', [('@leg_L', NEG(X))], []),
        ('4 screws from the front', [], [r'^L hip roll fork screw']),
        ('The right leg', [('@leg_R', NEG(X))], []),
        ('4 screws from the front', [], [r'^R hip roll fork screw']),
    ]), dict(key='column', title='The neck column', on=[], steps=[
        ('The neck column', [('neck column', None)], []),
        ('Neck servo in, horns on', [('neck servo', NEG(Y))], [r'^neck pitch cradle screw rear']),
        ('Its lid, 2 screws', [('neck lid', NEG(Y))], [r'^neck pitch cradle screw horn']),
        ('Head pitch servo in, horns on', [('head pitch servo', Y)], [r'^head pitch cradle screw rear']),
        ('Its lid, 2 screws', [('head pitch lid', Y)], [r'^head pitch cradle screw horn']),
    ]), dict(key='torso', title='Neck and body shell', on=['legs'], steps=[
        ('Battery into its slot from behind, onto its tray; a hook-and-loop strap round both', [('battery', X)], []),
        ('A 5 V regulator into each side pocket', [('L 5 V regulator', Z), ('R 5 V regulator', Z)], []),
        ('The IMU on the top plate, double-sided tape', [('IMU', NEG(Z))], []),
        ('The column down into the chassis fork', [('@column', NEG(Z))], []),
        ('4 screws on each horn', [], [r'^neck pitch fork screw']),
        ('The body shell, 2 screws', [('body shell', NEG(Z))], [r'^body screw']),
    ]), dict(key='headbench', title='The head yaw and roll', on=[], steps=[
        ('The head fork', [('head fork', None)], []),
        ('Head yaw servo in, 2 screws from under the bridge', [('head yaw servo', NEG(Z))], [r'^head yaw cradle screw rear']),
        ('The thin sheet, 2 screws', [('head yaw sheet', NEG(Z))], [r'^head yaw cradle screw horn']),
        ('Bearing and horn', [('head yaw bearing', NEG(Z)), ('head yaw horn', NEG(Z))], []),
        ('The yaw bracket, 4 screws, before its roll servo', [('head yaw bracket', NEG(Z))], [r'^head yaw fork screw']),
        ('Head roll servo in from the front', [('head roll servo', NEG(X))], [r'^head roll cradle screw rear']),
        ('The rear bearing and rear horn, from behind', [('head roll rear bearing', X), ('head roll rear horn', X)], []),
        ('The lid, 2 screws', [('head roll lid', NEG(X))], [r'^head roll cradle screw horn']),
        ('Bearing and horn', [('head roll bearing', NEG(X)), ('head roll horn', NEG(X))], []),
    ]), dict(key='jawbench', title='The jaw and its rod', on=[], steps=[
        ('The jaw', [('jaw', None)], []),
        ('Glue in its soft insert', [('jaw soft insert', NEG(Z))], []),
        ('The rod on its lever, 1 screw', [('beak rod', Y)], [r'^beak rod screw jaw']),
    ]), dict(key='head', title='The head', on=['torso'], steps=[
        ('The head fork down onto the head pitch servo', [('@headbench', NEG(Z))], []),
        ('4 screws on each horn', [], [r'^head pitch fork screw']),
        ('The head frame down over the roll servo', [('head frame', NEG(Z))], []),
        ('4 screws on each horn', [], [r'^head roll fork screw']),
        ('Beak servo in from the side, 2 screws', [('beak servo', NEG(Y))], [r'^beak cradle screw rear']),
        ('Its lid, 2 screws', [('beak lid', NEG(Y))], [r'^beak cradle screw horn']),
        ('The beak crank on its horn, servo at mid-range, 4 screws', [('beak crank', NEG(Y))], [r'^beak crank screw']),
        ('The U2D2 on the frame, from below, foam tape', [('U2D2', Z)], []),
        ('The Pi onto its plate from the front, 4 screws', [('Pi Zero 2 W', NEG(X))], [r'^Pi screw']),
        ('The Feetech bus board on its rails, foam tape', [('servo bus board', NEG(Z))], []),
        ('The jaw, its rod already on its lever, in from the front', [('@jawbench', NEG(X))], []),
        ('The rod onto the crank pin', [], [r'^beak rod screw crank']),
        ('The hood, down between the jaw\'s tabs', [('hood', NEG(Z))], []),
        ('Let the jaw hang on its rod and glue in the soft mouth roof through the gap', [('mouth roof', Past(Z, ['jaw', 'jaw soft insert', 'beak rod']))], []),
        ('The camera, its ribbon to the Pi, then glue in the face (the camera taped to its back), the eye ring and its iris', [('camera', NEG(X)), ('face', NEG(X)), ('eye ring', NEG(X)), ('eye iris', NEG(X))], []),
        ('2 screws up through the band into the hood\'s back', [], [r'^hood rear screw']),
        ('A spacer each side, and the hinge screws hold the jaw and the hood', [], [r'^[LR] hinge screw']),
    ])]
    return out


class Build:
    def __init__(self, spec, S=None):
        self.spec, self.S = spec, S or C.Solids(spec)
        self.idx = {g['name']: (ln, i, g) for ln, l in spec['links'].items() for i, g in enumerate(l['geoms'])}
        self.parts = {n: dict(kind=k, geoms=gs) for n, k, gs in PARTS}
        self.owner = {g: n for n, p in self.parts.items() for g in p['geoms']}
        self.screws = {g['name']: (ln, g) for ln, l in spec['links'].items() for g in l['geoms'] if 'fast' in g}
        self.cuts = {}
        for l in spec['links'].values():
            for g in l['geoms']:
                for t in g.get('targets', []) if g['role'] == 'cut' else []:
                    self.cuts.setdefault(t, []).append(g)

    def inside(self, g, pts):
        """Points in a part, its cuts removed. A shell is its wall: a screw inside the body isn't in the body shell. (Taking it as solid drilled a hole through
        the shell and covers over every screw under them, and counted air as thread; only the first Fusion picture showed it.)"""
        hit = G.inside(g, pts)
        for c in self.cuts.get(g['name'], []):
            hit = hit & ~G.inside(c, pts)
        if g['role'] == 'shell':
            hit = hit & ~G.inside(G.inner_of(g, C.WALL), pts)
        return hit

    def solid(self, part):
        ms = []
        for g in self.parts[part]['geoms']:
            ln, i, _ = self.idx[g]
            ms.append(self.S.wall.get((ln, i), self.S.geom[(ln, i)]))
        return C.union(ms)


def tube(p, d, r0, L):
    import trimesh
    T = np.eye(4)
    T[:3, :3] = G._frame_to(np.asarray(d, float))
    T[:3, 3] = np.asarray(p) + np.asarray(d) * (r0 + L / 2)
    m = trimesh.creation.cylinder(radius=KEY_R, height=L, sections=12)
    m.apply_transform(T)
    return C.to_manifold(m)


def check_hold(B, rep):
    """(2026-11-03: the hood hung on 2 hinge screws on one axis, and would have tipped about them. Every check passed it.)"""
    lines = {n: [] for n, p in B.parts.items() if p['kind'] == 'P'}
    for n, (ln, g) in B.screws.items():
        f = g['fast']
        p, d = np.array(f['p']), np.array(f['d'])
        for t in np.linspace(0, f['L'], 25):
            q = (p + d * max(t, 0.0002))[None]
            for part in lines:
                if any(B.idx[x][0] == ln and B.inside(B.idx[x][2], q).any() for x in B.parts[part]['geoms']):
                    if not any(np.allclose(p, a[0]) for a in lines[part]):
                        lines[part].append((p, d))
    for part, ls in lines.items():
        if part in GLUED or part in PIVOTS:
            rep.add('HOLD', part, True, 'glued' if part in GLUED else 'turns on its screws')
            continue
        if len(ls) < 2:
            rep.add('HOLD', part, False, f'{len(ls)} screw: it can turn about it')
            continue
        p0, d0 = ls[0]
        off = [np.linalg.norm(np.cross(a - p0, d0)) for a, _ in ls[1:]]
        rep.add('HOLD', part, max(off) > 0.001, f'{len(ls)} screws' if max(off) > 0.001 else f'{len(ls)} screws, all on one axis: it can turn about them')


# parts that are meant to share space: a horn and the plate on it, a part seated in its neighbour
SEATS = (' flange', ' rear boss', ' rear horn', 'bearing', ' cradle', ' shoulder', ' seat')


def check_apart(B, rep):
    """Bought parts of one link against everything else on it. (2026-11-03: a printed bar ran through the Pi's board, and the static
    check skips parts of one link.)"""
    names = [n for n, p in B.parts.items()]
    for a in names:
        pa = B.parts[a]
        if pa['kind'] != 'B' or any(k in a for k in (' servo', 'horn', 'bearing')) and 'servo' not in a:
            continue
        la = {B.idx[g][0] for g in pa['geoms']}
        sa = B.solid(a)
        for b in names:
            if b == a or not ({B.idx[g][0] for g in B.parts[b]['geoms']} & la):
                continue
            if B.parts[b]['kind'] == 'B' and b <= a and b in names:
                pass
            v = C.overlap(sa, B.solid(b))
            # (a servo's plates are drawn up to 0.5 mm into its case, so one solid joins them: tools/export_prints.py cuts the real pocket, with clearance)
            ok = v <= (0.5e-6 if ' servo' in a else C.SEATED)
            if not ok:
                rep.add('APART', f'{a} / {b}', False, f'{v * 1e6:.2f} cm3 in the same place')
    rep.add('APART', 'bought parts', True)
    # a cable has to plug in: nothing printed where the plugs go (limits above would pass a whole plate over them)
    for n, (ln, i, g) in B.idx.items():
        if not n.endswith('cable plugs'):
            continue
        plug = B.S.geom[(ln, i)]
        hit = [p for p, q in B.parts.items() if q['kind'] == 'P' and C.overlap(plug, B.solid(p)) > C.TOUCH]
        rep.add('APART', n, not hit, f'no way to plug the cable in: {hit} in the way' if hit else '')


def check(spec, secs, rep, S=None):
    B = Build(spec, S)
    placed, used, done = {}, set(), {}
    for sec in secs:
        have = [p for o in sec['on'] for p in done[o]]
        for cap, items, pats in sec['steps']:
            for item, way in items:
                group = done[item[1:]] if item.startswith('@') else [item]
                if not item.startswith('@'):
                    if item not in B.parts:
                        raise SystemExit(f'no part {item}')
                    placed[item] = placed.get(item, 0) + 1
                if way is not None and have:
                    fixed = C.union([B.solid(p) for p in have if p not in getattr(way, 'aside', ())])
                    moving = C.union([B.solid(p) for p in group])
                    base = C.overlap(moving, fixed)
                    worst = 0.0
                    for t in np.arange(0.001, TRAVEL + 1e-9, 0.001):
                        v = C.overlap(moving.translate([-a * t for a in way]), fixed)
                        worst = max(worst, v - base)
                    who = []
                    if worst > C.TOUCH:
                        for o in [p for p in have if p not in getattr(way, 'aside', ())]:
                            so = B.solid(o)
                            b0 = C.overlap(moving, so)
                            if max(C.overlap(moving.translate([-a * t for a in way]), so) - b0
                                   for t in np.arange(0.002, TRAVEL + 1e-9, 0.002)) > C.TOUCH:
                                who.append(o)
                    rep.add('PATH', f"{sec['key']}: {item}", worst <= C.TOUCH,
                            f'cuts {worst * 1e6:.2f} cm3 into {who}, travelling {way}' if worst > C.TOUCH else '')
                have = have + list(group)
            for pat in pats:
                names = [n for n in B.screws if re.search(pat, n)]
                if not names:
                    rep.add('ALL', f'pattern {pat}', False, 'matches no screw')
                for n in names:
                    used.add(n)
                    ln, g = B.screws[n]
                    f = g['fast']
                    p, d = np.array(f['p']), np.array(f['d'])
                    # HELD: a part under the head
                    under = [q for q, (l2, i2, g2) in B.idx.items() if l2 == ln and g2['role'] in ('struct', 'shell')
                             and B.inside(g2, (p + d * 0.0002)[None]).any()]
                    clamp = {B.owner.get(q) for q in under}
                    if not f.get('pivot'):
                        rep.add('HELD', n, bool(under), '' if under else 'nothing under the head to clamp')
                    # THREAD: the tip half in something else
                    ts = np.linspace(f['L'] / 2, f['L'], 21)
                    pts = p + np.outer(ts, d)
                    bite = np.zeros(len(pts), bool)
                    for q, (l2, i2, g2) in B.idx.items():
                        if l2 == ln and g2['role'] in G.RIGID and B.owner.get(q) not in clamp:
                            bite |= B.inside(g2, pts)
                    mm = bite.mean() * f['L'] / 2
                    rep.add('THREAD', n, mm >= MIN_BITE - 1e-4, f"{f['size']} x {f['L'] * 1000:.0f}: bites {mm * 1000:.1f} mm")
                    # ACCESS: a key from the head, past parts on now (its own counterbore is printed to suit)
                    key = tube(p, -d, 0.0016, KEY_REACH - 0.0016)
                    blocked = [o for o in have if o not in clamp and C.overlap(key, B.solid(o)) > 1e-9]
                    rep.add('ACCESS', n, not blocked, f'blocked by {blocked[:3]}' if blocked else '')
        done[sec['key']] = have
    check_hold(B, rep)
    check_apart(B, rep)
    for n, p in B.parts.items():
        c = placed.get(n, 0)
        rep.add('ALL', f'part {n}', c == 1, '' if c == 1 else f'fitted {c} times')
    for ln, l in spec['links'].items():
        for g in l['geoms']:
            if g['role'] in G.RIGID and g['name'] not in B.owner:
                rep.add('ALL', f"geom {g['name']}", False, 'in no part')
    for n in B.screws:
        if n not in used:
            rep.add('ALL', f'screw {n}', False, 'never fitted')
    return B


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bad')
    a = ap.parse_args()
    spec = G.load()
    secs = sections()
    if a.bad == 'seal':                            # the yaw bracket's screws after its roll servo is in
        body = next(s for s in secs if s['key'] == 'body')
        st = body['steps']
        k = next(i for i, x in enumerate(st) if 'yaw brackets' in x[0])
        cap, items, pats = st[k]
        st[k] = (cap, items, [])
        st.append(('late', [], pats))
    elif a.bad == 'thread':                        # a horn screw far too short
        for l in spec['links'].values():
            for g in l['geoms']:
                if g['name'].startswith('L knee fork screw') and 'fast' in g:
                    g['fast']['L'] = 0.003
    elif a.bad == 'order':                         # a part forgotten
        body = next(s for s in secs if s['key'] == 'body')
        body['steps'] = [x for x in body['steps'] if 'push in the hip yaw' not in x[0]]
    elif a.bad == 'path':                          # the lids pushed in from the wrong side, through their servos
        th = next(s for s in secs if s['key'] == 'thigh_L')
        th['steps'] = [(c, [(p, NEG(w)) if 'lid' in p else (p, w) for p, w in it], s_) for c, it, s_ in th['steps']]
    elif a.bad == 'hold':                          # the hood on its hinge screws alone
        for g in spec['links']['head']['geoms']:
            if g['name'].startswith('hood rear screw'):
                g['fast']['L'] = 0.001
    elif a.bad == 'window':                        # the thigh plate over the plugs, as it was
        for ln in spec['links']:
            spec['links'][ln]['geoms'] = [g for g in spec['links'][ln]['geoms'] if not g['name'].endswith('plug window')]
    elif a.bad == 'apart':                         # the bar back through the Pi
        for g in spec['links']['head']['geoms']:
            if g['name'] == 'Pi mount':
                g['size'][0] += 0.02
    rep = C.Report()
    check(spec, secs, rep)
    fails = rep.failing()
    if a.bad:
        print(f"--bad {a.bad}: {'CAUGHT' if fails else 'NOT CAUGHT'} ({len(fails)} failing)")
        for r in fails[:3]:
            print('  ', r['group'], r['item'], r['detail'])
        return 0 if fails else 1
    rep.write(os.path.join(G.ROOT, 'reports', 'assembly.md'), 'From tools/assembly.py')
    for r in fails:
        print(r['group'], r['item'], r['detail'])
    print(f'{len(rep.rows)} assembly checks, {len(fails)} failing')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
