"""Always running on the duck's Pi (the duck-launcher user service, from install_launcher_user.sh): waits for the Xbox controller and starts a
mode, so nothing has to be typed. Idle, it holds no servo and leaves the bus free. Every combo must be held 1 s (--hold-s), and the
controller buzzes when it takes effect.

  RT + A, 1 s   stand: run_policy.py --pad --stand-only --auto-stand, stand_nod.onnx. It stands up at once (the policy itself, from
                sitting); the right stick and d-pad move the head, X nods, Y says yes and B no (the beak moving with the sound), never a walk command. RT + A, 1 s again: it sits down
                and the mode ends. Only with --allow-stand (install_launcher_user.sh sets it)
  RT + X, 1 s   emotions: the same stand on stand_emote.onnx (trained to keep its balance through microduck's 13 emotions) with
                --emotions: LB / RB pick an emotion, X plays it (head, beak, sound). RT + A, 1 s: it sits down and the mode ends.
                Only with --allow-stand
  RT + Y, 1 s   the BAM walk: run_policy.py --pad --auto-stand on walk_bam.onnx (milli-rl's walk on Pollen's XL330 model, 2026-11-25).
                It stands up, the left stick walks it (RT held: faster), the right stick turns it. RT + Y again (or RT + A, or B), 1 s: it sits down and the
                mode ends. Only with --allow-stand. In simulation it stays up but follows the speed command poorly: keep a hand near
  RT + B, 1 s   head mode, sitting: head_pad.py (the legs hold where they are, the head on the controller). RT + B, 1 s again: off
  LT + A, 1 s   the walk policy: run_policy.py --pad. Only with --allow-walk: off until the power is proven under load
  LB + RB       inside any mode: stop at once, torque off
  LT + d-pad up / down, 1 s, idle   the Wi-Fi on / off, the speaker saying which. The Wi-Fi breaks up the Bluetooth speaker's
                sound (2026-11-25: the one radio chip; clean with the Wi-Fi off): off while playing with the duck, the USB cable to reach it
  RT + LT + RB + LB, 1 s, idle   shut the Pi down cleanly (a long buzz first); wait for the green light to stop blinking, then unplug.
                Pulling the plug instead risks the card, as a power cut mid-write lost the Wi-Fi settings twice (2026-11-24, -25)

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
COMBOS = {'stand': {'RT', 'A'}, 'emote': {'RT', 'X'}, 'head': {'RT', 'B'}, 'walk': {'LT', 'A'}, 'walkbam': {'RT', 'Y'}, 'shutdown': {'RT', 'LT', 'RB', 'LB'}, 'wifi_on': {'LT', 'UP'}, 'wifi_off': {'LT', 'DOWN'}}


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


def say(name):
    """One of the launcher's spoken sounds (sounds/<name>.wav) on the speaker; nothing if none is connected."""
    subprocess.run(['paplay', os.path.join(HERE, 'sounds', name + '.wav')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wifi_set(pad, on):
    """LT + d-pad up / down: the Wi-Fi radio on / off, the speaker saying which (needs duck_polkit.sh's rule, from setup_pi.sh)."""
    pad.rumble(300)
    if on:
        r = subprocess.run(['nmcli', 'radio', 'wifi', 'on'])
        say('wifi_on')
    else:
        say('wifi_off')
        r = subprocess.run(['nmcli', 'radio', 'wifi', 'off'])
    print(time.strftime('%H:%M:%S'), 'Wi-Fi', 'on' if on else 'off', '' if r.returncode == 0 else '(refused: sudo bash duck_polkit.sh)', flush=True)
    if r.returncode != 0:
        for _ in range(3):
            pad.rumble(150, 1.0)
            time.sleep(0.35)


def run(args):
    print(time.strftime('%H:%M:%S'), 'starting:', ' '.join(args), flush=True)
    r = subprocess.run([PY, '-u', '-W', 'ignore'] + args, cwd=HERE)
    print(time.strftime('%H:%M:%S'), f'ended ({r.returncode})', flush=True)
    return r.returncode


def active_model(args, mode):
    """models/active.json's model for this controller mode in place of the --model in the run_policy.py arguments: that file says which
    model the real duck runs, and so is what it runs (2026-11-25)."""
    import json
    try:
        m = json.load(open(os.path.join(HERE, 'models', 'active.json')))[mode]['model']
    except (OSError, KeyError, ValueError):
        return args
    if not m:
        return args
    parts = args.split()
    if '--model' in parts:
        parts[parts.index('--model') + 1] = 'models/' + m
    else:
        parts += ['--model', 'models/' + m]
    import active_models
    _, st = active_models.check(mode)
    sha = (json.load(open(os.path.join(HERE, 'models', 'active.json')))[mode].get('sha256') or '')[:12]
    note = {'ok': f'sha256 {sha} ok', 'mismatch': f'WARNING: the file is not the one active.json records (sha256 {sha}): a cut-off copy or another '
            'model under that name; bash fetch_models.sh brings the right one', 'missing': 'WARNING: the file is missing',
            'unrecorded': 'no sha256 recorded (python active_models.py --update)'}.get(st, st)
    print(f'{mode}: models/{m} (models/active.json), {note}', flush=True)
    return ' '.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-walk', action='store_true', help='LT + A starts the walk policy')
    ap.add_argument('--allow-stand', action='store_true', help='RT + A starts the stand policy')
    ap.add_argument('--no-idle-telemetry', action='store_true', help="don't stream the duck's state to the twin while idle")
    ap.add_argument('--hold-s', type=float, default=1.0, help='seconds a combo must be held')
    ap.add_argument('--stand-args', default='--pad --stand-only --auto-stand --model models/stand_bam.onnx --bam --rise 8 --blend 0 --telemetry --max-volts 6.3 --min-volts 4.0',
                    help='for run_policy.py')
    ap.add_argument('--emote-args', default='--pad --stand-only --auto-stand --model models/stand_emote_calm.onnx --bam --rise 8 --blend 0 --telemetry --max-volts 6.3 --min-volts 4.0 --emotions',
                    help='for run_policy.py')
    ap.add_argument('--walkbam-args', default='--pad --auto-stand --model models/walk_bam.onnx --bam --rise 8 --blend 0 --telemetry --max-volts 6.3 --min-volts 4.0 --vx-max 0.2 --vx-boost 0.2 --vy-max 0.15',
                    help='for run_policy.py (RT + Y)')
    ap.add_argument('--walk-args', default='--pad --telemetry --max-volts 6.3', help='for run_policy.py')
    a = ap.parse_args()
    a.stand_args, a.emote_args = active_model(a.stand_args, 'stand'), active_model(a.emote_args, 'emote')
    a.walkbam_args = active_model(a.walkbam_args, 'walk_bam')
    pad = EvdevPad()
    combos = {k: v for k, v in COMBOS.items() if k in ('head', 'shutdown', 'wifi_on', 'wifi_off') or (k in ('stand', 'emote', 'walkbam') and a.allow_stand) or (k == 'walk' and a.allow_walk)}
    print('launcher: ' + ', '.join(f"{' + '.join(sorted(v, reverse=True))} held {a.hold_s:g} s = {k}" for k, v in combos.items()), flush=True)
    holds, was_lost = Holds(combos, a.hold_s, exact=True), True
    idle = IdleStream(not a.no_idle_telemetry)
    idle.start()
    while True:
        s = pad.state()
        if s.lost != was_lost:
            was_lost = s.lost
            print(time.strftime('%H:%M:%S'), 'controller ' + ('lost' if s.lost else 'connected'), flush=True)
        mode = holds.check(s)
        if mode in ('wifi_on', 'wifi_off'):
            wifi_set(pad, mode == 'wifi_on')
            while holds.holding(pad.state()):
                time.sleep(0.05)
            holds = Holds(combos, a.hold_s, exact=True)
            mode = None
        if mode == 'shutdown':
            print(time.strftime('%H:%M:%S'), 'shutting down (RT + LT + RB + LB)', flush=True)
            idle.stop()
            say('shutting_down')
            pad.rumble(1200, 1.0)
            time.sleep(1.5)
            r = subprocess.run(['systemctl', 'poweroff'])
            if r.returncode != 0:                           # not allowed (no polkit rule: setup_pi.sh writes it): three short buzzes
                print('poweroff refused: sudo bash setup_pi.sh, or the polkit rule in it', flush=True)
                for _ in range(3):
                    pad.rumble(150, 1.0)
                    time.sleep(0.35)
                idle.start()
            mode = None
        if mode:
            pad.rumble(300)
            idle.stop()
            if mode == 'stand':
                rc = run(['run_policy.py'] + a.stand_args.split() + ['--hold-s', str(a.hold_s)])
            elif mode == 'emote':
                rc = run(['run_policy.py'] + a.emote_args.split() + ['--hold-s', str(a.hold_s)])
            elif mode == 'walkbam':
                rc = run(['run_policy.py'] + a.walkbam_args.split() + ['--hold-s', str(a.hold_s)])
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
            holds = Holds(combos, a.hold_s, exact=True)
            idle.start()
        time.sleep(0.05)


if __name__ == '__main__':
    main()
