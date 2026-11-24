"""Always running on the duck's Pi (the duck-launcher service, from setup_pi.sh): waits for the Xbox controller and starts a mode, so
nothing has to be typed. Idle, it holds no servo and leaves the bus free.

  B           head mode on: head_pad.py (the legs hold where they are, the head on the controller); B again inside it turns it off
  Menu + A    the walk policy: run_policy.py --pad (then A stands it up, B sits it down). Only with --allow-walk: off until the Pi's
              power is proven under load (docs/dynamixel/TROUBLESHOOTING.md, 2026-11-23)

  sudo systemctl status duck-launcher        is it running         journalctl -u duck-launcher -f    what it is doing
  sudo systemctl stop duck-launcher          before running a script by hand that needs the bus (stand_test.py, telemetry.py)
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck.gamepad import EvdevPad  # noqa: E402

PY = sys.executable


def run(args):
    print('starting:', ' '.join(args), flush=True)
    r = subprocess.run([PY, '-u', '-W', 'ignore'] + args, cwd=HERE)
    print(f'ended ({r.returncode})', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-walk', action='store_true', help='Menu + A starts the walk policy')
    ap.add_argument('--walk-args', default='--pad --telemetry --max-volts 6.3', help='for run_policy.py')
    a = ap.parse_args()
    pad = EvdevPad()
    print('launcher: B = head mode' + (', Menu + A = walk policy' if a.allow_walk else ''), flush=True)
    prev, was_lost = set(), True
    while True:
        s = pad.state()
        if s.lost != was_lost:
            was_lost = s.lost
            print('controller ' + ('lost' if s.lost else 'connected'), flush=True)
        new = s.held - prev
        prev = s.held
        started = False
        if not s.lost and 'B' in new and 'Menu' not in s.held:
            run(['head_pad.py'])
            started = True
        elif not s.lost and a.allow_walk and 'A' in new and 'Menu' in s.held:
            run(['run_policy.py'] + a.walk_args.split())
            started = True
        if started:                                         # the press that ended the mode must not start it again
            time.sleep(0.5)
            prev = pad.state().held
        time.sleep(0.05)


if __name__ == '__main__':
    main()
