"""Writes the duck's Xbox controller shortcuts as a picture, the controller in the middle (dark):
  python tools/make_controller_shortcuts.py docs/dynamixel/controller_shortcuts.svg
then a PNG from it: msedge --headless --window-size=2200,1040 --screenshot=<png> file:///<svg>
The combos are pi/launcher.py's: change both together. Each mode's box has the colour of the button that starts it."""
import sys
from xml.sax.saxutils import escape

W, H = 2200, 1040
BG, TEXT, MUTED = '#0D1117', '#E6EDF3', '#9BA7B4'
GREEN, RED, BLUE, YELLOW = ('#3FB950', '#11231A'), ('#F85149', '#2A1416'), ('#58A6FF', '#101E33'), ('#E3B341', '#2A2110')   # A, B, X, Y
PURPLE, WHITE = ('#BC8CFF', '#1D1730'), ('#F0F6FC', '#1A212B')
out = []


def box(x, y, w, h, col, title, lines):
    stroke, fill = col
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{fill}" stroke="{stroke}" stroke-width="4"/>')
    ty = y + 56
    out.append(f'<text x="{x + 30}" y="{ty}" font-size="32" font-weight="700" fill="{stroke}">{escape(title)}</text>')
    ty += 12
    for text in lines:
        ty += 42
        out.append(f'<text x="{x + 30}" y="{ty}" font-size="28" fill="{TEXT}">{escape(text)}</text>')


def arrow(points, col):
    d = 'M ' + ' L '.join(f'{x} {y}' for x, y in points)
    out.append(f'<path d="{d}" fill="none" stroke="{col[0]}" stroke-width="3.5" stroke-linejoin="round" marker-end="url(#a{col[0][1:]})"/>')


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Segoe UI, Noto Sans, Helvetica, Arial, sans-serif">')
out.append('<defs>' + ''.join(
    f'<marker id="a{c[0][1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c[0]}"/></marker>'
    for c in (GREEN, RED, BLUE, YELLOW, PURPLE, WHITE)) + '</defs>')
out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
out.append(f'<text x="1100" y="78" text-anchor="middle" font-size="46" font-weight="700" fill="{TEXT}">duck-droids: controller shortcuts</text>')
out.append(f'<text x="1100" y="124" text-anchor="middle" font-size="27" fill="{MUTED}">Hold a combo for 1 second. The same combo again ends a mode.</text>')

# the controller
EDGE, BODY, PART, KEY = '#5B6675', '#1B222C', '#2A333F', '#0D1117'
out.append(f'<path d="M 740 360 C 860 315, 1340 315, 1460 360 C 1525 390, 1555 520, 1545 630 C 1538 705, 1485 725, 1435 712 C 1380 698, 1355 665, 1290 655 L 910 655 '
           f'C 845 665, 820 698, 765 712 C 715 725, 662 705, 655 630 C 645 520, 675 390, 740 360 Z" fill="{BODY}" stroke="{EDGE}" stroke-width="6"/>')
for x, lab, ring in ((790, 'LT', PURPLE[0]), (1275, 'RT', TEXT)):
    out.append(f'<rect x="{x}" y="244" width="135" height="54" rx="25" fill="{PART}" stroke="{ring}" stroke-width="4"/>')
    out.append(f'<text x="{x + 67}" y="280" text-anchor="middle" font-size="25" font-weight="700" fill="{ring}">{lab}</text>')
for x, lab in ((775, 'LB'), (1260, 'RB')):
    out.append(f'<rect x="{x}" y="308" width="165" height="40" rx="19" fill="{PART}" stroke="{WHITE[0]}" stroke-width="4"/>')
    out.append(f'<text x="{x + 82}" y="337" text-anchor="middle" font-size="23" font-weight="700" fill="{WHITE[0]}">{lab}</text>')
for cx, cy in ((860, 450), (1205, 565)):                    # the sticks
    out.append(f'<circle cx="{cx}" cy="{cy}" r="62" fill="{PART}" stroke="{EDGE}" stroke-width="5"/><circle cx="{cx}" cy="{cy}" r="36" fill="{BODY}" stroke="{EDGE}" stroke-width="4"/>')
out.append(f'<rect x="958" y="507" width="44" height="116" rx="10" fill="{PART}" stroke="{EDGE}" stroke-width="4"/>')
out.append(f'<rect x="922" y="543" width="116" height="44" rx="10" fill="{PART}" stroke="{EDGE}" stroke-width="4"/>')
out.append(f'<rect x="960" y="545" width="40" height="40" fill="{PART}"/>')
for cx, cy, lab, col in ((1340, 402, 'Y', YELLOW), (1272, 466, 'X', BLUE), (1408, 466, 'B', RED), (1340, 530, 'A', GREEN)):
    out.append(f'<circle cx="{cx}" cy="{cy}" r="31" fill="{KEY}" stroke="{col[0]}" stroke-width="4.5"/>')
    out.append(f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" font-size="28" font-weight="700" fill="{col[0]}">{lab}</text>')
out.append(f'<circle cx="1100" cy="405" r="24" fill="{KEY}" stroke="{EDGE}" stroke-width="4"/>')
for cx in (1040, 1160):
    out.append(f'<circle cx="{cx}" cy="455" r="10" fill="{PART}" stroke="{EDGE}" stroke-width="3"/>')
for x, y, lab in ((760, 540, 'left stick'), (1168, 492, 'right stick'), (1070, 612, 'd-pad')):
    out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="20" fill="{MUTED}">{lab}</text>')

# left: walk and stand
box(40, 190, 560, 240, YELLOW, 'WALK  ·  RT + Y  (experimental)', ['left stick  =  walk', 'right stick  =  turn', 'd-pad  =  head'])
arrow([(600, 374), (1252, 374), (1312, 391)], YELLOW)
box(40, 470, 560, 200, GREEN, 'STAND  ·  RT + A', ['right stick, d-pad  =  head', 'X = nod  ·  Y = "yes"  ·  B = "no"'])
arrow([(600, 640), (1340, 640), (1340, 565)], GREEN)

# right: head mode and emotions
box(1600, 190, 560, 280, RED, 'HEAD MODE  ·  RT + B  (sitting)', ['RB / LB  =  next / previous emotion', 'X  =  repeat', 'right stick, d-pad  =  head', 'Y = beak  ·  A = rest pose'])
arrow([(1600, 330), (1442, 456)], RED)
box(1600, 510, 560, 200, BLUE, 'EMOTIONS  ·  RT + X  (standing)', ['RB / LB  =  next / previous emotion', 'X  =  repeat'])
arrow([(1600, 560), (1304, 479)], BLUE)

# below: Wi-Fi and stop
box(500, 800, 560, 200, PURPLE, 'WI-FI', ['LT + d-pad up  =  on', 'LT + d-pad down  =  off'])
arrow([(980, 800), (980, 627)], PURPLE)
box(1140, 800, 560, 200, WHITE, 'STOP', ['LB + RB  =  stop now', 'RT + LT + RB + LB  =  shut down'])

out.append('</svg>')
open(sys.argv[1], 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('written', sys.argv[1])
