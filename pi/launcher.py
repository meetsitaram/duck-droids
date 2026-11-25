"""Always running on the duck's Pi (the duck-launcher user service, from install_launcher_user.sh): waits for the Xbox controller and starts a
mode, so nothing has to be typed. Idle, it holds no servo and leaves the bus free. Every combo must be held 1 s (--hold-s), and the
controller buzzes when it takes effect.

  RT + A, 1 s   stand: run_policy.py --pad --stand-only --auto-stand, stand_nod.onnx. It stands up at once (the policy itself, from
                sitting); the right stick and d-pad move the head, X nods, Y the beak, never a walk command. RT + A, 1 s again: it sits down
                and the mode ends. Only with --allow-stand (install_launcher_user.sh sets it)
  RT + X, 1 s   emotions: the same stand on stand_emote.onnx (trained to keep its balance through microduck's 13 emotions) with
                --emotions: LB / RB pick an emotion, X plays it (head, beak, sound). RT + A, 1 s: it sits down and the mode ends.
                Only with --allow-stand
  RB + B, 1 s   head mode, sitting: head_pad.py (the legs hold where they are, the head on the controller). RB + B, 1 s again: off
  LT + A, 1 s   the walk policy: run_policy.py --pad. Only with --allow-walk: off until the power is proven under load
  LB + RB       inside any mode: stop at once, torque off

  systemctl --user status duck-launcher       tail -f ~/duck/launcher.log
  systemctl --user stop duck-launcher         before running a script by hand that needs the bus (stand_test.py, telemetry.py)
"""
import argparse
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck.gamepad import EvdevPad, Holds  # noqa: E402

PY = sys.executable
COMBOS = {'stand': {'RT', 'A'}, 'emote': {'RT', 'X'}, 'head': {'RB', 'B'}, 'walk': {'LT', 'A'}}


class IdleStream:
    """While idle, telemetry.py (read only: servo positions and the IMU) feeds the PC's twin, so it always shows the duck; stopped before a
    mode starts, as the mode needs the bus and the stream's port (and sends its own stream)."""

    def __init__(self, on):
        self.on, self.p = on, None

    def start(self):
        if self.on and self.p is None:
            self.p = subprocess.Popen([PY, '-u', '-W', 'ignore', 'telemetry.py', '--hz', '15'], cwd=HERE,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self.p is not None:
            self.p.send_signal(signal.SIGINT)              # its own clean exit: the port and the bus closed
            try:
                self.p.wait(3)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()
            self.p = None
            time.sleep(0.3)


def run(args):
    print(time.strftime('%H:%M:%S'), 'starting:', ' '.join(args), flush=True)
    r = subprocess.run([PY, '-u', '-W', 'ignore'] + args, cwd=HERE)
    print(time.strftime('%H:%M:%S'), f'ended ({r.returncode})', flush=True)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-walk', action='store_true', help='LT + A starts the walk policy')
    ap.add_argument('--allow-stand', action='store_true', help='RT + A starts the stand policy')
    ap.add_argument('--no-idle-telemetry', action='store_true', help="don't stream the duck's state to the twin while idle")
    ap.add_argument('--hold-s', type=float, default=1.0, help='seconds a combo must be held')
    ap.add_argument('--stand-args', default='--pad --stand-only --auto-stand --model models/stand_bam.onnx --bam --rise 8 --blend 0 --telemetry --max-volts 6.3 --min-volts 4.0',
                    help='for run_policy.py')
    ap.add_argument('--emote-args', default='--pad --stand-only --auto-stand --model models/stand_emote.onnx --bam --rise 8 --blend 0 --telemetry --max-volts 6.3 --min-volts 4.0 --emotions',
                    help='for run_policy.py')
    ap.add_argument('--walk-args', default='--pad --telemetry --max-volts 6.3', help='for run_policy.py')
    a = ap.parse_args()
    pad = EvdevPad()
    combos = {k: v for k, v in COMBOS.items() if k == 'head' or (k in ('stand', 'emote') and a.allow_stand) or (k == 'walk' and a.allow_walk)}
    print('launcher: ' + ', '.join(f"{' + '.join(sorted(v, reverse=True))} held {a.hold_s:g} s = {k}" for k, v in combos.items()), flush=True)
    holds, was_lost = Holds(combos, a.hold_s), True
    idle = IdleStream(not a.no_idle_telemetry)
    idle.start()
    while True:
        s = pad.state()
        if s.lost != was_lost:
            was_lost = s.lost
            print(time.strftime('%H:%M:%S'), 'controller ' + ('lost' if s.lost else 'connected'), flush=True)
        mode = holds.check(s)
        if mode:
            pad.rumble(300)
            idle.stop()
            if mode == 'stand':
                rc = run(['run_policy.py'] + a.stand_args.split() + ['--hold-s', str(a.hold_s)])
            elif mode == 'emote':
                rc = run(['run_policy.py'] + a.emote_args.split() + ['--hold-s', str(a.hold_s)])
            elif mode == 'head':
                rc = run(['head_pad.py', '--hold-s', str(a.hold_s)])
            else:
                rc = run(['run_policy.py'] + a.walk_args.split() + ['--hold-s', str(a.hold_s)])
            if rc != 0:                                     # it failed (no IMU, no servo, low supply...): three short buzzes, see launcher.log
                for _ in range(3):
                    pad.rumble(150, 1.0)
                    time.sleep(0.35)
            # the hold that ended the mode is likely still held: wait for it to be let go, so it can't start the mode again
            while holds.holding(pad.state()):
                time.sleep(0.05)
            holds = Holds(combos, a.hold_s)
            idle.start()
        time.sleep(0.05)


if __name__ == '__main__':
    main()
