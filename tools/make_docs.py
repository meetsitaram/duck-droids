"""BOM.md and docs/ASSEMBLY.md, from the parts and the order in tools/assembly.py, so the counts cannot drift from the spec.

  python -I tools/make_docs.py

Links, prices and stock were read from the listings on 2026-11-02: confirm before ordering.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assembly as A  # noqa: E402
import geom as G  # noqa: E402
import mass_model as MM  # noqa: E402

def amz(asin, label='Amazon'):
    return f'[{label}](https://www.amazon.com/dp/{asin})'


# Amazon's stock counts are what the page showed on 2026-11-02, and they change daily. Amazon's pages refuse AI agents, so they were not re-read on 2026-11-03: confirm them yourself.
# The other shops were re-read on 2026-11-03 (their pages or a search's copy of them).
BUY = [
    # (what, key in the spec, price each USD, where, note)
    ('Feetech STS3215-C044 servo, 7.4 V, 1:191', 'STS3215_C044', 23.98,
     f"{amz('B0H3THGR55', 'Amazon, MengJie')} (7 left at $23.98) and {amz('B0G2L15ZG8', 'Amazon, RCmall, the 1-191 option')} (6 left at $25.99). "
     'Neither alone has 8', 'hip roll, hip pitch, knee, ankle'),
    ('Feetech STS3215-C046 servo, 7.4 V, 1:147', 'STS3215_C046', 23.98, f"{amz('B0H3TNG1Z6', 'Amazon, MengJie')} (6 left)", 'hip yaw'),
    ('ROBOTIS Dynamixel XC330-M288-T servo', 'XC330_M288', 103.39,
     '[ROBOTIS US](https://robotis.us/products/dynamixel-xc330-m288-t): **sold out** on 2026-11-03, no date given. [RobotShop US](https://www.robotshop.com/products/robotis-dynamixel-xc330-m288-t-smart-servo-actuator): $103.39, one page says re-stocking. RobotShop Canada showed 8 at $147.70. **This is the part that decides when you can build**', 'neck: it carries the head'),
    ('ROBOTIS Dynamixel XL330-M288-T servo', 'XL330_M288', 27.49,
     '[ROBOTIS US](https://robotis.us/products/dynamixel-xl330-m288-t): **sold out** on 2026-11-03, lead time to the end of November. '
     '[Seeed](https://www.seeedstudio.com/Servo-Motor-1-5V-103RPM-Brush-mm-p-6783.html) showed stock at $31.40, limit 2 per account, sold as numbered Reachy Mini servos (No. 1-6, each its own listing, with an arm and a preset ID: set the ID again)', 'head pitch, yaw, roll, beak'),
]
BEARINGS = [
    ('6704ZZ ball bearing, 20 x 27 x 4 mm', '6704ZZ', f"{amz('B082PSB7NH', 'Amazon, uxcell')}: 10 for $18.39",
     'round each STS3215 horn. Check a horn fits the bore before printing'),
    ('MR2216ZZ ball bearing, 16 x 22 x 4 mm', 'MR2216ZZ', f"{amz('B0C5ZCVGNP', 'Amazon, ET2216ZZ')}: 10 for $42.72. Same size, different name. "
     f"{amz('B0HHJFHP8F', 'uxcell')} sells 2 for $8.49, but had 1 pack left and 2 are too few",
     'round the head yaw and roll horns'),
    ('6700ZZ ball bearing, 10 x 15 x 4 mm', '6700ZZ', f"{amz('B0FQ4VYXRP', 'Amazon')}: 10 for $6.79", "in each shoe's inner ear"),
]
HORNS = ('ROBOTIS HNX330-N102 horns, 5 pack', '[ROBOTIS US](https://robotis.us/hnx330-n102-5pcs), [OpenELAB](https://openelab.io/products/dynamixel-hnx330-n102) at 22.90 euro; about $25. Confirm stock',
         '**Was missing: ROBOTIS lists the horn as not included with an XL330 or XC330.** One on each of the 5 servos. Check its size against the 16 mm bearing bore before printing')
PACKS = [
    # the packs that cover the screw table: (what, price USD, where, covers)
    ('M2 self-tapping pan head kit, 800 pieces', 15.66, amz('B0GV338JJK'), 'M2 x 6 and x 8, 100 each. The listing disagrees with itself on stainless or plated steel'),
    ('M3 socket cap kit, 610 pieces, with nuts and washers', 19.99, amz('B09NR8X2LV'), 'M3 x 8, 10, 12, 14. Its count per length is not listed: 32 of the 10 mm are needed'),
    ('M3 x 6 flat head socket screws, 100', 5.99, amz('B01HBN0U76'), 'M3 flat x 6. Head 6 mm wide, 1.7 mm high: check it sits flush'),
    ('M3 aluminium spacers, 3 mm long, 5 mm OD, 10', 6.99, amz('B0CQFF328L'), 'jaw hinges, with a 0.5 mm M3 washer each to make 3.5 mm. No 3.5 mm spacer found. 4 packs left'),
    ('Foam tape, hook-and-loop strap, small cable ties', 12.00, 'any hardware shop', 'the bus boards, IMU and camera on tape, the battery on a strap, the regulators and wires tied'),
]
PRINT = [
    ('ELEGOO PLA+, 1.75 mm, 1 kg', 13.99, amz('B0D41ZDC47'), 'white; other colours on the page'),
    ('OVERTURE TPU 95A, 1.75 mm, 1 kg', 23.99, amz('B0BGMP1MZ7'), 'black. Only 78 g needed: smaller spools exist if your printer handles TPU badly'),
]
ELECTRONICS = [
    # (what, need, price USD, where, note)
    ('Omron D2F-01F microswitch, 4 pack', '2', 6.74, amz('B0062WNDLI'), 'foot switches: solder terminals, 12.8 x 5.8 x 6.5 mm body. Safe to buy now'),
    ('Raspberry Pi Zero 2 W', '1', 17.25, '[PiShop](https://www.pishop.us/product/raspberry-pi-zero-2-w/), limit 1 per order. **Not Amazon: $85 there**', 'in the head'),
    ('microSD card, 32 GB', '1', 21.49, amz('B08L5HMJVW'), 'for the Pi; any A1 card, and cheaper elsewhere'),
    ('Arducam 8 MP IMX219 camera', '1', 16.99, amz('B09V576TFN'), 'includes the Pi Zero cable. Check its board against the 24 x 24 mm box modelled behind the eye'),
    ('BNO085 IMU board', '1', 29.50, '[Adafruit 4754](https://www.adafruit.com/product/4754), in stock on 2026-11-03', 'on the top plate; 25.6 x 22.7 x 4.6 mm, as modelled. Another maker\'s board may differ: check before swapping'),
    ('2S LiPo, 850 mAh, 50C, 54 x 30 x 15 mm, 2 pack', '1', 23.39, amz('B0DGQ6DRLS', 'Amazon, Zeee'), 'fits the slot as modelled. **It comes on a small JST plug, too small for 10 servos: solder on the XT30 below**'),
    ('XT30 connector pairs, with 18 AWG lead', '1', 8.00, 'any RC shop', 'the battery\'s power connector, and its off switch: no switch is designed in, so unplug it'),
    ('2S balance charger', '1', 9.49, amz('B0FDKX4V38'), 'check it matches the pack\'s balance plug'),
    ('5 V 8 A UBEC', '2', 18.98, amz('B07DD9L6P6', 'Amazon, FEICHAO'), '39 x 21 x 6 mm, one in each side pocket: one for the Dynamixels (7.7 A if all 5 stall), one for the Pi and IMU. Set the jumper to 5 V **before** connecting anything'),
    ('Feetech FE-URT-1 bus board', '1', 16.99, amz('B0FRQZQQF3'), 'on the Pi\'s UART, data and ground only: 55.8 x 36.6 x 11.5 mm per its listings, on rails in the head. Also sets IDs on the bench'),
    ('ROBOTIS U2D2', '1', 46.76, '[RobotShop](https://www.robotshop.com/products/robotis-u2d2-usb-to-serial-adapter-for-dynamixel), in stock on 2026-11-03. [ROBOTIS US](https://robotis.us/products/u2d2): sold out, $36.92', 'on the Pi\'s USB: 48 x 18 x 14.6 mm, under the Pi mount in the head. It gives the servos no power'),
    ('Micro USB OTG lead, short', '1', 5.00, 'any shop', 'the Pi to the U2D2'),
    ('3-pin 2.54 mm servo leads (5264), 15 and 30 cm', '12', 1.00, 'search "5264 3 pin 2.54 mm female to female". **No listing confirmed**', 'the Feetech chains. Listings disagree on whether a 15 cm lead comes with each servo. Across a joint, leave slack'),
]
SCREW_USE = {('M2', 6): 'STS3215 cases; XL/XC330 horns; shoe, cover and body screws. Self-tapping',
             ('M2', 8): 'XL/XC330 frame holes, inner ears, horns over a bearing. Self-tapping',
             ('M3 flat', 6): 'ankle rear horn: flat heads, flush under the bearing',
             ('M3', 10): 'STS3215 horns, through the bracket and its boss', ('M3', 8): 'ankle horns, through the outer ear', ('M3', 12): 'soles, from below', ('M3', 14): 'jaw hinges'}


def counts(spec):
    servos, screws = collections.Counter(), collections.Counter()
    bear = collections.Counter()
    for j in spec['joints']:
        servos[j['act']] += 1
        for _ in j.get('bearing', []):
            bear[spec['bearings']['STS3215' if j['act'].startswith('STS') else 'XL330']['part']] += 1
    bear[spec['bearings']['ankle']['part']] = 2
    for l in spec['links'].values():
        for g in l['geoms']:
            if 'fast' in g:
                screws[(g['fast']['size'], round(g['fast']['L'] * 1000))] += 1
    return servos, bear, screws


def bom(spec):
    servos, bear, screws = counts(spec)
    inert = MM.link_inertials(spec)
    ps = [p for v in inert.values() for p in v[3]]
    pla = sum(p[2] for p in ps if p[1] == 'pla')
    tpu = sum(p[2] for p in ps if p[1] == 'tpu')
    total = sum(v[0] for v in inert.values())
    cost = sum(servos[k] * pr for _, k, pr, _, _ in BUY)
    n44 = servos['STS3215_C044']
    cost += max(0, n44 - 7) * (25.99 - 23.98)      # only 7 at the lower price
    bearings = 18.39 + 42.72 + 6.79 + 11.27 + 25.00
    packs = sum(p[1] for p in PACKS)
    fil = sum(p[1] for p in PRINT)
    elec = sum(e[2] * (int(e[1]) if 'pack' not in e[0] else 1) for e in ELECTRONICS)
    L = ['# milli: parts to buy', '',
         'Generated by `tools/make_docs.py` from the spec, so the counts match the model. Amazon US prices and stock as shown on',
         '2026-11-02, signed out, before tax and shipping: **stock is thin, so confirm each part and price before ordering.** Amazon pages refuse AI agents, so its stock was not re-read on 2026-11-03; the other shops were, and on that day the ROBOTIS US shop had the XC330, XL330 and U2D2 sold out: start with those.', '',
         f'Model mass {total:.2f} kg.', '',
         '| Group | About | On Amazon? |', '|---|---|---|',
         f'| Servos | ${cost:.0f} | Feetech yes, Dynamixel no |',
         f'| Bearings and idlers | ${bearings:.0f} | bearings yes, idlers no |',
         f'| Screws and spacers | ${packs:.0f} | yes |',
         f'| Filament | ${fil:.0f} | yes |',
         f'| Electronics | ${elec:.0f} | most, but not the Pi at a fair price |',
         f'| **Total** | **${cost + bearings + packs + fil + elec:.0f}** | |', '',
         '## The plan: salvage an SO-101 pair and a Koch pair', '',
         'Dismantling both arm pairs (standard 7.4 V SO-101 kit, not the 12 V Pro) supplies most of the servos. The tables below are the '
         'full price, for buying everything new.', '',
         '| Joint | Servo | Need | From |', '|---|---|---|---|',
         '| Hip yaw | C046 | 2 | SO-101 leader (3 in it) |',
         '| Knee | C044 | 2 | SO-101 leader (2 in it) |',
         '| Hip roll, hip pitch, ankle | C001 in place of the C044, **or** buy 6 C044 | 6 | SO-101 follower (6 in it) and leader (1) |',
         '| Head pitch, yaw, roll, beak | XL330-M288 | 4 | Koch follower (4 in it) |',
         '| Neck | XC330-M288 | 1 | Buy: nothing in the arms fits |', '',
         f'That is about **${cost + bearings + packs + fil + elec - cost + 103.39 - 16.99:.0f}** with the C001s, or '
         f'**${cost + bearings + packs + fil + elec - cost + 103.39 - 16.99 + 6 * 23.98:.0f}** buying 6 C044s, if an arm\'s bus board replaces the FE-URT-1. '
         '**The C001s are not proven:** they are slower than the walk trained on C044s (5.4 against 9 rad/s no-load), so they have their own training run, '
         '`Mjlab-Velocity-Flat-Milli-Salvage`. Left over: 1 C001, 1 C046, 2 XL430s and 6 XL330-M077s.', '',
         'The arms stop working as teleoperation arms, and these servos are used: check each for backlash and rough gears.', '',
         '## Do this first: a one-joint test', '',
         'Nothing has been printed or measured yet, and each of these answers something that could change the design or the walking',
         'training. Take a C044 from the SO-101 leader, buy the 6704ZZ pack, the M2 and M3 kits and the PLA, and print the knee test in',
         '[prints/README.md](prints/README.md). About $70, using an arm\'s bus board and power supply if it gives 7.4 V.', '',
         '- **What comes in the box.** Every STS3215 needs a horn and the two ankle servos a rear horn as well, and Amazon\'s pages list only "servo". If they are missing, that is 12 more parts to find.',
         '- **The C044\'s real torque.** This listing\'s title says 16 kg.cm (1.57 N m), as does WowRobo; other retailers say 27.4 (2.69 N m), the number the walking training uses. Feetech publishes neither that we could find.',
         '- **Whether the 6704ZZ fits round the horn,** and how the printed joint holds up.', '',
         '## Servos', '',
         '| Have | Part | Need | Each | Where | Used for |', '|---|---|---|---|---|---|']
    for what, k, pr, where, note in BUY:
        L.append(f'| ☐ | {what} | {servos[k]} | ${pr:.2f} | {where} | {note} |')
    L += ['', 'Each Dynamixel comes with a 180 mm cable and its M2 screws (6 x 6 mm, 10 x 8 mm), per ROBOTIS.', '',
          '## Bearings and idlers', '', '| Have | Part | Need | Where | Used for |', '|---|---|---|---|---|']
    for what, k, where, note in BEARINGS:
        L.append(f'| ☐ | {what} | {bear[k]} | {where} | {note} |')
    L += [f'| ☐ | {HORNS[0]} | 1 | {HORNS[1]} | {HORNS[2]} |']
    L += ['| ☐ | ROBOTIS FPX330-H101 4-piece set | 1 | [ROBOTIS US](https://robotis.us/products/fpx330-h101-4pcs-set): $11.27. Not on Amazon | '
          'the idlers and caps for the neck and head pitch. ROBOTIS sells them only in this set, and the servos don\'t include them |']
    L += ['', '## Screws', '', 'Buy packs and keep spares; small screws get lost.', '', '| Have | Size | Need | Used for |', '|---|---|---|---|']
    for (sz, ln), n in sorted(screws.items()):
        L.append(f"| ☐ | {sz} x {ln} mm | {n} | {SCREW_USE.get((sz, ln), '')} |")
    L += ['| ☐ | M3 spacer, 3.5 mm | 2 | jaw hinges: the hinge tabs turn on them |', '', 'These packs cover the table:', '',
          '| Have | Pack | Price | Where | Covers |', '|---|---|---|---|---|']
    for what, pr, where, note in PACKS:
        L.append(f'| ☐ | {what} | ${pr:.2f} | {where} | {note} |')
    L += ['', '## Printed parts', '', f'About {pla * 1000:.0f} g of PLA and {tpu * 1000:.0f} g of TPU 95A, as modelled.', '',
          '| Have | Filament | Price | Where | Note |', '|---|---|---|---|---|']
    for what, pr, where, note in PRINT:
        L.append(f'| ☐ | {what} | ${pr:.2f} | {where} | {note} |')
    L += ['', '| Have | Part | Need | Material |', '|---|---|---|---|']
    seen = collections.Counter()
    for n, k, _ in A.PARTS:
        if k == 'P':
            seen[n[2:] if n[:2] in ('L ', 'R ') else n] += 1
    for n, c in seen.items():
        L.append(f"| ☐ | {n} | {c} | {'TPU 95A' if n in ('sole', 'jaw soft insert', 'mouth roof') else 'PLA'} |")
    L += ['', '## Sensors and electronics', '', 'Each board is modelled at its listed size, in a place checked against everything that moves. Wiring: [docs/WIRING.md](docs/WIRING.md). Still to settle:', '',
          '- **A full 2S pack is 8.4 V.** Waveshare and most sellers rate the 7.4 V STS3215 to 7.4 V; one says 8.4 V. Find out which before connecting a charged battery directly.',
          '- **Avoid the common $12-13 Waveshare servo board** ([this one](https://www.amazon.com/dp/B0CJ6TP3TP)): its input is 9-12.6 V and must match the servos.',
          '- **The Pi:** PiShop\'s page marked it out of stock on 2026-11-03, though nothing on the page said so. Look at other Raspberry Pi resellers if it won\'t add to a cart.', '',
          '| Have | Part | Need | Price | Where | Note |', '|---|---|---|---|---|---|']
    for what, need, pr, where, note in ELECTRONICS:
        L.append(f'| ☐ | {what} | {need} | ${pr:.2f} | {where} | {note} |')
    L += ['', '## Not designed yet', '', '- A power switch: unplug the XT30.', '- Speaker and microphone.', '- Exact cable lengths: measure on the build.', '']
    with open(os.path.join(G.ROOT, 'BOM.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


TITLE = {'jawbench': '10. The jaw and its rod', 'head': '11. The head', 'thigh_L': '1. Thighs', 'shin_L': '2. Shins and ankles', 'shoe_L': '3. Shoes', 'leg_L': '4. Join each leg', 'body': '5. Chassis and hips',
         'legs': '6. Legs onto the hips', 'column': '7. Neck column', 'torso': '8. Neck and body shell', 'headbench': '9. Head yaw and roll'}
WARN = {
    'thigh_L': 'The cable sockets are on each servo\'s rear face, behind a window in the plate. Plug the cables in from outside, before the cover, with room to turn the wires under it.',
    'shin_L': 'The rear-horn screws go in before the bearing: the bearing covers them.',
    'shoe_L': 'Solder the switch wires before pressing the switch in, and try the switch against the sole before printing all four parts: its travel in this TPU is untested.',
    'leg_L': 'The roll bracket goes onto the hip horn here, on the bench: once the leg is on the robot, the roll servo blocks those 4 screws.',
    'body': 'Screw on the yaw brackets **before** the roll servos: the roll servos cover those screws.',
    'column': 'Fit both horns to each servo before it goes in, at mid-range.',
    'torso': 'Do the neck before the body shell: the shell blocks the neck\'s horn screws. Do the shell before the head: the head will not pass through its slot.',
    'headbench': 'The head yaw servo\'s screws under the bridge go in here, on the bench: once this is on the neck, they cannot be reached.',
    'head': 'The roll servo\'s rear horn screws go in before the beak servo, which covers them. The jaw goes in before the hood, for the rod\'s screw. The hinge screws and the 2 at the back hold the hood on, so they are last.',
}


def guide():
    L = ['# How to build milli', '', 'Generated by `tools/make_docs.py` from the order in `tools/assembly.py`. That order is checked: every part can',
         'slide in along the path shown without hitting what is already on, and a key reaches every screw (`python -I tools/assembly.py`).', '',
         f"Watch each animation, then do the same. Parts: [BOM.md]({'../BOM.md' if G.RECIPE == 'hybrid' else 'BOM.md'}). The right side is the mirror of the left, so only the left is shown.", '',
         '> ⚠ marks what has to happen in that order, or cannot be done later.', '',
         '## 0. Before you start', '',
         '1. **Print one joint first** ([prints/README.md](../prints/README.md)), then everything. None of it has been test printed yet.',
         '2. **Set each servo\'s ID on its own**, before any are chained: ' + ('Feetech 1-10, Dynamixel 1-5, on their separate buses' if G.RECIPE == 'hybrid' else 'Dynamixel 1-15') + '. Label each servo.',
         '3. **Move each servo to mid-range** and keep it there: horns go on at mid-range, or the joint\'s range will be off-centre.',
         '4. **The pockets are cut 0.3 mm over the servos and 0.1 mm over the bearings.** If yours print tight or loose, change that once in tools/export_prints.py.', '',
         'Tools: 1.5 and 2 mm hex or small Phillips drivers, soldering iron (a grown-up, if you are young), threadlock for screws into metal.', '']
    for sec in A.sections_for(A.Build(G.load())):
        k = sec['key']
        if k not in TITLE:
            continue
        L += [f'## {TITLE[k]}', '', f"![{TITLE[k]}]({'images/assembly' if G.RECIPE == 'hybrid' else f'../images/assembly/{G.RECIPE}'}/{k}.gif)", '']
        if k in WARN and not (G.RECIPE != 'hybrid' and k == 'thigh_L'):
            L += [f'> ⚠ {WARN[k]}', '']
        elif k == 'thigh_L':
            L += ['> ⚠ The cable sockets are in notches at the edges of each servo\'s rear face. Plug the cables in through the windows in the thigh plate, before the cover.', '']
        for i, (cap, _, _) in enumerate(sec['steps'], 1):
            L.append(f'{i}. {cap}')
        if k.endswith('_L'):
            L += ['', 'Then the same for the right side, mirrored.']
        L.append('')
    L += ['## Wires', '', 'See [WIRING.md](WIRING.md). **Tie the ankle\'s wires up against its rail:** the shoe\'s ear passes close by them past 1 rad.', '']
    os.makedirs(G.out_path('docs'), exist_ok=True)
    with open(G.out_path('docs', 'ASSEMBLY.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


def bom_dynamixel(spec):
    """The all-Dynamixel variant's parts: its own list, as it shares few of the first variant's."""
    servos, bear, screws = counts(spec)
    inert = MM.link_inertials(spec)
    ps = [p for v in inert.values() for p in v[3]]
    pla, tpu = sum(p[2] for p in ps if p[1] == 'pla'), sum(p[2] for p in ps if p[1] == 'tpu')
    total = sum(v[0] for v in inert.values())
    n = servos['XL330_M288']
    L = ['# All-Dynamixel duck: parts to buy', '', 'Generated by `tools/make_docs.py` from the spec, so the counts match the model. Shops re-read on 2026-11-03; Amazon pages refuse AI agents, so those are as read on 2026-11-02. **Confirm each before ordering.**', '',
         f'Model mass {total:.2f} kg, 0.295 m tall. Nothing has been printed: print one joint first.', '',
         '## Servos: the real constraint', '',
         f'**{n} XL330-M288-T.** ROBOTIS US: [sold out](https://robotis.us/products/dynamixel-xl330-m288-t), lead time to the end of November, $27.49. '
         '[Seeed](https://www.seeedstudio.com/Servo-Motor-1-5V-103RPM-Brush-mm-p-6783.html): $31.40, limit 2 per account, sold as numbered Reachy Mini servos (No. 1-6, each its own listing, with an arm and a preset ID: set the ID again).', '',
         '| From a Koch arm pair | Count | Use |', '|---|---|---|',
         '| XL330-M288-T (follower) | 4 | the right servo: 4 of the 15 |', '| XL330-M077-T (leader) | 6 | same case, so it fits, but about a third of the torque: no walking joint. Check any use with its own numbers. Possibly the beak |',
         '| XL430 (follower) | 2 | a bigger case: does not fit |', '',
         'What 4 M288s can build now: the neck and head (5 joints, with an M077 on the beak), or one leg. Either tests the fit, connectors and screws on real parts.', '',
         '**They run past their rating:** on a 2S pack straight, as Microduck\'s trainer models its own (6.5-8.2 V), against ROBOTIS\'s 6 V maximum. Expect a shorter life than ROBOTIS rates. A 5 V supply would be within rating, but the walks here were trained at 2S.', '',
         '## Horns, idlers, bearings', '', '| Have | Part | Need | Where | Used for |', '|---|---|---|---|---|',
         f'| ☐ | ROBOTIS HNX330-N102 horns, 5 pack | {-(-n // 5)} packs | [ROBOTIS US](https://robotis.us/hnx330-n102-5pcs), [OpenELAB](https://openelab.io/products/dynamixel-hnx330-n102) | **ROBOTIS lists the horn as not included.** One per servo. Your Koch servos may still have theirs |',
         f"| ☐ | MR2216ZZ bearing, 16 x 22 x 4 mm | {bear['MR2216ZZ']} | {amz('B0C5ZCVGNP', 'Amazon, ET2216ZZ')}: 10 for $42.72, so 2 packs | round each horn. Check a horn fits the bore before printing |",
         f"| ☐ | 6700ZZ bearing, 10 x 15 x 4 mm | {bear['6700ZZ']} | {amz('B0FQ4VYXRP')}: 10 for $6.79 | each shoe's inner ear |",
         '| ☐ | ROBOTIS FPX330-H101 set | 1 | [ROBOTIS US](https://robotis.us/fpx330-h101-4pcs-set/): $11.27 | idlers for the neck, head pitch and head roll |', '',
         '## Screws', '', 'Each Dynamixel comes with its M2 screws (6 x 6 mm, 10 x 8 mm), per ROBOTIS, so most of these you have, if you kept them.', '', '| Have | Size | Need |', '|---|---|---|']
    for (sz, ln), c in sorted(screws.items()):
        L.append(f'| ☐ | {sz} x {ln} mm | {c} |')
    L += ['| ☐ | M3 spacer, 3.5 mm | 2: a 3 mm spacer and a 0.5 mm washer |', '', 'Packs: see [the hybrid list](../../BOM.md). Also foam tape, a hook-and-loop strap, small cable ties.', '',
          '## Printed parts', '', f'About {pla * 1000:.0f} g of PLA and {tpu * 1000:.0f} g of TPU 95A, as modelled. STLs: [prints/dynamixel/](../../prints/dynamixel/README.md).', '',
          '## Electronics', '', 'One bus, so one board. Sizes are from listings, in places checked against everything that moves.', '',
          '| Have | Part | Need | Where | Note |', '|---|---|---|---|---|',
          '| ☐ | Raspberry Pi Zero 2 W | 1 | [PiShop](https://www.pishop.us/product/raspberry-pi-zero-2-w/): its page marked it out of stock on 2026-11-03. Look at other resellers | in the head |',
          '| ☐ | ROBOTIS U2D2 | 1 | [RobotShop](https://www.robotshop.com/products/robotis-u2d2-usb-to-serial-adapter-for-dynamixel): $46.76, in stock on 2026-11-03. [ROBOTIS US](https://robotis.us/products/u2d2): sold out. **The Koch arm has one or two already** | on the Pi\'s USB, flat under the Pi\'s mount. It gives the servos no power |',
          '| ☐ | 2S LiPo, 450 mAh, 60C, 43 x 23 x 13 mm, XT30 | 1 | Gens Ace GEA4502S60XT3: [listing](https://www.rccarshop.co.uk/GEA4502S60XT3-GENSACE-ADVENTURE-LIPO-2S-7-4V-450-60C-XT30-43X23X13MM-28G), a UK shop whose page may mean out of stock. Any pack this size or smaller | in its slot, on a strap |',
          f"| ☐ | 5 V 8 A UBEC | 1 | {amz('B07DD9L6P6', 'Amazon, FEICHAO')}, $18.98 | 39 x 21 x 6 mm, taped to the battery's back: the Pi and IMU. **Set its jumper to 5 V and measure first** |",
          '| ☐ | BNO085 IMU board | 1 | [Adafruit 4754](https://www.adafruit.com/product/4754), $29.50, in stock on 2026-11-03 | on the top plate |',
          f"| ☐ | Arducam 8 MP IMX219 camera | 1 | {amz('B09V576TFN')}, $16.99 | on the back of the face. Check its board against the 24 x 24 mm modelled |",
          f"| ☐ | Omron D2F-01F microswitch, 4 pack | 1 | {amz('B0062WNDLI')}, $6.74 | foot switches. Travel against this TPU is untested |",
          f"| ☐ | microSD card, 2S charger, short micro USB OTG lead | 1 each | {amz('B08L5HMJVW', 'card')}, {amz('B0FDKX4V38', 'charger')} | check the charger matches the pack's balance plug |", '',
          'Each servo comes with a 180 mm lead. Across a joint, leave slack.', '',
          '## Not designed yet', '', '- A power switch: unplug the XT30.', '- Speaker and microphone.', '- Exact cable lengths: measure on the build.', '']
    folder = G.out_path('docs')
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, 'BOM.md'), 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    s = G.load()
    if G.RECIPE == 'dynamixel':
        bom_dynamixel(s)
        guide()
        print('docs/dynamixel/BOM.md, ASSEMBLY.md')
    else:
        bom(s)
        guide()
        print('BOM.md, docs/ASSEMBLY.md')
