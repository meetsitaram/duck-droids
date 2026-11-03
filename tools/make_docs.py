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


# Amazon's stock counts are what the page showed on 2026-11-02, and they change daily.
BUY = [
    # (what, key in the spec, price each USD, where, note)
    ('Feetech STS3215-C044 servo, 7.4 V, 1:191', 'STS3215_C044', 23.98,
     f"{amz('B0H3THGR55', 'Amazon, MengJie')} (7 left at $23.98) and {amz('B0G2L15ZG8', 'Amazon, RCmall, the 1-191 option')} (6 left at $25.99). "
     'Neither alone has 8', 'hip roll, hip pitch, knee, ankle'),
    ('Feetech STS3215-C046 servo, 7.4 V, 1:147', 'STS3215_C046', 23.98, f"{amz('B0H3TNG1Z6', 'Amazon, MengJie')} (6 left)", 'hip yaw'),
    ('ROBOTIS Dynamixel XC330-M288-T servo', 'XC330_M288', 103.39,
     '[ROBOTIS US](https://robotis.us/products/dynamixel-xc330-m288-t), **1 month lead time**. Amazon: unavailable', 'neck: it carries the head'),
    ('ROBOTIS Dynamixel XL330-M288-T servo', 'XL330_M288', 27.49,
     '[ROBOTIS US](https://robotis.us/products/dynamixel-xl330-m288-t), **2 months lead time**. Amazon: no ROBOTIS listing, only a third-party seller. '
     '[Seeed](https://www.seeedstudio.com/Servo-Motor-1-5V-103RPM-Brush-mm-p-6783.html) has it in stock at $31.40, limit 2 per account', 'head pitch, yaw, roll, beak'),
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
    ('M3 aluminium spacers, 3 mm long, 5 mm OD, 10', 6.99, amz('B0CQFF328L'), 'jaw hinges, with a 0.5 mm M3 washer each to make 3.5 mm. No 3.5 mm spacer found. 4 packs left'),
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
    ('BNO085 IMU board', '1', 22.99, amz('B0CL26J81F'), 'on the top plate'),
    ('2S LiPo, 850 mAh, 54 x 30 x 15 mm, 2 pack', '1', 23.39, amz('B0DGQ6DRLS', 'Amazon, Zeee'), '**1 mm thicker than the 14 mm slot.** No 800 mAh pack under 14 mm found. '
     f"{amz('B0727XZFDW', 'Tattu 650 mAh')}, 57 x 31 x 12 mm, $9.16, is thinner but 1 mm wider and shorter-lived"),
    ('2S balance charger', '1', 9.49, amz('B0FDKX4V38'), 'check it matches the pack\'s balance plug'),
    ('5 V 5 A UBEC, 2 pack', '2', 9.99, amz('B0C3GVGYDS'), 'one for the Pi and IMU, one for the Dynamixels: see the warning below'),
    ('Feetech FE-URT-1 bus board', '1', 16.99, amz('B0FRQZQQF3'), 'USB to the STS3215 bus: sets IDs on the bench. Check its size for the body'),
    ('ROBOTIS U2D2', '1', 36.92, '[ROBOTIS US](https://robotis.us/products/u2d2). Amazon: only a clone', 'USB to the Dynamixel bus: sets IDs. 48 x 18 x 15 mm, so it may not stay on board'),
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
    bearings = 18.39 + 42.72 + 6.79 + 11.27
    packs = sum(p[1] for p in PACKS)
    fil = sum(p[1] for p in PRINT)
    elec = sum(e[2] for e in ELECTRONICS)
    L = ['# milli: parts to buy', '',
         'Generated by `tools/make_docs.py` from the spec, so the counts match the model. Amazon US prices and stock as shown on',
         '2026-11-02, signed out, before tax and shipping: **stock is thin, so confirm each part and price before ordering.**', '',
         f'Model mass {total:.2f} kg.', '',
         '| Group | About | On Amazon? |', '|---|---|---|',
         f'| Servos | ${cost:.0f} | Feetech yes, Dynamixel no |',
         f'| Bearings and idlers | ${bearings:.0f} | bearings yes, idlers no |',
         f'| Screws and spacers | ${packs:.0f} | yes |',
         f'| Filament | ${fil:.0f} | yes |',
         f'| Electronics (wait, see below) | ${elec:.0f} | most, but not the Pi at a fair price |',
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
    L += ['', '## Sensors and electronics', '',
          '**Wait before ordering most of these.** The next round settles wiring, speaker and microphone, and checking real parts',
          'found that this part of the model does not work yet:', '',
          '- **The 5 V supply is undersized.** Stalled, the four XL330s and the XC330 draw 7.7 A (1.47 A and 1.80 A each, per ROBOTIS), before the Pi. '
          'A 3 A mini regulator cannot do it, and 5 A only works if they don\'t all stall together. '
          f"An {amz('B07DD9L6P6', '8 A UBEC')} ($18.98, 39 x 21 x 6 mm) covers the servos if 5 A proves short.",
          '- **The boards do not fit their boxes.** The regulator and IMU share a box 2.5 mm tall on the top plate, and the shell leaves 4 mm. The UBECs are taller. '
          'The bus board\'s box is 3.7 mm thick, and bus boards have connectors.',
          '- **A full 2S pack is 8.4 V.** Waveshare and most sellers rate the 7.4 V STS3215 to 7.4 V; one says 8.4 V. Find out which before connecting a charged battery directly.',
          '- **Avoid the common $12-13 Waveshare servo board** ([this one](https://www.amazon.com/dp/B0CJ6TP3TP)): its input is 9-12.6 V and must match the servos.', '',
          '| Have | Part | Need | Price | Where | Note |', '|---|---|---|---|---|---|']
    for what, need, pr, where, note in ELECTRONICS:
        L.append(f'| ☐ | {what} | {need} | ${pr:.2f} | {where} | {note} |')
    L += ['', '## Not designed yet', '', '- The rod from the beak servo to the jaw, and its two ball links.',
          '- Wire routes, cable lengths, power switch, battery connector.', '- Speaker and microphone.', '']
    with open(os.path.join(G.ROOT, 'BOM.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


TITLE = {'thigh_L': '1. Thighs', 'shin_L': '2. Shins and ankles', 'shoe_L': '3. Shoes', 'leg_L': '4. Join each leg', 'body': '5. Chassis and hips',
         'legs': '6. Legs onto the hips', 'column': '7. Neck column', 'torso': '8. Neck and body shell', 'headbench': '9. Head yaw and roll', 'head': '10. The head'}
WARN = {
    'thigh_L': 'Plug the 3-pin cables in before the servos go in: there is no way to reach the sockets afterwards.',
    'shin_L': 'The rear-horn screws go in before the bearing: the bearing covers them.',
    'shoe_L': 'Solder the switch wires before pressing the switch in, and try the switch against the sole before printing all four parts: its travel in this TPU is untested.',
    'leg_L': 'The roll bracket goes onto the hip horn here, on the bench: once the leg is on the robot, the roll servo blocks those 4 screws.',
    'body': 'Screw on the yaw brackets **before** the roll servos: the roll servos cover those screws.',
    'column': 'Fit both horns to each servo before it goes in, at mid-range.',
    'torso': 'Do the neck before the body shell: the shell blocks the neck\'s horn screws. Do the shell before the head: the head will not pass through its slot.',
    'headbench': 'The head yaw servo\'s screws under the bridge go in here, on the bench: once this is on the neck, they cannot be reached.',
    'head': 'The roll servo\'s rear horn screws go in before the beak servo, which covers them. The hinge screws are what holds the hood on, so they are last.',
}


def guide():
    L = ['# How to build milli', '', 'Generated by `tools/make_docs.py` from the order in `tools/assembly.py`. That order is checked: every part can',
         'slide in along the path shown without hitting what is already on, and a key reaches every screw (`python -I tools/assembly.py`).', '',
         'Watch each animation, then do the same. Parts: [BOM.md](../BOM.md). The right side is the mirror of the left, so only the left is shown.', '',
         '> ⚠ marks what has to happen in that order, or cannot be done later.', '',
         '## 0. Before you start', '',
         '1. **Print one joint first** ([prints/README.md](../prints/README.md)), then everything. None of it has been test printed yet.',
         '2. **Set each servo\'s ID on its own**, before any are chained: Feetech 1-8, Dynamixel 1-7, on their separate buses. Label each servo.',
         '3. **Move each servo to mid-range** and keep it there: horns go on at mid-range, or the joint\'s range will be off-centre.',
         '4. **One thing the pictures leave out:** the STS3215\'s face steps down 2.5 mm round its horn, and each lid\'s floor fills that step.',
         '   It does not show here, as the model\'s servo is a plain box.', '',
         'Tools: 1.5 and 2 mm hex or small Phillips drivers, soldering iron (a grown-up, if you are young), threadlock for screws into metal.', '']
    for sec in A.sections():
        k = sec['key']
        if k not in TITLE:
            continue
        L += [f'## {TITLE[k]}', '', f'![{TITLE[k]}](images/assembly/{k}.gif)', '']
        if k in WARN:
            L += [f'> ⚠ {WARN[k]}', '']
        for i, (cap, _, _) in enumerate(sec['steps'], 1):
            L.append(f'{i}. {cap}')
        if k.endswith('_L'):
            L += ['', 'Then the same for the right side, mirrored.']
        L.append('')
    L += ['## Not in this guide yet', '', '- Routing the wires, and the electronics: next round.', '- The rod from the beak servo to the jaw: not designed yet.', '']
    with open(os.path.join(G.ROOT, 'docs', 'ASSEMBLY.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    s = G.load()
    bom(s)
    guide()
    print('BOM.md, docs/ASSEMBLY.md')
