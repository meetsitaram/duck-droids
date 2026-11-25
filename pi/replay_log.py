"""Replay a run_policy.py log (run_policy_log.csv) in the twin: the solid duck from the joint angles the servos measured, a see-through
blue duck from the goals the policy (or the script) sent, slowed down and looped, with the time, the phase and the supply on screen.
The log has no IMU, so the body is placed by its feet, flat on the floor.

  python replay_log.py run_policy_log.csv                       the whole run at 1/4 speed
  python replay_log.py run_policy_log.csv --from -3 --speed 0.1  the last 3 s, at a tenth
"""
import argparse
import csv
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mujoco  # noqa: E402
import mujoco.viewer  # noqa: E402

import twin  # noqa: E402
from duck.hardware import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--speed', type=float, default=0.25)
    ap.add_argument('--from', dest='start', type=float, default=None, help='s into the log to start at; negative counts from the end')
    ap.add_argument('--to', type=float, default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    rows = list(csv.DictReader(open(a.log)))
    joints = [k[:-2] for k in rows[0] if k.endswith('_q') and not k.endswith('_qd')]
    t_end = float(rows[-1]['t'])
    t0 = a.start if a.start is None or a.start >= 0 else t_end + a.start
    rows = [r for r in rows if (t0 is None or float(r['t']) >= t0) and (a.to is None or float(r['t']) <= a.to)]
    frames = [(float(r['t']), r['phase'], r['volts'], {n: float(r[n + '_q']) for n in joints}, {n: float(r[n + '_goal']) for n in joints})
              for r in rows]
    m, d, adr = twin.load_model(cfg)
    view = twin.TargetView(m, adr, twin.CalibView(m).geoms)
    twin.GRAV[0] = None
    with mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
        while v.is_running():
            w0, f0 = time.monotonic(), frames[0][0]
            for t, phase, volts, q, goal in frames:
                while (time.monotonic() - w0) * a.speed < t - f0:
                    time.sleep(0.002)
                if not v.is_running():
                    return
                with v.lock():
                    twin.pose(m, d, adr, q)
                    texts = view.show(v, dict(goal=goal), q, None)
                    texts = [x for x in texts if x[1] != mujoco.mjtGridPos.mjGRID_TOPRIGHT]
                    texts.append((mujoco.mjtFontScale.mjFONTSCALE_200, mujoco.mjtGridPos.mjGRID_TOPRIGHT,
                                  f'{phase.upper()}  t {t:6.2f} s', f'supply {volts} V   x{a.speed:g} speed'))
                    v.set_texts(texts)
                    v.cam.lookat[:] = d.subtree_com[1]
                v.sync()
            time.sleep(1.0)


if __name__ == '__main__':
    main()
