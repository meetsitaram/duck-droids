"""A duck taller than echo, on echo's RobStride actuators: python -I spec/big_duck.py -> spec/robot_big.json. Then MILLI_RECIPE=big for the tools.

The small duck's joints and look at 1.80 m (2026-11-03, the user: "use the powerful servos we used on echo humanoid and build me a duck bigger than echo"; "full design first...
including connection parts, bearings, screws"; "they can be metal parts if needed for the strength"; "you can't give a gigantic 3d printed part that can't fit in a Bambu printer").
Not the small duck scaled up: at this size the load goes through metal, not printed brackets.

Choices, and why:
- Frame: 6061 and 7075 plate, cut flat and bolted, so a waterjet service can make every metal part from one sheet thickness. Printed parts carry no load.
- Skin: 3 mm PETG panels, bolted to the frame, each inside a 256 mm printer bed (tools/checks.py 'printable'). Split where it shows least, along the hood's and body's lines.
- Hip roll and hip pitch: a pair of RS04s on one axis, each side of the part they turn. 240 N m peak, without gearing, and no moment on either output.
- Knee: a pair of RS04s, each with a crank, a rod and a lever on the knee, as Agility's Cassie and Digit drive theirs by pushrod. 1.54:1 at its weakest (mid stroke), 3.35:1 at the straight end,
  over 70 deg, from -0.92 (bent) to +0.30. The crank never passes dead centre, so the knee can't straighten past +0.30 or squat fully: the chain had 143 deg. Rod load about 2 kN mid stroke, 3-4 kN at the ends.
- Head pitch: one RS04 through #40 roller chain, 13T to 25T, 1.92:1: +-1.6 rad is too far for a crank. The chain carries about 3 kN at peak against 14 kN to break it. The cost: backlash.
- No head roll (2026-11-03, the user: forget the flip, lower the upper body's weight): the head pitch went from a pair to one RS04, and the upper frames are lighter. Those masses are pocketing fills, assumed:
  no pockets are drawn and nothing has been stress-checked.
- Hip yaw: one RS04, as it turns the leg but doesn't hold it up: a 61824 thin-section bearing round the stator takes the leg's moment off the actuator's own bearing.
- Knees and head pitch ride on 6908 bearings in the frame; RS04 outputs carry only torque where a far bearing is given.
- Feet: an aluminium plate, printed TPU soles in two pieces. The stance is narrower than the small duck's in proportion, as a foot further out loads the hip roll more.

NOT SAFE TO BUILD. About 100 kg and 1.8 m, with no stress analysis, metal frames nobody has checked and joints that drop when power goes (no brakes): a failure could seriously hurt someone. See docs/big/BOM.md, "Open before ordering".

Not checked here: stress in the plates and shafts (a hand estimate only), chain tension and fatigue, heat, and how it survives a fall. Actuator numbers are the retailer's or maker's: confirm before ordering.
RS04 and RS03 holes (2026-11-05): read off the outline figure in RobStride's user manuals (RS04 260713, RS03 261013), which settles which circle takes which screw: M5 on 36 and three 6 mm pins on 35.86 for the RS04. That's a
picture in a PDF, not a drawing read in CAD, and no actuator has been measured: read RS04-20261030.stp and measure one before cutting metal. The real case isn't the plain cylinder below either: the RS04 is 120 across for 39 mm and 94 across
for its last 13.2, with its cable leaving through the side of that step, and the plates here don't allow for that (docs/big/BOM.md).
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop('MILLI_RECIPE', None)
import robot as T                                  # the small duck's shape primitives, no more
from robot import ALU, AMBER, BLACK, CELL, DARK, GREY, LENS, ORANGE, PCB, WHITE, YELLOW, box, cut, cyl, fast, loft, mirror_geom, mirror_name, plate

# echo's spec/actuators.json, where these come from: retailer numbers. Holes: RobStride's user manuals' outline figures (2026-11-05). RS04: 10 M4 on 106 (5 mm deep on the output side, 6 on the rear), output 9 M5 6.5 deep on 36, with 3 x 6 mm pins on 35.86.
# It was 35.86 for the screws, from the product page, which is the pins' circle. RS03: 8 M4 8 deep on 98, output 6 M4 6 deep on 30.36, with 3 x 4 mm holes: it was 8 on the output, and 90 for the head roll's mount, a guess
ACT = {
    'RS00': dict(r=0.0285, h=0.051, mass=0.31, rated_nm=5.0, peak_nm=14.0, noload_rads=32.0, gear=10.0, rotor_kgm2=1e-05, damping_nms=0.02, friction_nm=0.3),
    'RS03': dict(r=0.053, h=0.056, mass=0.88, rated_nm=20.0, peak_nm=60.0, noload_rads=20.0, gear=9.0, rotor_kgm2=1e-04, damping_nms=0.12, friction_nm=1.0, out_pcd=0.03036, out_n=6, mount_pcd=0.098, mount_n=8),
    'RS04': dict(r=0.06, h=0.056, mass=1.42, rated_nm=40.0, peak_nm=120.0, noload_rads=21.0, gear=9.0, rotor_kgm2=2e-04, damping_nms=0.2, friction_nm=1.5, out_pcd=0.036, out_n=9, mount_pcd=0.106, mount_n=10),
}
CHAIN = 25 / 13                                    # #40 chain, 13T on the RS04, 25T on the joint: the head pitch
# The knee's four-bar, from a sweep of its geometry with the stators where they were. The lever stands at CRANK_PHI at knee angle 0; a +y turn takes it down from there
# The lever 20 deg round from where the hybrid's walk put it: the same four-bar and ratios, its window moved toward bending. With -0.70..+0.65 the big duck's walk sat on the bent end 83-92 % of the
# time and never went straighter than -0.33: it stands more crouched than the hybrid, so it needs the bent side
CRANK_R, CRANK_LEVER, CRANK_ROD, CRANK_PHI = 0.060, 0.096, 0.106, math.radians(130)
KNEE_RATIO, KNEE_RATIO_MAX = 1.54, 3.35            # crank turn per knee turn: mid stroke, and at the straight end
KNEE_RATIO_BENT = 1.89                             # on the bent side, where a swinging knee moves fastest: about 1.7 at -0.92, so a little pessimistic
KNEE_RANGE = (-0.92, 0.30)                         # bent: where the shin cover meets the thigh plate. Straight: about 3.3:1, past which the rod is nearly in line with the crank


def crank_points(s, k):
    """Crank pin and lever pin (x, z) at knee angle 0, for a stator at s and the knee at k: the rod's two ends."""
    b = (k[0] + CRANK_LEVER * math.cos(CRANK_PHI), k[1] + CRANK_LEVER * math.sin(CRANK_PHI))
    dd = math.hypot(b[0] - s[0], b[1] - s[1])
    c = math.atan2(b[1] - s[1], b[0] - s[0]) - math.acos((CRANK_R ** 2 + dd ** 2 - CRANK_ROD ** 2) / (2 * CRANK_R * dd))
    return (s[0] + CRANK_R * math.cos(c), s[1] + CRANK_R * math.sin(c)), b
PCD13, PCD25 = 0.0530, 0.1014                      # 12.7 mm pitch sprockets
BEAR = {'61824': dict(d=0.120, D=0.150, w=0.016, mass=0.45), '6908': dict(d=0.040, D=0.062, w=0.012, mass=0.11), '6206': dict(d=0.030, D=0.062, w=0.016, mass=0.20)}
AL, ALD, PET = '#A8ACB0', '#50555B', WHITE
LINKS, JOINTS = {}, []
MATERIALS = dict(T.MATERIALS)
MATERIALS.update(al7075=dict(density=2810, note='7075-T6: plates under load'), al6061=dict(density=2700, note='6061-T6: plates and tubes'),
                 petg=dict(density=1270, note='PETG: skin panels, printed on a 256 mm bed'), steel=dict(density=7800, note='bought shafts, bearings and chain'),
                 cells=dict(density=2500, note='battery: explicit mass'), electronics=dict(density=1500, note='explicit masses'))


def link(name, geoms, note=''):
    LINKS[name] = dict(name=name, budget=0.0, geoms=list(geoms), note=note)


def metal(name, lo, hi, color=AL, mat='al6061', fill=1.0, **kw):
    return box(name, lo, hi, color, 'struct', fillet=0.002, material=mat, fill=fill, exposed=True, **kw)


def side_plate(name, y0, t, circles, color=AL, mat='al7075'):
    return dict(plate(name, y0, t, circles, color, 'struct'), material=mat, fill=1.0, exposed=True)


def axle(name, c, axis, r, h, color=ALD, mat='steel'):
    return dict(cyl(name, c, axis, r, h, color, 'struct'), material=mat, fill=1.0, exposed=True)


def disc(name, c, axis, r, h, color=AL):
    return dict(cyl(name, c, axis, r, h, color, 'struct'), material='al6061', fill=1.0, exposed=True)


def stator(name, act, c, axis):
    a = ACT[act]
    return dict(cyl(f'{name} (buy) {act}', c, axis, a['r'], a['h'], BLACK, 'actuator'), exposed=True, material='actuator')


def seat(name, c, axis, r=0.055):
    """Where a stator's face is bolted on: a thin ring that overlaps both, as the checks read a bare touch as two pieces."""
    return dict(cyl(f'{name} seat', c, axis, r, 0.001, ALD, 'struct'), material='al6061', fill=1.0, exposed=True, seat=True)


def chain(name, p, q, y, r0, r1):
    """A #40 roller chain's two strands between sprockets at p and q (x, z), at y: bought, drawn at the zero pose."""
    dx, dz = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dz)
    nx, nz = -dz / L, dx / L
    out = []
    for sg, tag in ((1, 'a'), (-1, 'b')):
        a = (p[0] + sg * r0 * nx, y, p[1] + sg * r0 * nz)
        b = (q[0] + sg * r1 * nx, y, q[1] + sg * r1 * nz)
        out.append(dict(T.cap(f'{name} {tag}', a, b, 0.004, DARK, 'decal'), material='steel', mass=0.09))
    return out


def bolts(name, c, axis, pcd, n, size, length, into, head=0.0035, t=0.002):
    """Screw heads on a face at c, pointing `into` (+1/-1 along the axis)."""
    k = 'xyz'.index(axis)
    u, v = [i for i in range(3) if i != k]
    out = []
    for i in range(n):
        p = list(c)
        p[u] += pcd / 2 * math.cos(2 * math.pi * (i + 0.5) / n)
        p[v] += pcd / 2 * math.sin(2 * math.pi * (i + 0.5) / n)
        q = list(p)
        q[k] -= into * t / 2
        d = [0.0, 0.0, 0.0]
        d[k] = float(into)
        out.append(fast(cyl(f'{name} {i}', q, axis, head, t, DARK, 'decal'), size, length, p, d))
    return out


def bearing(name, joint, c, axis, part, inner, outer):
    """Two races: returns the geoms for the link holding the inner race and the one holding the outer."""
    b = BEAR[part]
    race = (b['D'] - b['d']) / 2 * 0.45
    i = dict(cyl(f'{name} bearing inner race', c, axis, b['d'] / 2 + race, b['w'], ALU), exposed=True, material='steel', mass=b['mass'] / 2, on_joint=joint, part=part, seat=True)
    ic = cut(cyl(f'{name} bearing inner bore', c, axis, b['d'] / 2 - 0.00005, b['w'] + 0.002), f'{name} bearing inner race')
    o = dict(cyl(f'{name} bearing outer race', c, axis, b['D'] / 2, b['w'], ALU), exposed=True, material='steel', mass=b['mass'] / 2, on_joint=joint, part=part)
    oc = cut(cyl(f'{name} bearing outer bore', c, axis, b['D'] / 2 - race, b['w'] + 0.002), f'{name} bearing outer race')
    return [i, ic], [o, oc]


def joint(name, parent, child, origin, axis, lim, act, count=1, ratio=1.0, out=+1, act_c=None, remote=False, interface=()):
    JOINTS.append(dict(name=name, parent=parent, child=child, origin=list(origin), axis=axis, lower=lim[0], upper=lim[1], act=act, act_c=list(act_c or origin), out=out, long='-x',
                       exposed=True, remote=remote, case_in='parent', fork_at=None, fork_r=None, post=False, fork=False, sides=[], faces=[], bearing=[], stack=0.01, face_t=None, tray_full=False,
                       capacity=dict(model=act, count=count, ratio=ratio), interface=interface))


# ---------------------------------------------------------------- anchors, metres

H4 = ACT['RS04']['h']
R4 = ACT['RS04']['r']
ZA, ZK, XK = 0.190, 0.530, -0.235                  # ankle, knee: the small duck's stance, the shin upright
STANCE = 1.02
ZP = ZK - XK / math.tan(STANCE)                    # hip pitch and roll: 0.634
ZR = ZP
YY = 0.110                                         # hip yaw and roll axes: the two yaw drums (80 mm) 20 mm apart
ZY = ZR + 0.125                                    # the yaw plate over the roll stators
PL = 0.008                                         # the frame's plate thickness
# along y, from the middle out: the yoke, the inner upright, a stator, the crank lane, the thigh's two plates, a lane, a stator, the outer upright
YI = (0.174, 0.182)                                # inner upright or thigh rear plate
YSI = (0.182, 0.238)                               # inner stators
YCI = 0.244                                        # inner crank lane and hip output plate
YT = (0.250, 0.290)                                # the thigh's width, between its plates' outer faces
YCO = 0.296
YSO = (0.302, 0.358)
YO = (0.358, 0.366)
YC = (YT[0] + YT[1]) / 2                           # 0.270: thigh, shin, ankle and foot on one line
XQ, ZQ = -0.212, ZP - 0.015                        # the knee stators, at the thigh's top back corner, as the small duck's knee servo sits
PIN_A, PIN_B = crank_points((XQ, ZQ), (XK, ZK))
# each 12 mm lane: crank and lever in one plane, as they never come within 56 mm of each other, and the rod beside them, next to the thigh plate
LANE_I, LANE_O = YSI[1] + 0.0002, YSO[0] - 0.0062   # the 6 mm crank and lever plane's inner face, in each lane: a seat bolts the crank to the actuator's output
ROD_I, ROD_O = LANE_I + 0.0065, YT[1] + 0.0005      # the 5 mm rod's
# ankle: one RS04 in the shin, output outward; a 6206 on the far side
YA_S = (YC - H4 / 2 - 0.006, YC + H4 / 2 - 0.006)
FOOT = dict(x=(XK - 0.115, XK + 0.215), y=(YC - 0.095, YC + 0.095), plate=0.040, sole=0.040)

# ---------------------------------------------------------------- body

BX, BW = (-0.300, 0.200), 0.205
BZ = (ZY + 0.030, 1.045)
XN, ZN = 0.175, 0.940                              # neck pitch, in the body's front
YN = (0.034, 0.090)                                # the neck's two stators, either side of its tube
DECK = (ZY + 0.010 + H4, ZY + 0.010 + H4 + PL)     # the plate the yaw stators hang from
UPPER = (BZ[1] - 0.030, BZ[1] - 0.030 + PL)


def body_panels():
    secs = [(BZ[0], -0.05, 0, 0.235, 0.190, 6.0), (BZ[0] + 0.05, -0.05, 0, 0.250, BW, 8.0), (BZ[1] - 0.05, -0.05, 0, 0.250, BW, 8.0), (BZ[1] - 0.015, -0.05, 0, 0.230, 0.185, 5.0), (BZ[1], -0.05, 0, 0.190, 0.140, 3.5)]
    out = []
    xs = [-0.310, -0.068, 0.070, 0.205]
    ys = [-0.215, 0.0, 0.215]
    for i in range(3):
        for j in range(2):
            out.append(loft(f'body panel {"RMF"[i]}{"RL"[j]}', secs, WHITE, 'shell', open=('bottom',), clip=[((xs[i], 0, 0), (1, 0, 0)), ((xs[i + 1], 0, 0), (-1, 0, 0)), ((0, ys[j], 0), (0, 1, 0)), ((0, ys[j + 1], 0), (0, -1, 0))]))
    return [dict(g, material='petg') for g in out]


neck_slot = box('neck slot', (XN - 0.135, -0.125, ZN - 0.09), (0.26, 0.125, BZ[1] + 0.02), WHITE, 'shell')
yaw_in_l, yaw_out_l = bearing('L hip yaw', 'L_hip_yaw', (0, YY, ZY + 0.010 + H4 / 2), 'z', '61824', 'trunk', 'L_hip_yaw_link')
yaw_in_r = [mirror_geom(g) for g in yaw_in_l]
for g in yaw_in_r:
    if g.get('on_joint'):
        g['on_joint'] = 'R_hip_yaw'
link('trunk', [
    metal('deck plate', (-0.285, -0.170, DECK[0]), (0.210, 0.170, DECK[1]), mat='al7075', fill=0.45),
    metal('upper plate', (-0.260, -0.150, UPPER[0]), (0.065, 0.150, UPPER[1]), fill=0.4),
    *[metal(f'body post {i}', (x - 0.012, y - 0.012, DECK[1] - 0.0005), (x + 0.012, y + 0.012, UPPER[0] + 0.0005), ALD) for i, (x, y) in enumerate([(-0.24, 0.13), (-0.24, -0.13), (0.04, 0.13), (0.04, -0.13)])],
    # the neck's two plates, up from the deck, either side of its stators
    dict(side_plate('neck plate L', YN[1], PL, [(XN, ZN, 0.075), (XN - 0.10, DECK[1] + 0.029, 0.03), (XN + 0.015, DECK[1] + 0.029, 0.03)]), fill=0.6),
    dict(side_plate('neck plate R', -YN[1] - PL, PL, [(XN, ZN, 0.075), (XN - 0.10, DECK[1] + 0.029, 0.03), (XN + 0.015, DECK[1] + 0.029, 0.03)]), fill=0.6),
    metal('neck tie', (XN - 0.112, -YN[1] - 0.0005, DECK[1] - 0.0005), (XN - 0.100, YN[1] + 0.0005, ZN - 0.02), ALD),
    # the battery, computer and power board on the deck. Named 24S until 2026-11-05: a 24S pack is about 100 V full, and RobStride's manuals give 60 V as the most these actuators take. 13S is 54.6 V full, as 14S's 58.8 leaves no room
    # for what walking brakes back into the bus. The candidate to bench-test (2026-11-05, docs/big/BOM.md): Dan-Tech's 13S5P soft pack, 280 x 80 x 130, 5.2 kg, across the body between the posts. It has no BMS or case, so what was left of the
    # old box and its 8 kg holds those as an allowance, unchosen, and the walks' total stays the same
    box('battery 13S', (-0.215, -0.140, DECK[1] - 0.0005), (-0.135, 0.140, DECK[1] + 0.130), CELL, material='cells', mass=5.2),
    box('battery BMS, fuse and case, allowance', (-0.135, -0.095, DECK[1] - 0.0005), (-0.075, 0.095, UPPER[0] - 0.005), PCB, material='cells', mass=2.8),
    box('computer and power boards', (-0.065, -0.085, DECK[1] - 0.0005), (0.025, 0.085, DECK[1] + 0.03), PCB, material='electronics', mass=1.2),
    *body_panels(),
    cut(neck_slot, 'body panel FR', 'body panel FL', 'body panel MR', 'body panel ML'),
    # The hip yaw drums reach 8 mm up into the body's lower edge (Fusion's first clash check: a part in one link meeting one in another): a round clearance, 4 mm over the drum
    cut(cyl('L hip yaw drum clearance', (0, YY, ZY + 0.038), 'z', 0.085, 0.02), 'body panel ML'),
    cut(cyl('R hip yaw drum clearance', (0, -YY, ZY + 0.038), 'z', 0.085, 0.02), 'body panel MR'),
    *bolts('deck bolt L', (0, YY, DECK[1]), 'z', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, -1),
    *bolts('deck bolt R', (0, -YY, DECK[1]), 'z', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, -1),
    # the yaw bearings' inner rings hang from the deck on a sleeve round each stator
    disc('L hip yaw sleeve', (0, YY, ZY + 0.010 + H4 / 2 + 0.0145), 'z', 0.0625, H4 - 0.028, ALD),
    cut(cyl('L hip yaw sleeve bore', (0, YY, ZY + 0.010 + H4 / 2), 'z', R4 + 0.0005, H4 + 0.01), 'L hip yaw sleeve'),
    disc('R hip yaw sleeve', (0, -YY, ZY + 0.010 + H4 / 2 + 0.0145), 'z', 0.0625, H4 - 0.028, ALD),
    cut(cyl('R hip yaw sleeve bore', (0, -YY, ZY + 0.010 + H4 / 2), 'z', R4 + 0.0005, H4 + 0.01), 'R hip yaw sleeve'),
    *yaw_in_l, *yaw_in_r,
    stator('L_hip_yaw actuator', 'RS04', (0, YY, ZY + 0.010 + H4 / 2), 'z'),
    seat('L hip yaw', (0, YY, DECK[0]), 'z'),
    seat('R hip yaw', (0, -YY, DECK[0]), 'z'),
    seat('neck L', (XN, YN[1], ZN), 'y'),
    seat('neck R', (XN, -YN[1], ZN), 'y'),
    stator('R_hip_yaw actuator', 'RS04', (0, -YY, ZY + 0.010 + H4 / 2), 'z'),
    stator('neck_pitch actuator L', 'RS04', (XN, (YN[0] + YN[1]) / 2, ZN), 'y'),
    stator('neck_pitch actuator R', 'RS04', (XN, -(YN[0] + YN[1]) / 2, ZN), 'y'),
], 'a plate frame in printed panels: the yaw actuators, battery and computer, the neck in front')

# ---------------------------------------------------------------- left leg

XRS = (0.062, 0.062 + H4)                          # roll stators, front and back, outputs inward
link('L_hip_yaw_link', [
    disc('L hip yaw output plate', (0, YY, ZY + 0.004), 'z', 0.085, 0.008),
    metal('L hip yaw beam', (-0.130, YY - 0.055, ZY - 0.012), (0.130, YY + 0.055, ZY + 0.0001), mat='al7075'),
    # a drum from the plate up round the stator to the bearing's outer race
    disc('L hip yaw drum', (0, YY, ZY + 0.008 + (H4 / 2 + 0.002) / 2), 'z', 0.081, H4 / 2 + 0.002, ALD),
    cut(cyl('L hip yaw drum bore', (0, YY, ZY + 0.008 + (H4 / 2 + 0.002) / 2), 'z', 0.0745, H4), 'L hip yaw drum'),
    *yaw_out_l,
    *bolts('L hip yaw output bolt', (0, YY, ZY + 0.008), 'z', ACT['RS04']['out_pcd'], 9, 'M5', 0.016, 1),
    *[metal(f'L hip roll cheek {"FB"[i]}', (sg * XRS[1] if sg < 0 else XRS[1], 0, 0) if False else tuple(sorted((sg * XRS[1], sg * (XRS[1] + PL)))) [0:1] + (YY - 0.055, ZR - 0.070), tuple(sorted((sg * XRS[1], sg * (XRS[1] + PL))))[1:2] + (YY + 0.055, ZY - 0.011), mat='al7075') for i, sg in enumerate((1, -1))],
    stator('L_hip_roll actuator F', 'RS04', ((XRS[0] + XRS[1]) / 2, YY, ZR), 'x'),
    seat('L hip roll F', (XRS[1], YY, ZR), 'x'),
    seat('L hip roll B', (-XRS[1], YY, ZR), 'x'),
    stator('L_hip_roll actuator B', 'RS04', (-(XRS[0] + XRS[1]) / 2, YY, ZR), 'x'),
    *bolts('L hip roll mount bolt F', (XRS[1] + PL, YY, ZR), 'x', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, -1),
    *bolts('L hip roll mount bolt B', (-XRS[1] - PL, YY, ZR), 'x', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, 1),
], 'hangs from the yaw actuator; carries the two roll actuators')
link('L_hip_roll_link', [
    # the yoke: a plate on each roll output, a box between them, out to the pitch uprights
    disc('L hip roll output F', (0.058, YY, ZR), 'x', 0.040, 0.008),
    disc('L hip roll output B', (-0.058, YY, ZR), 'x', 0.040, 0.008),
    metal('L hip roll yoke', (-0.054, YY - 0.045, ZR - 0.045), (0.054, YI[0] + 0.0005, ZR + 0.045), ALD, 'al7075', 0.35),
    *bolts('L hip roll output bolt F', (0.054, YY, ZR), 'x', ACT['RS04']['out_pcd'], 9, 'M5', 0.016, 1),
    side_plate('L hip pitch upright in', YI[0], PL, [(0, ZP, 0.075)]),
    side_plate('L hip pitch upright out', YO[0], PL, [(0, ZP, 0.075)]),
    metal('L hip pitch bridge', (0.010, YI[1] - 0.0005, ZP + R4 + 0.002), (0.075, YO[0] + 0.0005, ZP + R4 + 0.002 + PL), mat='al7075'),
    metal('L hip pitch rib', (0.010, YI[0], ZP + 0.058), (0.075, YI[1], ZP + R4 + 0.002 + PL)),
    metal('L hip pitch rib out', (0.010, YO[0], ZP + 0.058), (0.075, YO[1], ZP + R4 + 0.002 + PL)),
    stator('L_hip_pitch actuator I', 'RS04', (0, sum(YSI) / 2, ZP), 'y'),
    seat('L hip pitch I', (0, YSI[0], ZP), 'y'),
    seat('L hip pitch O', (0, YSO[1], ZP), 'y'),
    stator('L_hip_pitch actuator O', 'RS04', (0, sum(YSO) / 2, ZP), 'y'),
    *bolts('L hip pitch mount bolt O', (0, YO[1], ZP), 'y', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, -1),
], 'the yoke: two roll outputs, and the two pitch actuators either side of the thigh')

# the thigh: two inner plates between the hip outputs, two outer plates behind the hip that carry the knee stators; a printed cover over each
TH = [(0.0, ZP, 0.055), (XK, ZK, 0.075), (XQ, ZQ, 0.070)]
THO = [(XQ, ZQ, 0.074), (XK, ZK + 0.055, 0.030)]
kn_in, kn_out = bearing('L knee', 'L_knee', (XK, YT[0] + PL - 0.006, ZK), 'y', '6908', None, None)
kn_in2, kn_out2 = bearing('L knee far', 'L_knee', (XK, YT[1] - PL + 0.006, ZK), 'y', '6908', None, None)
yaw_pad = YCI - 0.006
def thigh_covers():
    out = []
    r0, r1, r2 = 0.075, 0.085, 0.085
    pieces = (('hip', [(-0.075, ZP - 0.012, 0.035), (-0.085, ZP + 0.040, 0.022), (-0.150, ZP + 0.040, 0.022), (-0.150, ZP - 0.070, 0.022), (-0.078, ZP - 0.050, 0.030)]),
              ('rear', [(-0.160, ZP + 0.045, 0.030), (-0.285, ZP + 0.045, 0.040), (-0.300, ZP - 0.040, 0.040), (-0.160, ZP - 0.075, 0.030)]),
              ('knee', [(-0.160, ZP - 0.085, 0.020), (-0.300, ZP - 0.050, 0.030), (XK - 0.060, ZK + 0.020, 0.040), (XK + 0.040, ZK + 0.020, 0.040), (-0.115, ZP - 0.080, 0.020)]))
    for t, pts in pieces:
        out.append(dict(plate(f'L thigh cover out {t}', YO[1] + 0.008, 0.003, pts, WHITE, 'decal'), material='petg', exposed=True))
        # No covers on the thigh's inner side (2026-11-05). Fusion's first clash check found the hip piece 8.4 cm3 into the rear hip roll actuator, and the knee piece 0.16 into the cheek. tools/big_sweep.py then found the
        # other two reaching the body panel (10.7 cm3), cheek, deck and beam as the hip moves. They're 'decal', so the offline checks never saw any of it. Between the legs they show least, and the outer ones sweep clear.
        # The cost: the frame shows from the inside
    # stand-offs from the rear plates: one per piece, each side
    for t, (x_, z_) in (('hip', (-0.150, ZP + 0.010)), ('rear', (-0.255, ZQ)), ('knee', (XK, ZK + 0.060))):
        out.append(metal(f'L thigh cover post out {t}', (x_ - 0.005, YO[1] - 0.0005, z_ - 0.005), (x_ + 0.005, YO[1] + 0.0085, z_ + 0.005), ALD))
    return out


link('L_hip_pitch_link', [
    side_plate('L thigh plate in', YT[0], PL, TH),
    side_plate('L thigh plate out', YT[1] - PL, PL, TH),
    cut(cyl('L thigh bore in', (XK, YT[0] + PL - 0.006, ZK), 'y', BEAR['6908']['D'] / 2 - 0.0002, 0.02), 'L thigh plate in'),
    cut(cyl('L thigh bore out', (XK, YT[1] - PL + 0.006, ZK), 'y', BEAR['6908']['D'] / 2 - 0.0002, 0.02), 'L thigh plate out'),
    metal('L thigh spacer hip', (-0.05, YT[0] + PL - 0.0005, ZP - 0.07), (-0.03, YT[1] - PL + 0.0005, ZP + 0.03), ALD),
    metal('L thigh spacer mid', (XQ - 0.012, YT[0] + PL - 0.0005, ZQ - 0.03), (XQ + 0.012, YT[1] - PL + 0.0005, ZQ + 0.04), ALD),
    disc('L hip pitch output I', (0, YSI[1] + 0.00625, ZP), 'y', 0.040, 0.0125),
    disc('L hip pitch output O', (0, YSO[0] - 0.00625, ZP), 'y', 0.040, 0.0125),
    *bolts('L hip pitch output bolt', (0, YT[1] - PL, ZP), 'y', ACT['RS04']['out_pcd'], 9, 'M5', 0.016, 1),
    side_plate('L thigh rear plate in', YI[0], PL, THO),
    side_plate('L thigh rear plate out', YO[0], PL, THO),
    *[metal(f'L thigh tie {i}{n}', (x - 0.006, ya, z - 0.006), (x + 0.006, yb, z + 0.006), ALD) for i, (x, z) in enumerate([(XQ + 0.068, ZQ - 0.012), (XQ + 0.03, ZQ - 0.066)]) for n, (ya, yb) in (('i', (YI[1] - 0.0005, YT[0] + 0.0005)), ('o', (YT[1] - 0.0005, YO[0] + 0.0005)))],
    stator('L_knee actuator I', 'RS04', (XQ, sum(YSI) / 2, ZQ), 'y'),
    seat('L knee I', (XQ, YSI[0], ZQ), 'y'),
    seat('L knee O', (XQ, YSO[1], ZQ), 'y'),
    stator('L_knee actuator O', 'RS04', (XQ, sum(YSO) / 2, ZQ), 'y'),
    side_plate('L knee crank I', LANE_I, 0.006, [(XQ, ZQ, 0.028), (PIN_A[0], PIN_A[1], 0.014)]),
    side_plate('L knee crank O', LANE_O, 0.006, [(XQ, ZQ, 0.028), (PIN_A[0], PIN_A[1], 0.014)]),
    seat('L knee crank I', (XQ, YSI[1], ZQ), 'y', 0.02),
    seat('L knee crank O', (XQ, YSO[0], ZQ), 'y', 0.02),
    axle('L knee crank pin I', (PIN_A[0], (LANE_I + ROD_I + 0.005) / 2, PIN_A[1]), 'y', 0.005, ROD_I + 0.005 - LANE_I),
    axle('L knee crank pin O', (PIN_A[0], (ROD_O + LANE_O + 0.006) / 2, PIN_A[1]), 'y', 0.005, LANE_O + 0.006 - ROD_O),
    *bolts('L knee mount bolt O', (XQ, YO[1], ZQ), 'y', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, -1),
    *kn_out, *kn_out2,
    # the rods, drawn at knee angle 0: they swing with the knee, and a part in one link can't, so 'decal' keeps them out of the sweep checks
    dict(plate('L knee rod I', ROD_I, 0.005, [(PIN_A[0], PIN_A[1], 0.011), (PIN_B[0], PIN_B[1], 0.011)], AL, 'decal'), material='al7075', exposed=True),
    dict(plate('L knee rod O', ROD_O, 0.005, [(PIN_A[0], PIN_A[1], 0.011), (PIN_B[0], PIN_B[1], 0.011)], AL, 'decal'), material='al7075', exposed=True),
    *thigh_covers(),
], 'two plates between the hip outputs, two behind them for the knee actuators, crank and rod down to the knee')
SX_, SY_ = 0.055, 0.045                            # the shin box, half sizes
SHIN_TOP = ZK - 0.100                              # clear of the thigh plates (75 mm) and knee sprockets as the knee turns


def shin_cover():
    secs = [(ZA + R4 + 0.012, XK, YC, SX_ + 0.016, SY_ + 0.016, 4.0), (SHIN_TOP + 0.002, XK, YC, SX_ + 0.012, SY_ + 0.012, 4.0)]
    mid = (ZA + R4 + 0.012 + SHIN_TOP) / 2
    return [dict(loft(f'L shin cover {t}', secs, DARK, 'shell', open=('top', 'bottom'), clip=[((XK, 0, 0), (sg, 0, 0))]), material='petg') for t, sg in (('front', 1), ('back', -1))]


link('L_knee_link', [
    axle('L knee shaft', (XK, YC, ZK), 'y', 0.020, YT[1] - YT[0] + 0.032),
    side_plate('L knee lever I', LANE_I, 0.006, [(XK, ZK, 0.030), (PIN_B[0], PIN_B[1], 0.014)]),
    side_plate('L knee lever O', LANE_O, 0.006, [(XK, ZK, 0.030), (PIN_B[0], PIN_B[1], 0.014)]),
    axle('L knee lever pin I', (PIN_B[0], (LANE_I + ROD_I + 0.005) / 2, PIN_B[1]), 'y', 0.005, ROD_I + 0.005 - LANE_I),
    axle('L knee lever pin O', (PIN_B[0], (ROD_O + LANE_O + 0.006) / 2, PIN_B[1]), 'y', 0.005, LANE_O + 0.006 - ROD_O),
    side_plate('L shin hub in', YC - 0.0115, 0.006, [(XK, ZK, 0.030), (XK, SHIN_TOP - 0.005, 0.042)], AL, 'al7075'),
    side_plate('L shin hub out', YC + 0.0055, 0.006, [(XK, ZK, 0.030), (XK, SHIN_TOP - 0.005, 0.042)], AL, 'al7075'),
    metal('L shin spacer', (XK - 0.015, YC - 0.0060, ZK - 0.10), (XK + 0.015, YC + 0.0060, ZK - 0.03), ALD),
    # the box: top and bottom plates, and four walls
    metal('L shin top', (XK - SX_, YC - SY_, SHIN_TOP - 0.008), (XK + SX_, YC + SY_, SHIN_TOP), mat='al7075'),
    metal('L shin wall front', (XK + SX_ - 0.005, YC - SY_, ZA + R4 + 0.002 + PL - 0.0005), (XK + SX_, YC + SY_, SHIN_TOP - 0.0075)),
    metal('L shin wall back', (XK - SX_, YC - SY_, ZA + R4 + 0.002 + PL - 0.0005), (XK - SX_ + 0.005, YC + SY_, SHIN_TOP - 0.0075)),
    metal('L shin wall in', (XK - SX_ + 0.0045, YC - SY_, ZA + R4 + 0.002 + PL - 0.0005), (XK + SX_ - 0.0045, YC - SY_ + 0.005, SHIN_TOP - 0.0075)),
    metal('L shin wall out', (XK - SX_ + 0.0045, YC + SY_ - 0.005, ZA + R4 + 0.002 + PL - 0.0005), (XK + SX_ - 0.0045, YC + SY_, SHIN_TOP - 0.0075)),
    *shin_cover(),
    # the ankle stator's cradle: a plate each side, cap across the top
    metal('L shin cap', (XK - SX_ - 0.008, YC - SY_ - 0.002, ZA + R4 + 0.002), (XK + SX_ + 0.008, YC + SY_ + 0.002, ZA + R4 + 0.002 + PL), mat='al7075'),
    side_plate('L ankle plate in', YA_S[0] - PL, PL, [(XK, ZA, 0.072)]),
    stator('L_ankle_pitch actuator', 'RS04', (XK, sum(YA_S) / 2, ZA), 'y'),
    seat('L ankle', (XK, YA_S[0], ZA), 'y'),
    *bolts('L ankle mount bolt', (XK, YA_S[0] - PL, ZA), 'y', ACT['RS04']['mount_pcd'], 10, 'M4', 0.012, 1),
    axle('L ankle stub', (XK, YA_S[0] - PL - 0.0095, ZA), 'y', 0.015, 0.0200),
], 'the knee shaft on two bearings, down to the ankle actuator')
FX, FY = FOOT['x'], FOOT['y']
FC = (sum(FX) / 2, sum(FY) / 2)
SA, SB = (FX[1] - FX[0]) / 2, (FY[1] - FY[0]) / 2
an_in, an_out = bearing('L ankle', 'L_ankle_pitch', (XK, YA_S[0] - PL - 0.014, ZA), 'y', '6206', None, None)


def foot_part(name, zs, x0, x1, color, mat, **kw):
    return dict(loft(name, [(z, FC[0], FC[1], SA - d, SB - d, n) for z, d, n in zs], color, 'struct', open=(), clip=[((x0, 0, 0), (1, 0, 0)), ((x1, 0, 0), (-1, 0, 0))]), material=mat, exposed=True, **kw)


SOLE = [(0.0, 0.010, 3.0), (0.006, 0.003, 4.0), (FOOT['plate'] - 0.006, 0.0, 4.5)]
UP = [(FOOT['plate'] + 0.006, 0.0, 4.5), (FOOT['plate'] + 0.030, 0.0, 4.5), (FOOT['plate'] + 0.046, 0.012, 3.5)]
SPLIT = FC[0] + 0.015
link('L_foot', [
    metal('L foot plate', (FX[0] + 0.012, FY[0] + 0.012, FOOT['plate'] - 0.0065), (FX[1] - 0.012, FY[1] - 0.012, FOOT['plate'] + 0.0065), mat='al7075', fill=0.6),
    side_plate('L ankle ear out', YA_S[1] + PL + 0.004, PL, [(XK, ZA, 0.040), (XK - 0.075, FOOT['plate'] + 0.006, 0.006), (XK + 0.085, FOOT['plate'] + 0.006, 0.006)]),
    side_plate('L ankle ear in', YA_S[0] - PL - 0.022 - PL, PL, [(XK, ZA, 0.040), (XK - 0.075, FOOT['plate'] + 0.006, 0.006), (XK + 0.085, FOOT['plate'] + 0.006, 0.006)]),
    disc('L ankle output', (XK, YA_S[1] + 0.0065, ZA), 'y', 0.040, 0.013),
    *bolts('L ankle output bolt', (XK, YA_S[1] + PL + 0.004 + PL, ZA), 'y', ACT['RS04']['out_pcd'], 9, 'M5', 0.020, -1),
    metal('L ankle bearing housing', (XK - 0.040, YA_S[0] - PL - 0.0225, ZA - 0.040), (XK + 0.040, YA_S[0] - PL - 0.0065, ZA + 0.040), mat='al7075', fill=0.6),
    cut(cyl('L ankle housing bore', (XK, YA_S[0] - PL - 0.014, ZA), 'y', BEAR['6206']['D'] / 2 - 0.0002, 0.03), 'L ankle bearing housing'),
    foot_part('L sole rear', SOLE, FX[0] - 0.01, SPLIT, YELLOW, 'tpu'),
    foot_part('L sole front', SOLE, SPLIT, FX[1] + 0.01, YELLOW, 'tpu', contact=dict(c=[FC[0], FC[1], 0.002], size=[2 * SA - 0.03, 2 * SB - 0.02, 0.004])),
    foot_part('L shoe rear', UP, FX[0] - 0.01, SPLIT, ORANGE, 'petg'),
    foot_part('L shoe front', UP, SPLIT, FX[1] + 0.01, ORANGE, 'petg'),
    cut(box('L shoe opening', (XK - 0.085, YA_S[0] - PL - 0.03, FOOT['plate'] + 0.0064), (XK + 0.095, YA_S[1] + 2 * PL + 0.012, 0.2), ORANGE, 'shell'), 'L shoe rear', 'L shoe front'),
    *an_out,
], 'an aluminium plate on two ears; soles and shoe printed in two')
# the bearings' inner rings on the stub and shaft
LINKS['L_knee_link']['geoms'] += kn_in + kn_in2 + an_in
joint('L_hip_yaw', 'trunk', 'L_hip_yaw_link', (0, YY, ZY), 'z', (-0.45, 0.45), 'RS04', out=-1, interface=['L_hip_yaw actuator (buy) RS04', 'L hip yaw output plate', 'L hip yaw drum', 'L hip yaw sleeve'])
joint('L_hip_roll', 'L_hip_yaw_link', 'L_hip_roll_link', (0.062, YY, ZR), 'x', (-0.33, 0.33), 'RS04', count=2, out=-1, act_c=((XRS[0] + XRS[1]) / 2, YY, ZR), interface=['L_hip_roll actuator F (buy) RS04', 'L_hip_roll actuator B (buy) RS04', 'L hip roll output F', 'L hip roll output B'])
joint('L_hip_pitch', 'L_hip_roll_link', 'L_hip_pitch_link', (0, YSI[1], ZP), 'y', (-1.57, 0.43), 'RS04', count=2, out=1, act_c=(0, sum(YSI) / 2, ZP), interface=['L_hip_pitch actuator I (buy) RS04', 'L_hip_pitch actuator O (buy) RS04', 'L hip pitch output I', 'L hip pitch output O'])
joint('L_knee', 'L_hip_pitch_link', 'L_knee_link', (XK, YC, ZK), 'y', KNEE_RANGE, 'RS04', count=2, ratio=KNEE_RATIO, out=1, act_c=(XQ, sum(YSI) / 2, ZQ), remote=True)
joint('L_ankle_pitch', 'L_knee_link', 'L_foot', (XK, YA_S[1], ZA), 'y', (-1.2, 1.2), 'RS04', out=1, act_c=(XK, sum(YA_S) / 2, ZA), interface=['L_ankle_pitch actuator (buy) RS04', 'L ankle output', 'L ankle stub', 'L ankle bearing housing'])

# ---------------------------------------------------------------- neck and head

ZH = ZN + 0.340                                    # head pitch
NT = (-0.030, 0.030)                               # the neck's tube, 60 wide in y
XHP = XN
ZHS = ZN + 0.135                                   # the head pitch stators, low on the neck, for the head's reach
hp_in1, hp_out1 = bearing('head pitch L', 'head_pitch', (XN, 0.022, ZH), 'y', '6908', None, None)
hp_in2, hp_out2 = bearing('head pitch R', 'head_pitch', (XN, -0.022, ZH), 'y', '6908', None, None)
hp_outer = hp_out1 + hp_out2
link('neck_link', [
    disc('neck output L', (XN, YN[0] - 0.005, ZN), 'y', 0.040, 0.010),
    disc('neck output R', (XN, -YN[0] + 0.005, ZN), 'y', 0.040, 0.010),
    metal('neck spine', (XN - 0.040, NT[0], ZN - 0.050), (XN + 0.040, NT[1], ZH + 0.040), ALD, 'al7075', 0.25),
    cut(cyl('neck spine bore', (XN, 0, ZH), 'y', BEAR['6908']['D'] / 2 - 0.0002, 0.08), 'neck spine'),
    *hp_outer,
    side_plate('head pitch stator plate L', YN[0] + 0.012 + H4, PL, [(XN, ZHS, 0.072)]),
    stator('head_pitch actuator L', 'RS04', (XN, YN[0] + 0.012 + H4 / 2, ZHS), 'y'),
    axle('head pitch drive sprocket L (buy) 13T #40', (XN, 0.040, ZHS), 'y', PCD13 / 2, 0.012),
    *chain('head pitch chain L (buy) #40', (XN, ZHS), (XN, ZH), 0.038, PCD13 / 2, PCD25 / 2),
    metal('head pitch stator tie L', (XN - 0.012, NT[1] - 0.0005, ZHS + R4 + 0.001), (XN + 0.012, YN[1] + PL + 0.0045, ZHS + R4 + 0.011), ALD),
    seat('head pitch L', (XN, YN[0] + 0.012 + H4, ZHS), 'y'),
], 'a pocketed spine on the two neck outputs; the head pitch actuator low on it, on chain to the top')
ZHY = ZH + 0.115
ZHEAD = ZHY + 0.045                                # the hood's lower edge
HK = 6.95                                          # the small duck's head, at this height: 0.85 m long
HFRONT, HCX = XN + 0.040 + 0.60, XN
HOOD_MD = T.HOOD_MD
HBACK = HFRONT - HK * HOOD_MD[0][0]
link('head_pitch_link', [
    dict(axle('head pitch shaft', (XN, 0, ZH), 'y', 0.020, 0.150), fill=0.45),      # hollow: 40 mm outside, 30 inside
    *hp_in1, *hp_in2,
    metal('head pitch yoke', (XN - 0.070, 0.043, ZH - 0.040), (XN + 0.070, 0.051, ZHY - 0.039), mat='al7075'),
    metal('head pitch yoke R', (XN - 0.070, -0.051, ZH - 0.040), (XN + 0.070, -0.043, ZHY - 0.039), mat='al7075'),
    metal('head pitch bridge', (XN - 0.070, -0.051, ZHY - 0.047), (XN + 0.070, 0.051, ZHY - 0.039), mat='al7075'),
    dict(axle('head pitch sprocket L (buy) 25T #40', (XN, 0.038, ZH), 'y', PCD25 / 2, 0.008), fill=0.5),   # with lightening holes
    stator('head_yaw actuator', 'RS03', (XN, 0, ZHY - 0.039 + ACT['RS03']['h'] / 2), 'z'),
    seat('head yaw', (XN, 0, ZHY - 0.039), 'z', 0.05),
], 'the head pitch shaft on bearings at the neck top; the head yaw actuator on the bridge')
XHR = XN + 0.14
link('head_yaw_link', [
    disc('head yaw output', (XN, 0, ZHY + 0.021), 'z', 0.040, 0.008),
    metal('head yaw plate', (XN - 0.06, -0.06, ZHY + 0.025), (XHR + 0.002, 0.06, ZHY + 0.033), mat='al7075'),
    metal('head roll cradle', (XHR - 0.006, -0.06, ZHY + 0.025), (XHR + 0.002, 0.06, ZHY + 0.160), mat='al7075'),
    stator('head_roll actuator', 'RS03', (XHR + 0.002 + ACT['RS03']['h'] / 2, 0, ZHY + 0.095), 'x'),
    seat('head roll', (XHR + 0.002, 0, ZHY + 0.095), 'x', 0.05),
    *bolts('head roll mount bolt', (XHR - 0.006, 0, ZHY + 0.095), 'x', ACT['RS03']['mount_pcd'], ACT['RS03']['mount_n'], 'M4', 0.012, 1),
], 'turns the head; carries the head roll actuator')
XFR = XHR + 0.002 + ACT['RS03']['h'] + 0.010       # the head's main frame, on the roll output


def hood_panels():
    """The hood's arches, cut along x and across y and z so each panel prints on a 256 mm bed."""
    z0 = ZHEAD + 0.035
    s = [(HBACK - 0.03, z0, 0, 0.04, 0.10, 2.4)]
    for k, (d, h, w) in enumerate(HOOD_MD):
        s.append((HFRONT - HK * d, z0, 0, HK * h, HK * w, 2.4 + 0.6 * k / (len(HOOD_MD) - 1)))
    s.append((HFRONT + 0.08,) + s[-1][1:])
    xs = [HBACK - 0.04, HFRONT - 0.64, HFRONT - 0.42, HFRONT - 0.21, HFRONT + 0.005]
    ys = [-0.34, -0.12, 0.12, 0.34]
    zc = z0 + 0.135
    out = []
    for i in range(len(xs) - 1):
        for j in range(3):
            pl = [((xs[i], 0, 0), (1, 0, 0)), ((xs[i + 1], 0, 0), (-1, 0, 0)), ((0, ys[j], 0), (0, 1, 0)), ((0, ys[j + 1], 0), (0, -1, 0))]
            if j == 1:
                out.append(dict(loft(f'hood panel {i}c', s, WHITE, 'shell', open=(), along='x', clip=pl + [((0, 0, zc), (0, 0, 1))]), material='petg'))
            else:
                out.append(dict(loft(f'hood panel {i}{"RL"[j // 2]}u', s, WHITE, 'shell', open=(), along='x', clip=pl + [((0, 0, zc), (0, 0, 1))]), material='petg'))
                out.append(dict(loft(f'hood panel {i}{"RL"[j // 2]}l', s, WHITE, 'shell', open=(), along='x', clip=pl + [((0, 0, zc), (0, 0, -1)), ((0, 0, z0), (0, 0, 1))]), material='petg'))
    return out


JX = HFRONT - 0.30
JZ = ZHEAD + 0.02
def arch():
    return [(ZHEAD + 0.035, HK * HOOD_MD[-1][1], HK * HOOD_MD[-1][2])]


def face_panels():
    z0, a, b = arch()[0]
    secs = [(HFRONT + 0.004, z0, 0, a - 0.015, b - 0.015, 3.0), (HFRONT + 0.008, z0, 0, a - 0.015, b - 0.015, 3.0)]
    zc = z0 + 0.135
    out = []
    for j, (y0, y1) in enumerate(((-0.34, -0.12), (-0.12, 0.12), (0.12, 0.34))):
        pl = [((0, y0, 0), (0, 1, 0)), ((0, y1, 0), (0, -1, 0))]
        out.append(dict(loft(f'face panel {j}u', secs, GREY, 'decal', open=(), along='x', clip=pl + [((0, 0, zc), (0, 0, 1))]), material='petg'))
        out.append(dict(loft(f'face panel {j}l', secs, GREY, 'decal', open=(), along='x', clip=pl + [((0, 0, zc), (0, 0, -1)), ((0, 0, z0), (0, 0, 1))]), material='petg'))
    return out


def bill_panels():
    """The orange band under the hood, as the small duck's: a strip round its lower edge."""
    z0 = ZHEAD + 0.0175
    s_ = [(HBACK - 0.03, z0, 0, 0.0175, 0.14, 8.0)]
    for d, h, w in HOOD_MD:
        s_.append((HFRONT - HK * d, z0, 0, 0.0175, HK * w + 0.003, 8.0))
    s_.append((HFRONT + 0.008,) + s_[-1][1:])
    xs = [HBACK - 0.01, HFRONT - 0.64, HFRONT - 0.42, HFRONT - 0.21, HFRONT + 0.012]
    out = []
    for i in range(len(xs) - 1):
        for j, (y0, y1) in enumerate(((-0.35, -0.12), (-0.12, 0.12), (0.12, 0.35))):
            if j == 1 and i in (1, 2):                 # the rim is open here
                continue
            out.append(dict(loft(f'bill panel {i}{j}', s_, ORANGE, 'shell', open=(), along='x', clip=[((xs[i], 0, 0), (1, 0, 0)), ((xs[i + 1], 0, 0), (-1, 0, 0)), ((0, y0, 0), (0, 1, 0)), ((0, y1, 0), (0, -1, 0))]), material='petg'))
    return out


link('head', [
    disc('head roll output', (XFR - 0.0045, 0, ZHY + 0.095), 'x', 0.032, 0.010),
    metal('head main frame', (XFR, -0.20, ZHEAD), (XFR + PL, 0.20, ZHEAD + 0.24), mat='al6061', fill=0.25),
    metal('head rail L', (HBACK + 0.059, 0.188, ZHEAD + 0.02), (HFRONT - 0.039, 0.200, ZHEAD + 0.04), ALD, 'al6061', 0.3),
    metal('head rail R', (HBACK + 0.059, -0.200, ZHEAD + 0.02), (HFRONT - 0.039, -0.188, ZHEAD + 0.04), ALD, 'al6061', 0.3),
    metal('head rear frame', (HBACK + 0.06, -0.20, ZHEAD), (HBACK + 0.06 + PL, 0.20, ZHEAD + 0.09), mat='al6061', fill=0.3),
    metal('head front frame', (HFRONT - 0.04 - PL, -0.20, ZHEAD), (HFRONT - 0.04, 0.20, ZHEAD + 0.20), mat='al6061', fill=0.3),
    box('head boards and camera', (HFRONT - 0.10, -0.06, ZHEAD + 0.10), (HFRONT - 0.0475, 0.06, ZHEAD + 0.16), PCB, material='electronics', mass=0.6, exposed=True),
    *hood_panels(),
    *face_panels(),
    *bill_panels(),
    cut(box('bill opening rear', (HBACK + 0.07, -0.186, ZHEAD - 0.01), (HFRONT - 0.42, 0.186, ZHEAD + 0.05), ORANGE, 'shell'), *[f'bill panel {i}{j}' for i in range(4) for j in range(3) if not (j == 1 and i in (1, 2))]),
    cut(box('bill opening front', (HFRONT - 0.42, -0.225, ZHEAD - 0.01), (HFRONT - 0.03, 0.225, ZHEAD + 0.05), ORANGE, 'shell'), *[f'bill panel {i}{j}' for i in range(4) for j in range(3) if not (j == 1 and i in (1, 2))]),
    dict(cyl('eye ring', (HFRONT + 0.008, 0, ZHEAD + 0.17), 'x', 0.105, 0.016, AMBER, 'decal'), material='petg', mass=0.30),      # printed and hollow, not solid metal
    dict(cyl('eye lens', (HFRONT + 0.012, 0, ZHEAD + 0.17), 'x', 0.060, 0.012, LENS, 'decal'), material='petg', mass=0.10),
    metal('head beak mount', (HBACK + 0.11, -0.20, ZHEAD + 0.03), (HBACK + 0.17, 0.20, ZHEAD + 0.036), mat='al6061', fill=0.45),
    stator('beak actuator', 'RS00', (HBACK + 0.14, 0, ZHEAD + 0.0640), 'y'),
    seat('beak', (HBACK + 0.14, 0, ZHEAD + 0.036), 'z', 0.02),
    metal('head beak lug L', (JX - 0.02, 0.188, JZ - 0.02), (JX + 0.02, 0.2045, JZ + 0.02), mat='al6061'),
    metal('head beak lug R', (JX - 0.02, -0.2045, JZ - 0.02), (JX + 0.02, -0.188, JZ + 0.02), mat='al6061'),
], 'a plate-and-rail frame in printed panels')
link('beak_link', [
    metal('beak hinge L', (JX - 0.02, 0.205, JZ - 0.09), (JX + 0.02, 0.213, JZ + 0.02), mat='al6061'),
    metal('beak hinge R', (JX - 0.02, -0.213, JZ - 0.09), (JX + 0.02, -0.205, JZ + 0.02), mat='al6061'),
    metal('beak tray frame', (JX - 0.02, -0.213, JZ - 0.09), (HFRONT - 0.02, 0.213, JZ - 0.082), mat='al6061', fill=0.25),
    *[dict(loft(f'beak panel {i}', [(JX - 0.03, ZHEAD - 0.045, 0, 0.042, 0.30, 8.0), (HFRONT, ZHEAD - 0.045, 0, 0.042, 0.30, 8.0)], ORANGE, 'shell', open=(), along='x',
                clip=[((JX + 0.03 + (0.27 / 2) * (i // 3), 0, 0), (1, 0, 0)), ((JX + 0.03 + (0.27 / 2) * (i // 3 + 1), 0, 0), (-1, 0, 0)), ((0, -0.31 + 0.2067 * (i % 3), 0), (0, 1, 0)), ((0, -0.31 + 0.2067 * (i % 3 + 1), 0), (0, -1, 0))]), material='petg') for i in range(6)],
], 'the jaw: a sheet frame on two hinges, printed panels under it; the beak actuator drives it by a rod (to detail)')
joint('neck_pitch', 'trunk', 'neck_link', (XN, 0, ZN), 'y', (-0.15, 1.6), 'RS04', count=2, out=1, act_c=(XN, (YN[0] + YN[1]) / 2, ZN), interface=['neck_pitch actuator L (buy) RS04', 'neck_pitch actuator R (buy) RS04', 'neck output L', 'neck output R'])
joint('head_pitch', 'neck_link', 'head_pitch_link', (XN, 0, ZH), 'y', (-1.6, 1.6), 'RS04', count=1, ratio=CHAIN, out=1, act_c=(XN, YN[0] + 0.012 + H4 / 2, ZHS), remote=True)
joint('head_yaw', 'head_pitch_link', 'head_yaw_link', (XN, 0, ZHY + 0.017), 'z', (-2.5, 2.5), 'RS03', out=1, act_c=(XN, 0, ZHY - 0.039 + ACT['RS03']['h'] / 2), interface=['head_yaw actuator (buy) RS03', 'head yaw output'])
joint('head_roll', 'head_yaw_link', 'head', (XFR - 0.010, 0, ZHY + 0.095), 'x', (-0.38, 0.38), 'RS03', out=1, act_c=(XHR + 0.002 + ACT['RS03']['h'] / 2, 0, ZHY + 0.095), interface=['head_roll actuator (buy) RS03', 'head roll output'])
joint('beak', 'head', 'beak_link', (JX, 0.205, JZ), 'y', (0.0, 0.4), 'RS00', out=1, act_c=(HBACK + 0.14, 0, ZHEAD + 0.0640), remote=True)


def build():
    links, joints = {}, []
    for n, l in LINKS.items():
        links[n] = copy.deepcopy(l)
        if n.startswith('L_'):
            m = copy.deepcopy(l)
            m['name'] = mirror_name(n)
            m['geoms'] = []
            for g in l['geoms']:
                mg = mirror_geom(g)
                if mg.get('on_joint'):
                    mg['on_joint'] = mirror_name(g['on_joint'])
                if mg['name'].startswith('L_'):
                    mg['name'] = 'R_' + mg['name'][2:]
                m['geoms'].append(mg)
            links[m['name']] = m
    for j in JOINTS:
        joints.append(copy.deepcopy(j))
        if j['name'].startswith('L_'):
            m = copy.deepcopy(j)
            m['name'], m['parent'], m['child'] = mirror_name(j['name']), mirror_name(j['parent']), mirror_name(j['child'])
            m['origin'][1] = -m['origin'][1]
            m['act_c'][1] = -m['act_c'][1]
            m['interface'] = [('R_' + t[2:]) if t.startswith('L_') else ('R ' + t[2:]) if t.startswith('L ') else t for t in j['interface']]
            if m['axis'] in ('x', 'z'):
                m['lower'], m['upper'] = -j['upper'], -j['lower']
            if j['axis'] == 'y':
                m['out'] = -j['out']
            joints.append(m)
    for l in links.values():
        for g in l['geoms']:
            if g['role'] != 'cut' and 'material' not in g:
                g['material'] = 'actuator' if g['role'] == 'actuator' else ('tpu' if g['color'] == YELLOW else 'petg' if g['role'] == 'shell' else 'al6061')
    return dict(recipe='big', rl=RL, recipe_limits=dict(mass_budget_kg=115.0, target_tol=0.25, cannot=['floor pick', 'deep squat'], brief=['head forward and down, beak open', 'head tucked in']),
                frame='metres; X forward, Y left, Z up; floor z=0; zero pose standing', actuators=ACT, bearings=BEAR, materials=MATERIALS, links=links, joints=joints, root='trunk')


# For the trainer (tools/make_rl_model.py). Gains are a first guess, not measured: the order of a real full-size humanoid's walking gains, raised for this mass; damping about kp / 40.
# Each entry: joint without its side -> (kp N m/rad, kd N m s/rad), at the joint, after any pair or chain.
# speed_ratio: a crank's ratio changes along its stroke, and the trainer's motor has one. Its torque is the weakest point's (KNEE_RATIO). Its speed is the bent end's, about 11 rad/s, where the
# fast swing happens: the slowest point's 6.3 rad/s held the whole stroke back. So the straight end, slower still in a real crank, is optimistic here.
RL = dict(root_z=0.95, imu=[0.0, 0.0, 0.95], speed_ratio=dict(knee=KNEE_RATIO_BENT), gains=dict(hip_yaw=(150, 4), hip_roll=(300, 8), hip_pitch=(300, 8), knee=(400, 10), ankle=(100, 3),
                                                       neck_pitch=(200, 5), head_pitch=(300, 8), head_yaw=(60, 2), head_roll=(60, 2)))


if __name__ == '__main__':
    r = build()
    out = os.path.join(HERE, 'robot_big.json')
    json.dump(r, open(out, 'w', encoding='utf-8'), indent=1)
    # what cad/fusion/build.py reads: no printed part here has holes or pockets yet, so none is listed, and every panel is a plain body
    json.dump(dict(parts={}), open(os.path.join(HERE, 'parts_big.json'), 'w', encoding='utf-8'))
    json.dump({}, open(os.path.join(HERE, 'verify_points_big.json'), 'w', encoding='utf-8'))
    print(f"{len(r['links'])} links, {len(r['joints'])} joints -> {out}")
