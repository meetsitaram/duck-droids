"""BOM.md and docs/ASSEMBLY.md, from the parts and the order in tools/assembly.py, so the counts cannot drift from the spec.

  python -I tools/make_docs.py

Links, prices and stock were read from the listings on 2026-11-02: confirm before ordering.
"""
import json
import collections
import os
import re
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
PACKS = [
    # the packs that cover the screw table: (what, price USD, where, covers)
    ('M2 self-tapping pan head kit, 800 pieces', 15.66, amz('B0GV338JJK'), 'M2 x 6 and x 8, 100 each. The listing disagrees with itself on stainless or plated steel'),
    ('M3 socket cap kit, 610 pieces, with nuts and washers', 19.99, amz('B09NR8X2LV'), 'M3 x 8, 10, 12, 14. Its count per length is not listed: 32 of the 10 mm are needed'),
    ('M3 x 6 flat head socket screws, 100', 5.99, amz('B01HBN0U76'), 'M3 flat x 6. Head 6 mm wide, 1.7 mm high: check it sits flush'),
    ('M3 washers, 0.5 mm thick, a few', 2.00, 'any hardware shop; the price is a guess', 'jaw hinges, one each side (it was a 3.5 mm spacer until the hinge tab came in against the hood). No 3.5 mm spacer found. 4 packs left'),
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
WIRES_NOTE = {
    'thigh_L': 'Each thigh servo has 2 sockets, wired through. A lead from the knee to the hip pitch, and one out of the hip pitch toward the roll servo. Plug them in now: the plate covers the sockets.',
    'shin_L': 'The ankle is the end of its leg\'s chain: one lead up to the knee. Leave slack across the knee and tie it to the rail.',
    'body': 'One lead from each hip yaw servo to the body, and one on to its roll servo, before each servo goes in.',
    'legs': 'Plug the leg\'s lead into the roll servo as it comes on, with slack for the hip\'s whole range.',
    'column': 'A lead between the two neck servos, and one down toward the body, with slack for the neck\'s range.',
    'headbench': 'A lead between the yaw and roll servos, with slack for the yaw\'s range of +/- 2.5 rad: it winds round.',
    'framebench': 'The beak servo is the end of the head\'s chain: one lead, plugged in before it goes in.',
    'head': 'The bus board\'s 2 sockets feed the head chain and the legs. Plug in its leads, and the right-angle USB-C lead to the Pi, before the board goes on.',
}


WIRES_HYBRID = {
    'thigh_L': 'Each thigh servo has 2 sockets, wired through. A lead from the knee to the hip pitch, and one out of the hip pitch toward the roll servo. Plug them in now: the plate covers the sockets.',
    'shin_L': 'The ankle is the end of its leg\'s chain: one lead up to the knee. Leave slack across the knee and tie it to the rail.',
    'body': 'One lead from each hip yaw servo up through the top plate, and one on to its roll servo, before each servo goes in.',
    'legs': 'Plug the leg\'s lead into the roll servo as it comes on, with slack for the hip\'s whole range.',
    'torso': 'Before the shell: the battery\'s XT30 tail into the UBEC\'s input, the legs\' splice, and the 2S pair for the neck; 5 V pair from the UBEC. Then the IMU\'s 4 wires. Everything for the head comes out of the shell\'s neck slot. The XT30 and balance plug sit in the port at the back. See WIRING.md.',
    'column': 'A lead between the two neck servos, with slack for the neck\'s range. The neck servo is the end of the head\'s chain.',
    'headbench': 'A lead between the yaw and roll servos, with slack for the yaw\'s range of +/- 2.5 rad: it winds round. One on from the yaw to the head pitch.',
    'framebench': 'One lead on the beak servo, plugged in before it goes in.',
    'head': 'Dynamixel board: its USB-C lead, socket 1 to the beak servo, and the 5 V pair, before it goes on. Feetech board: the neck lead, the 3 UART wires and the 2S pair, before it goes on. Solder the Pi\'s 7 wires first: they are out of reach once it is on its plate.',
}


def driver(sz):
    return {'M2': 'small Phillips', 'M2.5': 'small Phillips', 'M2 flat': 'small Phillips', 'M3': '2.5 mm hex', 'M3 flat': '2 mm hex'}.get(sz, 'driver')


SCREW_USE = {('M2.5', 5): 'the bus board, into its brass standoffs. Kept with the board, if yours came with them',
             ('M2', 6): 'STS3215 cases; XL/XC330 horns; shoe, cover and body screws. Self-tapping',
             ('M2', 8): 'XL/XC330 frame holes, inner ears, horns over a bearing. Self-tapping',
             ('M3 flat', 6): 'ankle rear horn: flat heads, flush under the bearing', ('M2 flat', 5): 'ankle idler: flat heads, flush under the bearing',
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
    bearings = 18.39 + 42.72 + 6.79 + 11.27
    packs = sum(p[1] for p in PACKS)
    fil = sum(p[1] for p in PRINT)
    elec = sum(e[2] * (int(e[1]) if 'pack' not in e[0] else 1) for e in ELECTRONICS)
    L = ['# milli: parts to buy', '', 'This is the hybrid duck. The all-Dynamixel duck has [its own list](docs/dynamixel/BOM.md).', '',
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
    L += ['| ☐ | ROBOTIS FPX330-H101 4-piece set | 1 | [ROBOTIS US](https://robotis.us/products/fpx330-h101-4pcs-set): $11.27. Not on Amazon | '
          'the idlers and caps for the neck and head pitch. ROBOTIS sells them only in this set, and the servos don\'t include them |']
    L += ['', '## Screws', '', 'Buy packs and keep spares; small screws get lost.', '', '| Have | Size | Need | Used for |', '|---|---|---|---|']
    for (sz, ln), n in sorted(screws.items()):
        L.append(f"| ☐ | {sz} x {ln} mm | {n} | {SCREW_USE.get((sz, ln), '')} |")
    L += ['| ☐ | M3 washer, 0.5 mm | 1 | the far hinge of the jaw: its tab turns on it |', '', 'These packs cover the table:', '',
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


TITLE = {'framebench': '9b. The head frame and the beak servo', 'jawbench': '10. The jaw', 'head': '11. The head', 'thigh_L': '1. Thighs', 'shin_L': '2. Shins and ankles', 'shoe_L': '3. Shoes', 'leg_L': '4. Join each leg', 'body': '5. Chassis and hips',
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
    'head': 'The beak servo goes into the head frame first, on the bench: the roll servo blocks its screws afterwards. The jaw goes in before the hood. The far hinge screw and the 2 at the back hold the hood on, so they are last.',
}


def guide():
    FILMED = {'dynamixel': '../images/assembly/dynamixel', 'hybrid': 'images/assembly/hybrid'}.get(G.RECIPE)      # (hybrid's guide is at docs/, others' at docs/<recipe>/)
    if G.RECIPE == 'hybrid' and not os.path.exists(os.path.join(G.ROOT, 'docs', 'images', 'assembly', 'hybrid', 'build_5min.mp4')):
        FILMED = None                              # (its video is filmed from Fusion's bodies. Until then, no pictures: the older GIFs show an older duck)
    L = ['# How to build the hybrid duck' if G.RECIPE == 'hybrid' else '# How to build the all-Dynamixel duck', '', 'Generated by `tools/make_docs.py` from the order in `tools/assembly.py`. That order is checked: every part can',
         'slide in along the path shown without hitting what is already on, and a key reaches every screw (`python -I tools/assembly.py`).', '',
         (f'See it whole first: ' + (f'[the 30-second reveal]({FILMED}/reveal_30s.mp4) and ' if os.path.exists(os.path.join(G.ROOT, 'docs', 'images', 'assembly', G.RECIPE, 'reveal_30s.mp4')) else '') + f'[the 5-minute build]({FILMED}/build_5min.mp4). ' if FILMED else '') + ("Each section's clip names the parts and screws as they come in; the steps below it say what to do. The GIFs run at 1.5 times speed. " if FILMED else '' if G.RECIPE == 'hybrid' else f"Watch each animation, then do the same. ") + f" Parts: [BOM.md]({'../BOM.md' if G.RECIPE == 'hybrid' else 'BOM.md'}). The right side is the mirror of the left, so only the left is shown.", '',
         '> ⚠ marks what has to happen in that order, or cannot be done later.', '',
         '## 0. Before you start', '',
         '1. **Print one joint first** ([prints/README.md](../prints/README.md)), then everything. None of it has been test printed yet.',
         '2. **Set each servo\'s ID on its own**, before any are chained: ' + ('Feetech 1-10, Dynamixel 1-5, on their separate buses' if G.RECIPE == 'hybrid' else 'Dynamixel 1-15') + '. Label each servo.',
         '3. **Move each servo to mid-range** and keep it there: horns go on at mid-range, or the joint\'s range will be off-centre.',
         '4. **The pockets are cut 0.3 mm over the servos and 0.1 mm over the bearings.** If yours print tight or loose, change that once in tools/export_prints.py.', '',
         'Tools: a small Phillips driver, 2 and 2.5 mm hex keys, soldering iron (a grown-up, if you are young), threadlock for screws into metal. Self-tapping screws into plastic: stop when snug, as they strip.', '']
    B_ = A.Build(G.load())
    for sec in A.sections_for(B_):
        k = sec['key']
        if k not in TITLE:
            continue
        if FILMED:            # clips from the build video: tools/cut_clips.py
            L += [f'## {TITLE[k]}', '', f'![{TITLE[k]}]({FILMED}/clips/{k}.gif)', '', f'[Sharper, with controls (MP4)]({FILMED}/clips/{k}.mp4)', '']
        elif G.RECIPE == 'hybrid':
            L += [f'## {TITLE[k]}', '']
        else:
            L += [f'## {TITLE[k]}', '', f"![{TITLE[k]}]({'images/assembly' if G.RECIPE == 'hybrid' else f'../images/assembly/{G.RECIPE}'}/{k}.gif)", '']
        if k in WARN and not (G.RECIPE != 'hybrid' and k == 'thigh_L') and not ((FILMED or G.RECIPE == 'hybrid') and k == 'shoe_L'):
            L += [f'> ⚠ {WARN[k]}', '']
        elif k == 'thigh_L':
            L += ['> ⚠ The cable sockets are in notches at the edges of each servo\'s rear face. Plug the cables in through the windows in the thigh plate, before the cover.', '']
        if k in WIRES_NOTE and G.RECIPE != 'hybrid':
            L += [f'> 🔌 {WIRES_NOTE[k]}', '']
        if k in WIRES_HYBRID and G.RECIPE == 'hybrid':
            L += [f'> 🔌 {WIRES_HYBRID[k]}', '']
        need, total = [], collections.Counter()
        for cap, items, pats in sec['steps']:
            names = [n for n in B_.screws if any(re.search(p_, n) for p_ in pats)]
            for n in names:
                f_ = B_.screws[n][1]['fast']
                total[(f_['size'], round(f_['L'] * 1000))] += 1
        if total:
            L += ['**Screws for this section:** ' + ', '.join(f'{c} x {sz} x {ln} mm' for (sz, ln), c in sorted(total.items())) + (' (each side)' if k.endswith('_L') else ''), '']
        for i, (cap, _, pats) in enumerate(sec['steps'], 1):
            here = collections.Counter()
            for n in B_.screws:
                if any(re.search(p_, n) for p_ in pats):
                    f_ = B_.screws[n][1]['fast']
                    here[(f_['size'], round(f_['L'] * 1000))] += 1
            how = '; '.join(f'{c} x {sz} x {ln} mm, {driver(sz)}' for (sz, ln), c in sorted(here.items()))
            L.append(f'{i}. {cap}' + (f' *({how})*' if how else ''))
        if k.endswith('_L'):
            L += ['', 'Then the same for the right side, mirrored.']
        L.append('')
    if FILMED:
        L += ['## 12. Try every joint', '', f'![Try every joint]({FILMED}/clips/finished.gif)', '', f'[Sharper, with controls (MP4)]({FILMED}/clips/finished.mp4)', '', 'Move each joint by hand, slowly, through its range, with the power off. Nothing should catch or bind.', '']
    L += ['## Wires', '', 'See [WIRING.md](WIRING.md). **Tie the ankle\'s wires up against its rail:** the shoe\'s ear passes close by them past 1 rad.', '']
    os.makedirs(G.out_path('docs'), exist_ok=True)
    with open(G.out_path('docs', 'ASSEMBLY.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


def bom_dynamixel(spec):
    """The all-Dynamixel variant's bill of materials, written for someone building it to order: every purchased and fabricated part, one table each, nice-to-haves marked Optional and left out of the total."""
    servos, bear, screws = counts(spec)
    inert = MM.link_inertials(spec)
    ps = [p for v in inert.values() for p in v[3]]
    pla, tpu = sum(p[2] for p in ps if p[1] == 'pla'), sum(p[2] for p in ps if p[1] == 'tpu')
    total = sum(v[0] for v in inert.values())
    n = servos['XL330_M288']
    per_servo = {('M2', 6): 6, ('M2', 8): 10}                 # the screws in each servo's box, per ROBOTIS
    for k, each in per_servo.items():
        assert n * each >= screws[k], k

    def sc(size, ln):
        return screws[(size, ln)]

    def link(label, url):
        return f'[{label}]({url})'

    # (key, part, maker and part number, specification, quantity per robot, what is ordered, how many, price each or None, source, Required / Optional)
    GROUPS = [
        ('Actuators', [
            ('servo', 'Smart servo', 'ROBOTIS XL330-M288-T', '0.52 N m stall and 103 rev/min at 5 V, 288.4:1, 18 g, model number 1200', n, 'each', n, 27.49,
             link('ROBOTIS US', 'https://robotis.us/products/dynamixel-xl330-m288-t') + ': sold out, lead time to end of November. Second source ' + link('Seeed', 'https://www.seeedstudio.com/Servo-Motor-1-5V-103RPM-Brush-mm-p-6783.html') + ' at $31.40, limit 2 per account', 'Required'),
            ('m077', 'Jaw servo, softer alternate', 'ROBOTIS XL330-M077-T', '0.215 N m stall and 383 rev/min at 5 V, 77.5:1, 18 g, model number 1190. Same pocket, horn and screws. Replaces 1 of the M288s', 1, 'each', 1, None, 'ROBOTIS', 'Optional'),
        ]),
        ('Bearings and idlers', [
            ('mr2216', 'Ball bearing, around each horn', 'MR2216ZZ (ET2216ZZ)', '16 x 22 x 4 mm', bear['MR2216ZZ'], 'pack of 10', 2, 42.72, amz('B0C5ZCVGNP'), 'Required'),
            ('b6700', 'Ball bearing, shoe inner ear', '6700ZZ', '10 x 15 x 4 mm', bear['6700ZZ'], 'pack of 10', 1, 6.79, amz('B0FQ4VYXRP'), 'Required'),
            ('idler', 'Idler: neck, head pitch, head roll, both ankles', 'ROBOTIS FPX330-H101', 'set of 4', 5, 'set of 4', 2, 11.27, link('ROBOTIS US', 'https://robotis.us/fpx330-h101-4pcs-set/'), 'Required'),
        ]),
        ('Fasteners', [
            ('m2x6', 'Screw, servo mounting', 'generic', 'M2 x 6 mm', sc('M2', 6), 'in the servo box', 0, None, f'{n * per_servo[("M2", 6)]} come with the servos', 'Required'),
            ('m2x8', 'Screw, servo mounting', 'generic', 'M2 x 8 mm', sc('M2', 8), 'in the servo box', 0, None, f'{n * per_servo[("M2", 8)]} come with the servos', 'Required'),
            ('m2f', 'Screw, flat head, machine thread', 'generic', 'M2 x 5 mm, Phillips, black oxide 304 stainless', sc('M2 flat', 5), 'pack of 50', 1, None, amz('B0H5JXD9YQ'), 'Required'),
            ('m25', 'Screw, bus board, machine thread', 'generic', 'M2.5 x 5 mm, pan head, Phillips, black oxide 304 stainless', sc('M2.5', 5), 'pack of 50', 1, None, 'Amazon', 'Required'),
            ('so', 'Spare hex standoffs, bus board: 4 come with the Waveshare board', 'uxcell', 'brass, M2.5, female-female, 8 mm long, 5 mm across flats', 0, 'pack of 50', 1, None, 'Amazon', 'Optional'),
            ('m3kit', 'Screws, socket cap: 1 x M3 x 10, 4 x M3 x 12', 'generic', 'kit of 610 with nuts and washers', sc('M3', 10) + sc('M3', 12), 'kit', 1, 19.99, amz('B09NR8X2LV'), 'Required'),
            ('wash', 'Washer, far hinge tab to hood', 'uxcell', 'M3, 6 mm outside, 0.5 mm thick, stainless', 1, 'pack of 100', 1, None, amz('B015A39NCC'), 'Required'),
            ('m2kit', 'Spare M2 screws', 'generic', 'self-tapping pan head kit, 800 pieces', 0, 'kit', 1, 15.66, amz('B0GV338JJK'), 'Optional'),
        ]),
        ('Electronics', [
            ('pi', 'Computer', 'Raspberry Pi Zero 2 W', 'without header', 1, 'each', 1, None, link('PiShop', 'https://www.pishop.us/product/raspberry-pi-zero-2-w/') + ': out of stock on 2026-11-03', 'Required'),
            ('sd', 'microSD card', 'SanDisk Ultra', '32 GB microSDHC, A1, Class 10, UHS-I', 1, 'each', 1, None, amz('B08L5HMJVW'), 'Required'),
            ('board', 'Servo bus board', 'Waveshare Bus Servo Adapter (A), SKU 25514', 'USB-C, 2 servo sockets, also sold as Serial Bus Servo Driver Board', 1, 'each', 1, None, amz('B0CTMM4LWK') + '. Second source ' + link('Abra', 'https://abra-electronics.com/electromechanical/motors/motor-controllers/wave-25514-serial-bus-servo-driver-board.html') + ' at $9.05', 'Required'),
            ('reg', '5 V regulator', 'hiBCTR USB buck converter QC3.0', '6-32 V in, 35 x 17 x 8.5 mm', 1, 'pack of 2', 1, 7.97, 'Amazon', 'Required'),
            ('imu', 'IMU', 'BNO085 module, EC Buying', 'modelled at 25.6 x 22.7 x 4.6 mm; I2C', 1, 'each', 1, None, amz('B0CDGZMLPP') + '. Second source ' + link('Adafruit 4754', 'https://www.adafruit.com/product/4754') + ' at $29.50, in stock on 2026-11-03', 'Required'),
            ('cam', 'Camera', 'Arducam 8 MP IMX219', 'board modelled at 24 x 24 mm', 1, 'each', 1, 16.99, amz('B09V576TFN'), 'Optional'),
            ('ribbon', 'Camera ribbon, if the camera lacks one', 'GODIYMODULES', 'Pi Zero 22-pin to 15-pin, 15 cm', 1, 'pack of 2', 1, None, amz('B0F9WJ62LV'), 'Optional'),
        ]),
        ('Power and wiring', [
            ('batt', 'Battery', 'OVONIC 2S LiPo, 100C', '450 mAh, XT30, 61.5 x 15.8 x 13.5 mm, 31 g', 1, 'pack of 4', 1, 26.39, amz('B0D2KT723L'), 'Required'),
            ('xt30', 'Battery connector', 'Nuofany XT30 pigtail', '100 mm, 16 AWG', 1, '5 pairs', 1, 9.99, amz('B0B4H4GKQL'), 'Required'),
            ('wire', 'Power wire, red and black', 'BNTECHGO silicone wire', '20 AWG', 1, '10 ft each', 1, None, amz('B01M12PSJM'), 'Required'),
            ('thin', 'Signal wire: IMU', 'Fermerry silicone wire', '28 AWG stranded, 4 wires, about 1 m in all', 1, '6 colours, 5 ft each', 1, None, amz('B089CR4SDM'), 'Required'),
            ('long', 'Servo cable: socket 2 to right leg, neck servo to left leg', 'ROBOTIS Robot Cable-X3P or equivalent', 'JST EH 3-pin both ends, 300-400 mm', 2, 'each', 2, None, 'no source chosen: the 300 mm found is listed with a Molex plug', 'Required'),
            ('usb', 'Regulator to Pi power', 'LY tech flat ribbon USB', 'right-angle USB-A to right-angle micro USB, 10 cm', 1, 'each', 1, 13.50, 'Amazon', 'Required'),
            ('otg', 'Pi to bus board', 'Veeloon', 'right-angle micro USB OTG to right-angle USB-C, 0.6 ft', 1, 'pack of 2', 1, 7.99, amz('B0DKBQ7TD3'), 'Required'),
        ]),
        ('Consumables', [
            ('fix', 'Foam tape, hook-and-loop strap, small cable ties', 'generic', '', 1, 'lot', 1, 12.00, 'any hardware shop; price estimated', 'Required'),
            ('joint', 'Solder, heat-shrink tube, CA glue', 'generic', '', 1, 'lot', 1, None, 'any hardware shop', 'Required'),
        ]),
        ('Support equipment (not in the robot)', [
            ('chg', 'Charger', 'as linked', '2S LiPo, to 8.4 V, must match the balance plug', 1, 'each', 1, None, amz('B0FDKX4V38'), 'Required'),
        ]),
    ]
    num, k = {}, 0
    for _, rows in GROUPS:
        for r in rows:
            k += 1
            num[r[0]] = k

    SEARCH = {'servo': 'Dynamixel XL330-M288-T', 'm077': 'Dynamixel XL330-M077-T', 'mr2216': 'MR2216ZZ bearing 16x22x4mm', 'b6700': '6700ZZ bearing 10x15x4mm', 'idler': 'Dynamixel FPX330-H101 idler',
              'm2x6': 'M2 x 6mm self tapping pan head screw', 'm2x8': 'M2 x 8mm self tapping pan head screw', 'm2f': 'M2 x 5mm flat head phillips machine screw', 'm25': 'M2.5 x 5mm pan head machine screw black oxide',
              'so': 'uxcell M2.5 x 8mm female female hex brass standoff', 'm3kit': 'M3 socket cap screw kit', 'wash': 'uxcell M3 x 6mm x 0.5mm flat washer', 'm2kit': 'M2 self tapping pan head screw kit',
              'pi': 'Raspberry Pi Zero 2 W', 'sd': 'SanDisk 32GB Ultra microSDHC A1', 'board': 'Waveshare Serial Bus Servo Driver Board', 'reg': 'hiBCTR USB buck converter QC3.0', 'imu': 'BNO085 IMU module',
              'cam': 'Arducam 8MP IMX219 camera module', 'ribbon': 'Raspberry Pi Zero camera cable 22 pin to 15 pin 15cm', 'batt': 'OVONIC 2S 450mAh 100C XT30', 'xt30': 'XT30 pigtail 16 AWG 100mm', 'wire': '20 AWG silicone wire red black',
              'thin': '28 AWG silicone stranded wire', 'long': 'JST EH 2.5mm 3 pin cable double ended 300mm', 'usb': 'LY tech flat ribbon micro USB 90 degree', 'otg': 'micro USB to USB C OTG cable 90 degree',
              'fix': 'foam tape hook and loop strap cable ties', 'joint': 'solder heat shrink CA glue', 'chg': '2S LiPo balance charger JST-XH'}

    def search(key):
        return f"[Search Amazon](https://www.amazon.com/s?k={SEARCH[key].replace(' ', '+')})"

    def money(v):
        return f'${v:,.2f}'
    tot, opt, unpriced, summary, T = 0.0, 0.0, 0, [], []
    for g, rows in GROUPS:
        T += [f'### {g}', '', '| Item | Part | Maker / part number | Specification | Qty per robot | Order unit | Order qty | Unit price | Line price | Source |', '|---|---|---|---|---|---|---|---|---|---|']
        sub = 0.0
        for key, part, mpn, spec_, q, unit, oq, price, src, st in rows:
            line = None if price is None else oq * price
            if st == 'Required':
                if line is not None:
                    sub += line
                elif oq:
                    unpriced += 1
            elif line is not None:
                opt += line
            o = st == 'Optional'
            T.append(f"| {num[key]} | {'**OPTIONAL:** ' if o else ''}{part} | {mpn} | {spec_} | {(f'({q})' if o else q) if q else '-'} | {unit} | {(f'({oq})' if o else oq) if oq else '-'} | {money(price) if price else '-'} | {money(line) if line else '-'} | {src}<br>{search(key)} |")
        T.append('')
        tot += sub
        summary.append(f'| {g} | {money(sub) if sub else "-"} |')
    # fabricated parts: from the spec, left and right together, each with its print file
    parts = json.load(open(G.parts_path(), encoding='utf-8'))['parts']
    COL = {'#3A3D42': 'Dark grey', '#E8642A': 'Orange', '#ECEBE6': 'White', '#9A9C98': 'Mid grey', '#F0A030': 'Amber', '#0A1420': 'Black', '#F2B233': 'Yellow', '#F7AE55': 'Pale orange'}
    total_v = {m: sum(q['volume_cm3'] for q in parts.values() if q['material'] == m) for m in ('pla', 'tpu')}

    def grams(q):
        return (pla if q['material'] == 'pla' else tpu) * 1000 * q['volume_cm3'] / total_v[q['material']]
    F, vol, j = [], {}, 0
    for name, q in parts.items():
        kk = (q['material'], q['color'])
        vol[kk] = vol.get(kk, 0) + grams(q)
        if name.startswith('R '):
            continue
        j += 1
        fn = name.replace(' ', '_') + '.stl'
        two = name.startswith('L ')
        assert os.path.exists(os.path.join(G.out_path('prints'), fn)), fn
        if two:
            assert 'R ' + name[2:] in parts, name
        shown = name[2:].capitalize() + ', left and right' if two else name.capitalize()
        files = f"`{fn}`, `R_{fn[2:]}`" if two else f'`{fn}`'
        F.append(f"| P{j} | {shown} | {files} | {'PLA' if q['material'] == 'pla' else 'TPU 95A'} | {COL.get(q['color'], q['color'])} | {q['color']} | {grams(q):.1f} g | {2 if two else 1} |")
    fil = [f"| {COL.get(c, c)} | {c} | {'PLA' if m == 'pla' else 'TPU 95A'} | {g_:.0f} g | {g_ * 1.15:.0f} g |" for (m, c), g_ in sorted(vol.items(), key=lambda x: (x[0][0], -x[1]))]
    L = ['# All-Dynamixel duck: bill of materials', '',
         '| | |', '|---|---|',
         '| Product | All-Dynamixel duck, biped, 15 servos |',
         f'| Height, mass | 0.295 m, {total:.2f} kg as modelled |',
         '| Build quantity | Quantities are for 1 robot |',
         f'| Fabricated parts | {len(parts)} printed parts, {pla * 1000:.0f} g PLA and {tpu * 1000:.0f} g TPU 95A |',
         '| Status | Prototype: no unit built, no part test printed |',
         '| Prices | USD, as listed 2026-11-02 to 2026-11-04, before tax and shipping. Confirm before ordering |',
         '| Related | [Print files](../../prints/dynamixel/README.md), [wiring](WIRING.md), [assembly](ASSEMBLY.md) |', '',
         'Generated by `tools/make_docs.py` from the spec. Quantities match the model.', '',
         '## Cost summary', '', '| Group | Required parts, priced |', '|---|---|', *summary,
         f'| **Total of quoted lines** | **{money(tot)}** |', '',
         f'{unpriced} required lines have no quote yet and are not in the total, nor is filament. Optional parts add {money(opt)} on the quoted lines.', '',
         '## Purchased parts', '', 'Every line is required unless it starts with **OPTIONAL**. Optional lines show their quantities in brackets and are not in the total.', '', *T,
         '## Fabricated parts', '', 'All 3D printed. Files are in [prints/dynamixel/](../../prints/dynamixel/README.md), already oriented for printing, in millimetres. Mass is each piece. The hood has an orange band, painted or split in the slicer.', '',
         '| Item | Part | File | Material | Colour | Hex | Mass each | Qty per robot |', '|---|---|---|---|---|---|---|---|', *F, '',
         '### Filament', '', '| Colour | Hex | Material | Model mass | With 15 % for supports and scrap |', '|---|---|---|---|---|', *fil, '',
         f"Optional alternate to item {num['idler']}: printed idlers, 5 wheels and 5 bushings in PETG or nylon, each held by an M2.5 x 8 mm self-tapping screw, from [prints/dynamixel/optional/](../../prints/dynamixel/optional/README.md). Untested.", '',
         '## Build notes that affect ordering', '',
         f"- **Items {num['servo']}, {num['batt']}:** the servos run directly from 2S, 7.4-8.4 V, above ROBOTIS's 6 V maximum. Expect a shorter life than ROBOTIS rates. The walking policies were trained at this voltage.",
         f"- **Item {num['m077']}:** with it, order {n - 1} of item {num['servo']}. It moves nearly 4 times faster, so limit its speed in software. Its gearing is lower, so check that the jaw holds when unpowered. The simulations use the M288.",
         f"- **Item {num['board']}:** set both jumpers to B. Its silkscreen says DC 9-12.6 V and the battery is 7.4-8.4 V: bench test before ordering in quantity.",
         f"- **Item {num['imu']}:** its listing names both BNO080 and BNO085: confirm which chip arrives, its size, and that it starts in I2C mode. The model and fit come from Adafruit's board.",
         f"- **Item {num['reg']}:** feeds the Pi's PWR port only. It can output up to 12 V if a device asks for fast charging, so measure about 5 V before connecting.",
         f"- **Item {num['batt']}:** marked HV. Charge as a normal 2S, to 8.4 V.",
         f"- **Item {num['usb']}:** check the Pi's voltage under load, as the ribbon's wires are thin.",
         f"- **Items {num['m2x6']}, {num['m2x8']}:** come in ROBOTIS's servo box. Seeed sells the servo as a numbered Reachy Mini part, with an arm and a preset ID: order item {num['m2kit']} and set each ID again if buying there.",
         '- Each servo includes a 180 mm cable, which covers every link in the chains except the 2 long ones.', '',
         '## Open before ordering', '',
         f"- **Servo supply:** item {num['servo']} is sold out at ROBOTIS US and limited at Seeed. {n} units is the longest lead time here.",
         f"- **Sources to choose:** items {', '.join(str(num[x]) for x in ('long',))}.",
         f"- **Measure on the first parts:** a horn in the bore of item {num['mr2216']}; the Waveshare board's standoffs against their printed hex sockets, 5 mm across flats (item {num['board']}); the camera board (item {num['cam']}); servo cable lengths (item {num['long']}).",
         f"- **Amazon listings** (items {', '.join(str(num[x]) for x in ('mr2216', 'b6700', 'm2f', 'wash', 'board', 'imu', 'otg', 'batt', 'xt30', 'wire', 'thin', 'cam'))}, and those found by search) are as last read: confirm each page before ordering.",
         '- **Not in this design:** power switch (the XT30 is the disconnect), speaker, microphone.', '']
    folder = G.out_path('docs')
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, 'BOM.md'), 'w', encoding='utf-8').write('\n'.join(L))


def bom_hybrid(spec):
    """The hybrid duck's bill of materials, in the all-Dynamixel's format: every purchased and fabricated part, one table each, nice-to-haves marked Optional and left out of the total."""
    servos, bear, screws = counts(spec)
    inert = MM.link_inertials(spec)
    ps = [p for v in inert.values() for p in v[3]]
    pla, tpu = sum(p[2] for p in ps if p[1] == 'pla'), sum(p[2] for p in ps if p[1] == 'tpu')
    total = sum(v[0] for v in inert.values())
    parts = json.load(open(G.parts_path(), encoding='utf-8'))['parts']
    n_sts = servos['STS3215_C044'] + servos['STS3215_C046']
    n_dx = servos['XL330_M288'] + servos['XC330_M288']

    def sc(size, ln):
        return screws[(size, ln)]

    def link(label, url):
        return f'[{label}]({url})'
    m3 = sorted((ln, c) for (sz, ln), c in screws.items() if sz == 'M3')
    # (key, part, maker and part number, specification, quantity per robot, what is ordered, how many, price each or None, source, Required / Optional)
    GROUPS = [
        ('Actuators', [
            ('c044', 'Smart servo: hip roll, hip pitch, knee, ankle', 'Feetech STS3215-C044', '7.4 V, 1:191, TTL bus, 2 sockets. Listings give 16 and 27.4 kg.cm stall: see the notes', servos['STS3215_C044'], 'each', servos['STS3215_C044'], 23.98,
             amz('B0H3THGR55', 'Amazon, MengJie') + ': 7 left at this price on 2026-11-02. ' + amz('B0G2L15ZG8', 'Amazon, RCmall, the 1-191 option') + ': 6 left at $25.99. Neither alone had 8', 'Required'),
            ('c046', 'Smart servo: hip yaw', 'Feetech STS3215-C046', '7.4 V, 1:147, TTL bus, 2 sockets', servos['STS3215_C046'], 'each', servos['STS3215_C046'], 23.98, amz('B0H3TNG1Z6', 'Amazon, MengJie') + ': 6 left on 2026-11-02', 'Required'),
            ('xc330', 'Smart servo: neck', 'ROBOTIS XC330-M288-T', '0.93 N m stall at 5 V, 288.4:1, 23 g', servos['XC330_M288'], 'each', servos['XC330_M288'], 103.39,
             link('RobotShop', 'https://www.robotshop.com/products/robotis-dynamixel-xc330-m288-t-smart-servo-actuator') + ': on backorder on 2026-11-05. ' + link('ROBOTIS US', 'https://robotis.us/products/dynamixel-xc330-m288-t') + ': sold out, no date', 'Required'),
            ('xl330', 'Smart servo: head pitch, yaw, roll, beak', 'ROBOTIS XL330-M288-T', '0.52 N m stall and 103 rev/min at 5 V, 288.4:1, 18 g', servos['XL330_M288'], 'each', servos['XL330_M288'], 27.49,
             link('ROBOTIS US', 'https://robotis.us/products/dynamixel-xl330-m288-t') + ': sold out on 2026-11-05, lead time to end of November. Second source ' + link('Seeed', 'https://www.seeedstudio.com/Servo-Motor-1-5V-103RPM-Brush-mm-p-6783.html') + ' at $31.40, limit 2 per account', 'Required'),
        ]),
        ('Bearings, horns and idlers', [
            ('b6704', 'Ball bearing, around each STS3215 horn', '6704ZZ', '20 x 27 x 4 mm', bear['6704ZZ'], 'pack of 10', 1, 18.39, amz('B082PSB7NH', 'Amazon, uxcell'), 'Required'),
            ('mr2216', 'Ball bearing, around the head yaw and roll horns', 'MR2216ZZ (ET2216ZZ)', '16 x 22 x 4 mm', bear['MR2216ZZ'], 'pack of 10', 1, 42.72, amz('B0C5ZCVGNP'), 'Required'),
            ('b6700', 'Ball bearing, shoe inner ear', '6700ZZ', '10 x 15 x 4 mm', bear['6700ZZ'], 'pack of 10', 1, 6.79, amz('B0FQ4VYXRP'), 'Required'),
            ('horn', 'Horn, one on each Dynamixel', 'ROBOTIS HNX330-N102', 'for XL330 and XC330', n_dx, 'pack of 5', 1, 4.60, link('ROBOTIS US', 'https://robotis.us/hnx330-n102-5pcs') + ': sold out on 2026-11-05, lead time mid-November. ROBOTIS\'s box list for these servos names no horn', 'Required'),
            ('idler', 'Idler: neck, head pitch, head roll', 'ROBOTIS FPX330-H101', 'set of 4', 3, 'set of 4', 1, 11.27, link('ROBOTIS US', 'https://robotis.us/fpx330-h101-4pcs-set/'), 'Required'),
        ]),
        ('Fasteners', [
            ('m2kit', 'Screws, self-tapping pan head: M2 x 6, M2 x 8', 'generic', f'{sc("M2", 6)} x M2 x 6, {sc("M2", 8)} x M2 x 8. Kit of 800, 100 of each', sc('M2', 6) + sc('M2', 8), 'kit', 1, 15.66, amz('B0GV338JJK'), 'Required'),
            ('m25', 'Screw, the 2 bus boards, machine thread', 'generic', 'M2.5 x 5 mm, pan head, Phillips, black oxide 304 stainless', sc('M2.5', 5), 'pack of 50', 1, None, 'Amazon', 'Required'),
            ('so', 'Spare hex standoffs, bus board: 4 come with each Waveshare board', 'uxcell', 'brass, M2.5, female-female, 8 mm long, 5 mm across flats', 0, 'pack of 50', 1, None, 'Amazon', 'Optional'),
            ('m3kit', 'Screws, socket cap: ' + ', '.join(f'{c} x M3 x {ln}' for ln, c in m3), 'generic', 'kit of 610 with nuts and washers. Its count per length is not listed: count them on arrival', sum(c for _, c in m3), 'kit', 1, 19.99, amz('B09NR8X2LV'), 'Required'),
            ('m3f', 'Screw, flat head socket: ankle rear horn, flush under the bearing', 'generic', 'M3 x 6 mm. Head 6 mm wide, 1.7 mm high', sc('M3 flat', 6), 'pack of 100', 1, 5.99, amz('B01HBN0U76'), 'Required'),
            ('wash', 'Washer, far hinge tab to hood', 'uxcell', 'M3, 6 mm outside, 0.5 mm thick, stainless', 1, 'pack of 100', 1, None, amz('B015A39NCC'), 'Required'),
        ]),
        ('Electronics', [
            ('pi', 'Computer', 'Raspberry Pi Zero 2 W', 'without header', 1, 'each', 1, 17.25, link('PiShop', 'https://www.pishop.us/product/raspberry-pi-zero-2-w/') + ': out of stock on 2026-11-03', 'Required'),
            ('sd', 'microSD card', 'SanDisk Ultra', '32 GB microSDHC, A1, Class 10, UHS-I', 1, 'each', 1, 21.49, amz('B08L5HMJVW'), 'Required'),
            ('board', 'Servo bus board, one per bus', 'Waveshare Bus Servo Adapter (A), SKU 25514', 'USB-C and UART, 2 servo sockets, also sold as Serial Bus Servo Driver Board', 2, 'each', 2, 4.99, link('Waveshare', 'https://www.waveshare.com/bus-servo-adapter-a.htm') + ', before its shipping. ' + amz('B0CTMM4LWK') + '. Second source ' + link('Abra', 'https://abra-electronics.com/electromechanical/motors/motor-controllers/wave-25514-serial-bus-servo-driver-board.html'), 'Required'),
            ('reg', '5 V regulator, the Pi\'s', 'hiBCTR USB buck converter QC3.0', '6-32 V in, 35 x 17 x 8.5 mm', 1, 'pack of 2', 1, 7.97, 'Amazon', 'Required'),
            ('ubec', '5 V regulator, the Dynamixels\'', 'FEICHAO UBEC', '8 A, 5 V or 6 V by jumper, 39 x 21 x 6 mm', 1, 'each', 1, 18.98, amz('B07DD9L6P6'), 'Required'),
            ('imu', 'IMU', 'BNO085 module, EC Buying', 'modelled at 25.6 x 22.7 x 4.6 mm; I2C', 1, 'each', 1, None, amz('B0CDGZMLPP') + '. Second source ' + link('Adafruit 4754', 'https://www.adafruit.com/product/4754') + ' at $29.50, in stock on 2026-11-03', 'Required'),
            ('cam', 'Camera', 'Arducam 8 MP IMX219', 'board modelled at 24 x 24 mm', 1, 'each', 1, 16.99, amz('B09V576TFN'), 'Optional'),
            ('ribbon', 'Camera ribbon, if the camera lacks one', 'GODIYMODULES', 'Pi Zero 22-pin to 15-pin, 15 cm', 1, 'pack of 2', 1, None, amz('B0F9WJ62LV'), 'Optional'),
        ]),
        ('Power and wiring', [
            ('batt', 'Battery', 'Zeee 2S LiPo, 50C', '850 mAh, 54 x 30 x 15 mm, 52 g. Comes on a small JST plug, too small for 10 servos: its power lead is cut and an XT30 soldered on', 1, 'pack of 2', 1, 23.39, amz('B0DGQ6DRLS', 'Amazon, Zeee'), 'Required'),
            ('xt30', 'Battery connector', 'Nuofany XT30 pigtail', '100 mm, 16 AWG', 1, '5 pairs', 1, 9.99, amz('B0B4H4GKQL'), 'Required'),
            ('wire', 'Power wire, red and black: 2S and 5 V up the neck', 'BNTECHGO silicone wire', '20 AWG, 2 pairs of about 400 mm', 1, '10 ft each', 1, None, amz('B01M12PSJM'), 'Required'),
            ('thin', 'Signal wire: UART and IMU, the Pi\'s regulator', 'Fermerry silicone wire', '28 AWG stranded, 7 + 2 wires', 1, '6 colours, 5 ft each', 1, None, amz('B089CR4SDM'), 'Required'),
            ('long', 'Feetech lead: Feetech board to the legs\' splice, up the neck', 'generic', '3-pin 5264, 2.54 mm, any length: one plug is kept, its V wire taken out, and it is extended in item THIN to about 330 mm', 1, 'each', 1, None, 'no listing confirmed: the 2 hip yaw leads to the splice are from the servos\' own boxes', 'Required'),
            ('usb', 'Regulator to Pi power', 'LY tech flat ribbon USB', 'right-angle USB-A to right-angle micro USB, 10 cm', 1, 'each', 1, 13.50, 'Amazon', 'Required'),
            ('otg', 'Pi to Dynamixel board', 'Veeloon', 'right-angle micro USB OTG to right-angle USB-C, 0.6 ft', 1, 'pack of 2', 1, 7.99, amz('B0DKBQ7TD3'), 'Required'),
        ]),
        ('Consumables', [
            ('fix', 'Foam tape, hook-and-loop strap, small cable ties', 'generic', '', 1, 'lot', 1, 12.00, 'any hardware shop; price estimated', 'Required'),
            ('joint', 'Solder, heat-shrink tube, CA glue', 'generic', '', 1, 'lot', 1, None, 'any hardware shop', 'Required'),
        ]),
        ('Support equipment (not in the robot)', [
            ('chg', 'Charger', 'as linked', '2S LiPo, to 8.4 V, must match the balance plug', 1, 'each', 1, 9.49, amz('B0FDKX4V38'), 'Required'),
        ]),
    ]
    num, k = {}, 0
    for _, rows in GROUPS:
        for r in rows:
            k += 1
            num[r[0]] = k
    GROUPS = [(g, [tuple(str(x).replace('item THIN', f"item {num['thin']}") if isinstance(x, str) else x for x in r) for r in rows]) for g, rows in GROUPS]
    SEARCH = {'c044': 'Feetech STS3215 C044 1:191', 'c046': 'Feetech STS3215 C046 1:147', 'xc330': 'Dynamixel XC330-M288-T', 'xl330': 'Dynamixel XL330-M288-T', 'b6704': '6704ZZ bearing 20x27x4mm', 'mr2216': 'MR2216ZZ bearing 16x22x4mm', 'b6700': '6700ZZ bearing 10x15x4mm',
              'horn': 'Dynamixel HNX330-N102 horn', 'idler': 'Dynamixel FPX330-H101 idler', 'm2kit': 'M2 self tapping pan head screw kit', 'm25': 'M2.5 x 5mm pan head machine screw black oxide', 'so': 'uxcell M2.5 x 8mm female female hex brass standoff',
              'm3kit': 'M3 socket cap screw kit', 'm3f': 'M3 x 6mm flat head socket screw', 'wash': 'uxcell M3 x 6mm x 0.5mm flat washer', 'pi': 'Raspberry Pi Zero 2 W', 'sd': 'SanDisk 32GB Ultra microSDHC A1', 'board': 'Waveshare Serial Bus Servo Driver Board',
              'reg': 'hiBCTR USB buck converter QC3.0', 'ubec': 'FEICHAO UBEC 5V 8A', 'imu': 'BNO085 IMU module', 'cam': 'Arducam 8MP IMX219 camera module', 'ribbon': 'Raspberry Pi Zero camera cable 22 pin to 15 pin 15cm',
              'batt': 'Zeee 2S 850mAh 50C LiPo', 'xt30': 'XT30 pigtail 16 AWG 100mm', 'wire': '20 AWG silicone wire red black', 'thin': '28 AWG silicone stranded wire', 'long': '5264 3 pin 2.54mm servo cable female female 300mm',
              'usb': 'LY tech flat ribbon micro USB 90 degree', 'otg': 'micro USB to USB C OTG cable 90 degree', 'fix': 'foam tape hook and loop strap cable ties', 'joint': 'solder heat shrink CA glue', 'chg': '2S LiPo balance charger JST-XH'}

    def search(key):
        return f"[Search Amazon](https://www.amazon.com/s?k={SEARCH[key].replace(' ', '+')})"

    def money(v):
        return f'${v:,.2f}'
    tot, opt, unpriced, summary, T = 0.0, 0.0, 0, [], []
    for g, rows in GROUPS:
        T += [f'### {g}', '', '| Item | Part | Maker / part number | Specification | Qty per robot | Order unit | Order qty | Unit price | Line price | Source |', '|---|---|---|---|---|---|---|---|---|---|']
        sub = 0.0
        for key, part, mpn, spec_, q, unit, oq, price, src, st in rows:
            line = None if price is None else oq * price
            if st == 'Required':
                if line is not None:
                    sub += line
                elif oq:
                    unpriced += 1
            elif line is not None:
                opt += line
            o = st == 'Optional'
            T.append(f"| {num[key]} | {'**OPTIONAL:** ' if o else ''}{part} | {mpn} | {spec_} | {(f'({q})' if o else q) if q else '-'} | {unit} | {(f'({oq})' if o else oq) if oq else '-'} | {money(price) if price else '-'} | {money(line) if line else '-'} | {src}<br>{search(key)} |")
        T.append('')
        tot += sub
        summary.append(f'| {g} | {money(sub) if sub else "-"} |')
    COL = {'#3A3D42': 'Dark grey', '#E8642A': 'Orange', '#ECEBE6': 'White', '#9A9C98': 'Mid grey', '#F0A030': 'Amber', '#0A1420': 'Black', '#F2B233': 'Yellow', '#F7AE55': 'Pale orange'}
    total_v = {m: sum(q['volume_cm3'] for q in parts.values() if q['material'] == m) for m in ('pla', 'tpu')}

    def grams(q):
        return (pla if q['material'] == 'pla' else tpu) * 1000 * q['volume_cm3'] / total_v[q['material']]
    F, vol, j = [], {}, 0
    for name, q in parts.items():
        kk = (q['material'], q['color'])
        vol[kk] = vol.get(kk, 0) + grams(q)
        if name.startswith('R '):
            continue
        j += 1
        fn = name.replace(' ', '_') + '.stl'
        two = name.startswith('L ')
        assert os.path.exists(os.path.join(G.out_path('prints'), fn)), fn
        if two:
            assert 'R ' + name[2:] in parts, name
        shown = name[2:].capitalize() + ', left and right' if two else name.capitalize()
        files = f"`{fn}`, `R_{fn[2:]}`" if two else f'`{fn}`'
        F.append(f"| P{j} | {shown} | {files} | {'PLA' if q['material'] == 'pla' else 'TPU 95A'} | {COL.get(q['color'], q['color'])} | {q['color']} | {grams(q):.1f} g | {2 if two else 1} |")
    fil = [f"| {COL.get(c, c)} | {c} | {'PLA' if m == 'pla' else 'TPU 95A'} | {g_:.0f} g | {g_ * 1.15:.0f} g |" for (m, c), g_ in sorted(vol.items(), key=lambda x: (x[0][0], -x[1]))]
    L = ['# Hybrid duck: bill of materials', '',
         '| | |', '|---|---|',
         f'| Product | Hybrid duck, biped, 15 servos: {n_sts} Feetech STS3215 in the legs, {n_dx} ROBOTIS Dynamixel at the neck and head |',
         f'| Height, mass | 0.318 m, {total:.2f} kg as modelled |',
         '| Build quantity | Quantities are for 1 robot |',
         f'| Fabricated parts | {len(parts)} printed parts, {pla * 1000:.0f} g PLA and {tpu * 1000:.0f} g TPU 95A |',
         '| Status | Prototype: no unit built, no part test printed. Its walking policies were trained with foot switches, which this version doesn\'t have: it needs retraining before it walks |',
         '| Prices | USD, as listed 2026-11-02 to 2026-11-05, before tax and shipping. Confirm before ordering |',
         '| Related | [Print files](prints/README.md), [wiring](docs/WIRING.md), [assembly](docs/ASSEMBLY.md) |', '',
         'Generated by `tools/make_docs.py` from the spec. Quantities match the model.', '',
         '## Cost summary', '', '| Group | Required parts, priced |', '|---|---|', *summary,
         f'| **Total of quoted lines** | **{money(tot)}** |', '',
         f'{unpriced} required lines have no quote yet and are not in the total, nor is filament. Optional parts add {money(opt)} on the quoted lines.', '',
         '## Purchased parts', '', 'Every line is required unless it starts with **OPTIONAL**. Optional lines show their quantities in brackets and are not in the total.', '', *T,
         '## Fabricated parts', '', 'All 3D printed. Files are in [prints/](prints/README.md), already oriented for printing, in millimetres. Mass is each piece. The hood has an orange band, painted or split in the slicer.', '',
         '| Item | Part | File | Material | Colour | Hex | Mass each | Qty per robot |', '|---|---|---|---|---|---|---|---|', *F, '',
         '### Filament', '', '| Colour | Hex | Material | Model mass | With 15 % for supports and scrap |', '|---|---|---|---|---|', *fil, '',
         'Listings read on 2026-11-02: ' + amz('B0D41ZDC47', 'ELEGOO PLA+') + ', $13.99 per kg, and ' + amz('B0BGMP1MZ7', 'OVERTURE TPU 95A') + ', $23.99 per kg.', '',
         '## Build notes that affect ordering', '',
         f"- **Items {num['c044']}, {num['c046']}, {num['batt']}:** a full 2S pack is 8.4 V. Most sellers rate the 7.4 V STS3215 to 7.4 V; one gives 5-8.4 V. Try one servo on a charged pack first.",
         f"- **Item {num['c044']}:** listings disagree on its torque: 16 kg.cm (1.57 N m) in one title, 27.4 (2.69 N m) on others, the number the walking training uses. Feetech publishes neither that we could find. Measure one before ordering 8.",
         f"- **Items {num['c044']}, {num['c046']}:** listings give each servo 2 horns, 18 screws and a lead, about 15 cm, on a 5264 plug. Sellers differ: check the first box. The ankle's rear horn is one of those 2.",
         f"- **Items {num['xc330']}, {num['xl330']}:** each comes with a 180 mm cable, 6 M2 x 6 and 10 M2 x 8 screws, per ROBOTIS. Seeed sells the XL330 as a numbered Reachy Mini part, with an arm and a preset ID: set each ID again.",
         f"- **Item {num['horn']}:** ROBOTIS lists no horn in these servos' boxes, though it gives the screws for one. Check its size against the bore of item {num['mr2216']} before printing.",
         f"- **Item {num['board']}:** Feetech board: both jumpers at A, for UART. Dynamixel board: both at B, for USB. Silkscreen and shop page say DC 9-12.6 V; Waveshare's product page also says 5 V or 7.4 V can go in, and these boards get 7.4-8.4 V and 5 V: bench test one of each before fitting. The Dynamixel plugs may need its sockets eased.",
         f"- **Item {num['reg']}:** feeds the Pi's PWR port only. It can output up to 12 V if a device asks for fast charging, so measure about 5 V before connecting.",
         f"- **Item {num['ubec']}:** set its jumper to 5 V **before** connecting anything: 6 V is at the Dynamixels' limit. Listing's price read as each on 2026-11-02.",
         f"- **Item {num['batt']}:** a small plug on 10 servos that can pull 27 A between them won't do, hence item {num['xt30']}. Packs sold with an XT30 found: GNB 850 mAh 2S at 56 x 31 x 16 mm, CNHL 850 mAh 2S at 60 x 30 x 17 mm: neither fits the slot as modelled.",
         f"- **Item {num['usb']}:** check the Pi's voltage under load, as the ribbon's wires are thin.",
         f"- **Item {num['long']}:** carries data and ground only, so the walking current stays out of the neck. Each STS3215's own lead covers every other link: [lengths](reports/wire_routes.md).", '',
         '## Open before ordering', '',
         f"- **Servo supply:** items {num['xc330']}, {num['xl330']}, {num['horn']} are sold out at ROBOTIS US on 2026-11-05, and item {num['xc330']} is on backorder at RobotShop. These decide when it can be built.",
         f"- **Feetech stock:** items {num['c044']}, {num['c046']} are the Amazon counts of 2026-11-02, which change daily.",
         f"- **Sources to choose:** item {num['long']}.",
         f"- **Measure on the first parts:** a horn in the bores of items {num['b6704']}, {num['mr2216']}; the Waveshare board's standoffs against their printed hex sockets, 5 mm across flats (item {num['board']}); the camera board (item {num['cam']}); servo lead lengths (item {num['long']}).",
         f"- **Walking:** the policies in this repo were trained with foot switches. This duck has none: retrain before trusting any walk.",
         f"- **Amazon listings** (items {', '.join(str(num[x]) for x in ('c044', 'c046', 'b6704', 'mr2216', 'b6700', 'm2kit', 'm3kit', 'm3f', 'wash', 'sd', 'board', 'ubec', 'imu', 'batt', 'xt30', 'wire', 'thin', 'otg', 'cam', 'chg'))}, and those found by search) are as last read, or as read for the all-Dynamixel duck: confirm each page before ordering.",
         '- **Not in this design:** power switch (the XT30 is the disconnect), speaker, microphone.', '']
    open(os.path.join(G.ROOT, 'BOM.md'), 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    s = G.load()
    if G.RECIPE == 'dynamixel':
        bom_dynamixel(s)
        guide()
        print('docs/dynamixel/BOM.md, ASSEMBLY.md')
    elif G.RECIPE == 'hybrid':
        bom_hybrid(s)
        guide()
        print('BOM.md, docs/ASSEMBLY.md')
    else:
        bom(s)
        guide()
        print('BOM.md, docs/ASSEMBLY.md')
