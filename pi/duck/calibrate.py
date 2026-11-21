"""Measure each servo's centre tick on the real robot, with its torque off, posed by hand at the model's zero pose: legs straight, head level, beak shut.

  python -m duck.calibrate --port /dev/serial0

Saves the centres into the config. Directions aren't measured here: run `python run.py --policy wave --no-fall` next, on a stand, and fix a joint's `direction` if it moves the wrong way.
"""
import argparse
import json
import os

from . import dxl
from .hardware import load_config

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--port', default='/dev/serial0')
ap.add_argument('--joints', help='only these, comma separated, e.g. neck_pitch,head_pitch: the rest keep their centres')
ap.add_argument('--yes', action='store_true', help="the duck is already posed: don't wait for Enter")
ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
a = ap.parse_args()
cfg = load_config(a.config)
which = a.joints.split(',') if a.joints else list(cfg['joints'])
bad = [n for n in which if n not in cfg['joints']]
if bad:
    raise SystemExit('not joints: ' + ', '.join(bad))
bus = dxl.Bus(a.port)
for name in which:
    bus.write(cfg['joints'][name]['id'], dxl.TORQUE_ENABLE, 0)
if not a.yes:
    input('Pose the duck at zero: legs straight, head level, beak shut. Then press Enter. ')
for name in which:
    j = cfg['joints'][name]
    j['centre'] = bus.read(j['id'], dxl.PRESENT_POSITION, signed=True) % 4096    # with torque off a reading can be past a turn: keep it in one turn
    print(f"{name:18s} id {j['id']:2d} centre {j['centre']}")
with open(a.config, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=1)
print('saved', a.config)
