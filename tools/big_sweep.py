"""What tools/checks.py leaves out on the big duck: its thigh covers are 'decal', so no sweep tests them. Sweeps them through the hip pitch's range against everything above that joint.

  MILLI_RECIPE=big python -I tools/big_sweep.py

Zero pose for every other joint. It doesn't test hip pitch and hip roll together, or the rods, whose real motion is the four-bar's and isn't in the model.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geom as G  # noqa: E402
import mass_model as MM  # noqa: E402

C = MM.C
TOUCH = 2e-8                                       # m3: 0.02 cm3


def rotated(solid, origin, ang):
    """A solid turned ang about a y axis through origin."""
    return solid.translate([-v for v in origin]).rotate([0.0, math.degrees(ang), 0.0]).translate(origin)


def main():
    s = G.load()
    S = C.Solids(s)
    j = next(x for x in s['joints'] if x['name'] == 'L_hip_pitch')
    above = ('trunk', 'L_hip_yaw_link', 'L_hip_roll_link')
    fixed = [(ln, g['name'], S.geom[(ln, i)]) for ln in above for i, g in enumerate(s['links'][ln]['geoms']) if S.geom.get((ln, i)) is not None and g['role'] != 'cut']
    bad = {}
    n = 0
    for i, g in enumerate(s['links']['L_hip_pitch_link']['geoms']):
        if 'thigh cover' not in g['name'] or S.geom.get(('L_hip_pitch_link', i)) is None:
            continue
        n += 1
        m = S.geom[('L_hip_pitch_link', i)]
        for a in np.linspace(j['lower'], j['upper'], 21):
            r = rotated(m, j['origin'], float(a))
            for ln, name, f in fixed:
                v = C.overlap(r, f)
                if v > TOUCH:
                    k = (g['name'], name)
                    if k not in bad or v > bad[k][0]:
                        bad[k] = (v, float(a))
    for (a, b), (v, ang) in sorted(bad.items(), key=lambda kv: -kv[1][0]):
        print(f'{a} | {b} | {v * 1e6:.1f} cm3 at {ang:+.2f} rad')
    print(f'{n} covers swept over {j["lower"]:+.2f} to {j["upper"]:+.2f} rad, {len(bad)} pairs clash')
    return json.dumps(sorted(k[0] for k in bad))


if __name__ == '__main__':
    main()
