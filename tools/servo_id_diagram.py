"""Draws the all-Dynamixel duck's servo ids, from pi/config/dynamixel.json, to docs/dynamixel/servo_ids.svg. Change the config
(tools/make_pi_config.py), not the picture.

  python -I tools/servo_id_diagram.py

A front view, the duck facing you: its right leg is on your left. Ids go in the order they're set, each chain from the bottom up.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, 'pi', 'config', 'dynamixel.json')
OUT = os.path.join(ROOT, 'docs', 'dynamixel', 'servo_ids.svg')
COLOURS = {'right': ('#E1F5EE', '#0F6E56', '#085041'), 'left': ('#EEEDFE', '#534AB7', '#3C3489'), 'head': ('#FAECE7', '#993C1D', '#712B13')}
LEG_Y = {'hip_yaw': 345, 'hip_roll': 380, 'hip_pitch': 415, 'knee': 480, 'ankle': 545}
HEAD_Y = {'beak': 60, 'head_roll': 95, 'head_yaw': 130, 'head_pitch': 172, 'neck_pitch': 212}
LINE, TEXT, MUTED = '#5F5E5A', '#2C2C2A', '#5F5E5A'


def place(name):
    """(x, y, group, label, label side) of a joint's servo."""
    for side, x in (('right', 280), ('left', 400)):
        if name.startswith(side + '_'):
            j = name[len(side) + 1:]
            return x, LEG_Y[j], side, j.replace('_', ' ').capitalize(), 'out'
    return 340, HEAD_Y[name], 'head', name.replace('_', ' ').capitalize(), 'in'


def main():
    joints = json.load(open(CFG, encoding='utf-8'))['joints']
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="680" height="650" viewBox="0 0 680 650" font-family="Arial, Helvetica, sans-serif">',
         '<title>Servo ids of the all-Dynamixel duck</title>',
         '<rect width="680" height="650" fill="#FFFFFF"/>',
         '<rect x="290" y="35" width="100" height="117" rx="16" fill="none" stroke="#B4B2A9" stroke-dasharray="4 3"/>',
         f'<text x="300" y="27" font-size="12" fill="{MUTED}">Head</text>',
         '<rect x="240" y="235" width="200" height="85" rx="12" fill="#F1EFE8" stroke="#B4B2A9"/>',
         f'<text x="340" y="272" font-size="14" font-weight="bold" fill="{TEXT}" text-anchor="middle">Body</text>',
         f'<text x="340" y="294" font-size="12" fill="{MUTED}" text-anchor="middle">Battery, IMU</text>']
    # bones: the head column, then each leg, stopping at the servos' circles
    for x, ys, top, bottom in ((340, sorted(HEAD_Y.values()), None, 235), (280, sorted(LEG_Y.values()), 320, 566), (400, sorted(LEG_Y.values()), 320, 566)):
        stops = ([top] if top else []) + ys + [bottom]
        for a, b in zip(stops, stops[1:]):
            y0 = a + (13 if a in ys else 0)
            y1 = b - (13 if b in ys else 0)
            if y1 > y0:
                s.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{LINE}" stroke-width="2"/>')
    for x in (280, 400):
        s.append(f'<rect x="{x - 30}" y="566" width="60" height="12" rx="4" fill="#F1EFE8" stroke="#B4B2A9"/>')
    for name, j in joints.items():
        x, y, group, label, side = place(name)
        fill, stroke, ink = COLOURS[group]
        s.append(f'<circle cx="{x}" cy="{y}" r="13" fill="{fill}" stroke="{stroke}"/>')
        s.append(f'<text x="{x}" y="{y + 5}" font-size="14" font-weight="bold" fill="{ink}" text-anchor="middle">{j["id"]}</text>')
        if group == 'right':
            lx, anchor = x - 22, 'end'
        elif group == 'left':
            lx, anchor = x + 22, 'start'
        else:
            lx, anchor = (410 if y < 152 else 362), 'start'
        s.append(f'<text x="{lx}" y="{y + 4}" font-size="12" fill="{MUTED}" text-anchor="{anchor}">{label}</text>')
    s += [f'<text x="280" y="604" font-size="14" font-weight="bold" fill="{TEXT}" text-anchor="middle">Duck\'s right leg</text>',
          f'<text x="400" y="604" font-size="14" font-weight="bold" fill="{TEXT}" text-anchor="middle">Duck\'s left leg</text>',
          f'<text x="340" y="630" font-size="12" fill="{MUTED}" text-anchor="middle">Front view: the duck faces you. Set in order, 1 to 15</text>',
          '</svg>']
    open(OUT, 'w', encoding='utf-8').write('\n'.join(s) + '\n')
    print('wrote', os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
