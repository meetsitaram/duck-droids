"""A trained policy on the real duck: the legs ease it up from sitting (as stand_test.py), the policy runs at 50 Hz through a script of
commands (stand, walk segments, head moves), then the legs ease it back down. Either kind of exported policy (trainer/export_slop.py):

  IMU policies (61 inputs: walk_imu, walk_style): on the Pi, with the BNO085. Stops if the body tips past --max-tilt.
  blind policies (433 inputs: walk_blind and the stand ones): tethered to the PC, no IMU and so no fall sensor.
Someone keeps a hand just behind the duck the whole time.

  python run_policy.py --imu-check                                   torque off: prints the IMU's gravity and gyro while you tilt the duck
  python run_policy.py --model models/walk_style.onnx --walk 0.1,0,0,4          stand 5 s, walk 0.1 m/s forward 4 s, stand, lower
  python run_policy.py --model models/walk_style.onnx --walk 0.1,0,0,3 --walk 0,0,0.5,3     forward, then turn in place
  python run_policy.py --model models/walk_blind.onnx --nods 2       blind: stand still and nod (tethered)
  python run_policy.py --port socket://127.0.0.1:9000 --imu 127.0.0.1:9001 --max-volts 9 ...   against the simulator (sim/server.py)
  python run_policy.py --pad                                         driven from the Xbox controller (below), until Menu
  python run_policy.py --pad-check                                   no servos: prints the commands the controller would give

With --pad the duck waits, sitting with torque on, for the controller:
  A          stand up (the scripted rise), then the policy runs
  left stick walk: up/down forward and back, left/right sideways      right stick, left/right: turn
  RT         held, walks faster, up to --vx-boost                    d-pad: the head, up/down pitch, left/right turn
  X          a nod                                                    Y: says yes, B: says no (stand mode: the beak moves with the sound)
  with --emotions (a stand policy, models/stand_emote.onnx): RB / LB play the next / previous of microduck's 13 emotions (printed, a
  short buzz; pressed during one, it plays when that ends), X the same one again. Each plays its head motion through the policy's head command (as it trained), its beak straight to the beak servo, its sound on the
  speaker, all from the same start. The d-pad and stick don't steer the head while it plays; it ends back at the standing pose.
  B          sit down (the scripted lower; stand mode: says no), then waits for A again   Menu (while sitting): quit
  LB + RB    stop: eases down at once, torque off, quit. If the controller drops for --pad-lost seconds while standing, it sits down.

The bus board over USB, jumpers at B, the port found by itself (on the Pi: its micro USB data port and an OTG cable, docs/dynamixel/WIRING.md;
with the board on the Pi's UART instead, jumpers at A and --port /dev/serial0).

Safety (as stand_test.py): current-based position mode with each servo's current capped (--cap for the legs, 600 mA head, 300 beak);
torque comes on with every goal where its joint is; a hardware error, a low supply, a joint lagging its goal by more than --max-lag, a leg
goal more than --leg-range from the standing pose, or Ctrl-C stops the policy and eases the duck back down to where it started (sitting) before
the torque goes off. Every tick is logged to --log as CSV, with what the policy saw and did, for comparing against the sim.
"""
import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from stand_test import BEAK, CAP, GOAL_CURRENT, HEAD, HW_ERROR, LED, LEGS, MODE_CURRENT_POSITION, POSITION_D, at  # noqa: E402

K = 2 * math.pi / dxl.TICKS_PER_REV
RATE = 50.0
MAX_MISSES = 5     # bus reads missed in a row before the run stops (each stands in with the last reading)


def head_script(a):
    """[(seconds, (neck_pitch, head_pitch, head_yaw, head_roll))]: the head command over time, off the standing pose, eased between keys."""
    # each key: (seconds, (vx, vy, wz, neck_pitch, head_pitch, head_yaw, head_roll)); walk segments get a second to speed up and to slow down
    z = (0.0, 0.0, 0.0, 0.0)
    still = (0.0, 0.0, 0.0)
    keys = [(a.settle, still + z)]
    for seg in a.walk:
        vx, vy, wz, secs = (float(v) for v in seg.split(','))
        keys += [(1.0, (vx, vy, wz) + z), (secs, (vx, vy, wz) + z), (1.0, still + z), (1.5, still + z)]
    head = []
    for _ in range(a.nods):                                  # nods: the head pitch, small and slow (front to back moves tip the duck)
        head += [(a.nod_s, (0.0, a.nod, 0.0, 0.0)), (a.nod_s, (0.0, -a.nod, 0.0, 0.0)), ]
    if a.nods:
        head += [(a.nod_s, z)]
    for _ in range(a.nods):                                  # the neck: the whole head forward and back a little
        head += [(a.nod_s, (-a.neck, 0.0, 0.0, 0.0)), (a.nod_s, (a.neck, 0.0, 0.0, 0.0))]
    if a.nods:
        head += [(a.nod_s, z)]
    for _ in range(a.turns):                                 # side to side: barely moves the weight
        head += [(a.nod_s, (0.0, 0.0, a.turn, 0.0)), (a.nod_s, (0.0, 0.0, -a.turn, 0.0))]
    if a.turns:
        head += [(a.nod_s, z)]
    keys += [(d, still + h) for d, h in head] + [(a.hold, still + z)]
    return keys


def head_at(keys, t):
    prev = (0.0,) * 7
    for dur, k in keys:
        if t < dur:
            s = t / dur
            s = s * s * (3 - 2 * s)
            return tuple(p + s * (q - p) for p, q in zip(prev, k))
        t -= dur
        prev = k
    return None


class PiPower:
    """The Pi's own undervoltage flag (vcgencmd get_throttled), read twice a second in a thread: bit 0 = under 4.63 V now, bit 16 = since boot.
    A reboot clears it, so it is logged every tick: the first stand (2026-11-23) rebooted the Pi as the policy took over, leaving no trace."""

    def __init__(self):
        import shutil
        import subprocess
        import threading
        self.value = None
        self.ok = shutil.which('vcgencmd') is not None
        if not self.ok:
            return

        def run():
            while True:
                try:
                    out = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True, timeout=1).stdout
                    self.value = int(out.strip().split('=')[1], 16)
                except Exception:                         # noqa: BLE001
                    pass
                time.sleep(0.5)
        threading.Thread(target=run, daemon=True).start()

    def under_now(self):
        return self.value is not None and bool(self.value & 0x1)

    def under_since_boot(self):
        return self.value is not None and bool(self.value & 0x10000)


class PadDriver:
    """The controller to commands, (vx, vy, wz, neck_pitch, head_pitch, head_yaw, head_roll), each tick, and the button presses as events."""

    NOD = [(0.5, 0.15), (0.6, -0.12), (0.5, 0.0)]          # (seconds, head pitch): one nod, eased between

    # the emotion head commands are clipped as the stand_emote policy trained on them (milli-rl emotion_head.py LIMITS): neck, head pitch,
    # yaw, roll off the standing pose; the roll 0.04 short of its +-0.24 stop
    EMOTE_LIMITS = {'neck_pitch': (-1.6, 0.15), 'head_pitch': (-1.6, 1.6), 'head_yaw': (-2.5, 2.5), 'head_roll': (-0.20, 0.20)}

    def __init__(self, a, cfg=None):
        from duck.gamepad import Holds, open_pad
        self.a = a
        self.emotions, self.sel, self.emo, self.beak_goal, self.queued = None, 0, None, None, False
        self.say, self._beak_tracks = None, {}
        self.standing = False                               # set by the main loop: emotions play only under the policy
        if getattr(a, 'emotions', False):
            import emote
            from duck import sound
            self.sound = sound
            cfg = cfg or emote.load_config()
            self.home = cfg['home']
            self.emotions = [(n, emote.track(n, cfg, a.emote_scale)[0]) for n in emote.names()]
            self.sample = emote.sample
            print('emotions: LB / RB to pick, X to play: ' + ', '.join(n for n, _ in self.emotions), flush=True)
        self.pad = open_pad(a.pad, a.pad_name)
        self.holds = Holds({'STANDSIT': {'RT', 'A'}}, a.hold_s)     # RT + A held 1 s: stand up, or sit back down; the controller buzzes
        self.prev = set()
        self.walk = np.zeros(3)
        self.beak_open = False
        self.nod_t = None
        self.lost_since = None

    def tick(self, dt=1 / RATE):
        """-> (cmd, events, seconds lost); events are the buttons pressed since the last tick, with LB+RB together as STOP"""
        from duck.gamepad import deadzone
        a = self.a
        s = self.pad.state()
        now = time.monotonic()
        if s.lost:
            self.lost_since = self.lost_since or now
        else:
            self.lost_since = None
        new = s.held - self.prev
        self.prev = s.held
        events = set(new)
        h = self.holds.check(s)
        if h:
            events.add(h)
            self.pad.rumble(300)
        if {'LB', 'RB'} <= s.held and new & {'LB', 'RB'}:
            events.add('STOP')
        ax = s.axes
        speed = a.vx_max + ax['rt'] * (a.vx_boost - a.vx_max)
        want = np.array([deadzone(ax['ly']) * speed, deadzone(ax['lx']) * a.vy_max, deadzone(ax['rx']) * a.wz_max])
        if a.stand_only:                                    # a stand policy: no walk command ever; the right stick steers the head instead
            want[:] = 0.0
        step = np.array([a.accel, a.accel, 4 * a.accel]) * dt
        self.walk += np.clip(want - self.walk, -step, step)
        if self.emotions:
            if events & {'LB', 'RB'} and 'STOP' not in events:      # RB / LB: the next / previous one; it plays now, or when one playing ends
                self.sel = (self.sel + (1 if 'RB' in events else -1)) % len(self.emotions)
                print(f'emotion: {self.emotions[self.sel][0]}', flush=True)
                self.pad.rumble(60, 0.3)
                self.queued = True
            if 'X' in events:                                       # X: the same one again
                self.queued = True
            if not self.standing:                                   # presses before it stands (or while it sits) don't wait to play later
                self.queued = False
            if self.queued and self.emo is None and self.standing:
                self.queued = False
                name, tr = self.emotions[self.sel]
                self.emo = (name, tr, now + self.a.audio_lead)     # the motion starts audio_lead after the sound: the speaker's lag
                self.sound.play(name)
                print(f'playing {name} ({tr[-1][0]:.1f} s)', flush=True)
        elif 'X' in events and self.nod_t is None:
            self.nod_t = now
        talk = {'Y': 'yes', 'B': 'no'} if a.stand_only and not self.emotions else {}
        for b, word in talk.items():                        # stand mode: Y says yes, B no, the beak moving with the sound (the user, 2026-11-25)
            if b in events and self.standing and self.say is None:
                self.say = (word, self.beak_track(word), now + a.audio_lead)
                self.sound_mod().play(word)
                print(f'saying {word}', flush=True)
        if 'Y' in events and not talk:
            self.beak_open = not self.beak_open
        pitch = ax['dy'] * a.head_max
        yaw = ax['dx'] * a.head_max
        if a.stand_only:
            pitch = float(np.clip(pitch + deadzone(ax['ry']) * a.head_max, -a.head_max, a.head_max))
            yaw = float(np.clip(yaw + deadzone(ax['rx']) * a.head_max, -a.head_max, a.head_max))
        if self.nod_t is not None:
            nod = head_at([(d, (0.0, 0.0, 0.0, 0.0, q, 0.0, 0.0)) for d, q in self.NOD], now - self.nod_t)
            if nod is None:
                self.nod_t = None
            else:
                pitch += nod[4]
        head = (0.0, pitch, yaw, 0.0)
        self.beak_goal = None
        if self.say is not None:
            word, tr, t0 = self.say
            if now - t0 > tr[-1][0] + 0.2 or not self.standing:
                self.say = None
            elif now >= t0:
                self.beak_goal = float(self.sample_fn()(tr, now - t0)['beak'])
        if self.emo is not None:
            name, tr, t0 = self.emo
            if now - t0 > tr[-1][0] + 0.3 or not self.standing:
                self.emo = None
                if not self.standing:
                    self.sound.stop()
            elif now >= t0:
                q = self.sample(tr, now - t0)
                head = tuple(float(np.clip(q[j] - self.home.get(j, 0.0), *self.EMOTE_LIMITS[j])) for j in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'))
                self.beak_goal = float(q['beak'])
        cmd = (float(self.walk[0]), float(self.walk[1]), float(self.walk[2])) + head
        return cmd, events, (now - self.lost_since) if self.lost_since else 0.0

    def sound_mod(self):
        from duck import sound
        return sound

    def sample_fn(self):
        import emote
        return emote.sample

    def beak_track(self, word):
        """The word's beak, from its emotion's mouth keyframes (emote.py's mapping), cached."""
        if word not in self._beak_tracks:
            import emote
            self._beak_tracks[word] = emote.track(word, emote.load_config())[0]
        return self._beak_tracks[word]

    def stop_walk(self):
        self.walk[:] = 0.0


def pad_check(a):
    a.pad = a.pad or 'evdev'
    d = PadDriver(a)
    print('the controller commands (no servos); Ctrl-C to stop')
    last = None
    try:
        while True:
            cmd, ev, lost = d.tick()
            line = (f'LOST {lost:.1f} s' if lost else 'ok') + f'  vx {cmd[0]:+.3f} vy {cmd[1]:+.3f} wz {cmd[2]:+.2f}  head pitch {cmd[4]:+.2f} yaw {cmd[5]:+.2f}  beak {"open" if d.beak_open else "shut"}'
            if ev:
                print('pressed:', ' '.join(sorted(ev)), flush=True)
            if line != last:
                print(line, flush=True)
                last = line
            time.sleep(1 / RATE)
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--model', default=os.path.join(HERE, 'models', 'walk_style.onnx'))
    ap.add_argument('--imu', default='bno085', help='bno085 (the Pi), or host:port for the simulator; IMU policies only')
    ap.add_argument('--imu-check-s', type=float, default=30.0)
    ap.add_argument('--imu-check', action='store_true', help='torque off: print the IMU gravity and gyro for 30 s while you tilt the duck, then stop')
    ap.add_argument('--walk', action='append', default=[], help='a walk segment vx,vy,wz,seconds (m/s, m/s, rad/s); repeatable, in order')
    ap.add_argument('--imu-stale', type=float, default=0.2, help='IMU policies: stop if the IMU has given nothing new for this long, s')
    ap.add_argument('--max-tilt', type=float, default=35.0, help='IMU policies: stop if the body tips past this, deg')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--rise', type=float, default=8.0, help='seconds from sitting to the standing pose, scripted')
    ap.add_argument('--lower', type=float, default=8.0, help='seconds back down at the end, scripted')
    ap.add_argument('--settle', type=float, default=5.0, help='seconds of the policy standing before the head moves')
    ap.add_argument('--hold', type=float, default=5.0, help='seconds of the policy standing after the head moves')
    ap.add_argument('--nods', type=int, default=0, help='how many nods (head pitch) and neck rocks; 0 for stand only')
    ap.add_argument('--turns', type=int, default=0, help='how many side to side turns of the head')
    ap.add_argument('--nod', type=float, default=0.15, help='rad, head pitch each way')
    ap.add_argument('--neck', type=float, default=0.10, help='rad, neck pitch each way')
    ap.add_argument('--turn', type=float, default=0.3, help='rad, head yaw each way')
    ap.add_argument('--nod-s', type=float, default=1.2, help='seconds per move')
    ap.add_argument('--cap', type=int, default=800, help='current cap per leg servo, mA (head 600, beak 300). The policy trained on 0.30-0.52 N m: 800 mA is about 0.28')
    ap.add_argument('--leg-gain', type=int, default=800, help='position P: the gains the policy trained at (walk_blind.json trained_position_p)')
    ap.add_argument('--neck-gain', type=int, default=1200)
    ap.add_argument('--head-gain', type=int, default=600)
    ap.add_argument('--head-damping', type=int, default=300, help='position D for the head and beak, as stand_test.py (the neck 100, legs 0)')
    ap.add_argument('--blend', type=float, default=1.5, help='seconds over which the policy output is eased in after the scripted rise')
    ap.add_argument('--leg-range', type=float, default=3.0, help='rad: stop if a leg goal goes further than this from the standing pose. Off by default: at these low gains a policy asks for torque with big goals (1.6 rad in the sim, standing), the joint limits clip every goal and the current cap limits the torque')
    ap.add_argument('--bam', action='store_true', help="the servos as milli-rl's *-Bam tasks train them (Pollen's XL330 model): position mode 3, P 800 legs / 1200 neck / 600 head, D 0, no current cap")
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--low-volts-reads', type=int, default=2, help='readings in a row (one each 0.5 s) under --min-volts before it stops: a brief dip is ridden out')
    ap.add_argument('--max-volts', type=float, default=6.0)
    ap.add_argument('--max-lag', type=float, default=20.0, help='degrees a joint may trail its goal in the scripted rise and lower (not under the policy, whose goals run well past where the joints get)')
    ap.add_argument('--abort-lower', type=float, default=8.0)
    ap.add_argument('--log', default=os.path.join(HERE, 'run_policy_log.csv'))
    ap.add_argument('--pad', nargs='?', const='evdev', default=None, help='drive it from the gamepad (evdev: the Xbox controller), or a test script for the simulator (duck/gamepad.py ScriptPad)')
    ap.add_argument('--pad-name', default='Xbox', help='part of the controller input device name')
    ap.add_argument('--telemetry', type=int, nargs='?', const=9100, default=None, help='send the servo readings and IMU to the PC twin on this port (python twin.py --remote <pi>)')
    ap.add_argument('--pad-check', action='store_true', help='no servos: print the commands the controller gives, for checking the mapping')
    ap.add_argument('--vx-max', type=float, default=0.12, help='m/s forward or back at full stick, RT released')
    ap.add_argument('--vx-boost', type=float, default=0.2, help='m/s at full stick with RT fully held')
    ap.add_argument('--vy-max', type=float, default=0.08, help='m/s sideways at full stick')
    ap.add_argument('--wz-max', type=float, default=0.8, help='rad/s turning at full stick')
    ap.add_argument('--head-max', type=float, default=0.3, help='rad of head pitch or turn from the d-pad')
    ap.add_argument('--accel', type=float, default=0.4, help='m/s per s (4x that in rad/s per s for turning): how fast the walk command may change')
    ap.add_argument('--grav-bias', type=float, default=0.0, help='debugging, simulator: deg of pitch bias added to the IMU gravity the policy sees (a miscalibrated IMU)')
    ap.add_argument('--risen-hold', type=float, default=3.0, help='seconds the scripted standing pose is held after the rise (steadied by hand) before the policy takes over; a tick buzz each second')
    ap.add_argument('--handover-tilt', type=float, default=30.0, help='deg: the policy takes over only with the body this upright. In the simulator, unheld, stand_nod recovered from 5 and 10 deg and fell from 15 (2026-11-24); 30 is for handing over while still held by hand until it is steady (the user\'s choice)')
    ap.add_argument('--imu-wait', type=float, default=10.0, help='seconds to hold the risen pose for the IMU to report and the body to be upright before the policy takes over; then it sits')
    ap.add_argument('--rise-to', help="a pose JSON (poses/sit_trained.json): the scripted --rise goes to its legs instead of the standing pose, then the policy takes over. For the real duck's deep sit (knees 88 deg), past what the policy trained on (2026-11-24)")
    ap.add_argument('--rise-slew', type=float, default=0.0, help='deg/s: for the first --rise-slew-s seconds of the policy, its leg goals change at most this fast (a slower rise); 0 off')
    ap.add_argument('--rise-slew-s', type=float, default=4.0)
    ap.add_argument('--rise-model', help='a sit/stand policy (models/sitstand2.onnx) that stands it up from sitting for --rise-policy-s, then --model takes over; use with --rise 0 --blend 0')
    ap.add_argument('--rise-policy-s', type=float, default=6.0, help='seconds of --rise-model after A')
    ap.add_argument('--auto-stand', action='store_true', help='with --pad: stand up at once (the launcher has already had RT + A), and end when it sits down')
    ap.add_argument('--emotions', action='store_true', help="with --pad and a stand policy (models/stand_emote.onnx): LB / RB pick one of microduck's emotions, X plays it (head through the policy, beak, sound)")
    ap.add_argument('--audio-lead', type=float, default=0.3, help="s the sound starts before an emotion's motion: the Bluetooth speaker's lag and the player's start")
    ap.add_argument('--emote-scale', type=float, default=1.0, help='every emotion move scaled by this (the policy trained on 0.7-1.0)')
    ap.add_argument('--hold-s', type=float, default=1.0, help='seconds a controller combo (RT + A) must be held')
    ap.add_argument('--stand-only', action='store_true', help='with --pad: never send a walk command (for the stand policies, stand_nod.onnx); the right stick and d-pad move the head')
    ap.add_argument('--pad-lost', type=float, default=1.0, help='seconds without the controller, standing, before it sits down')
    a = ap.parse_args()
    if a.pad_check:
        pad_check(a)
        return

    import onnxruntime as ort
    lay = json.load(open(os.path.splitext(a.model)[0] + '.json'))
    names = lay['joint_order']
    stand = np.array([lay['standing_pose_rad'][n] for n in names])
    blocks = {b['name']: b for b in lay['blocks']}
    H = blocks['joint_pos']['history']
    IMU = 'projected_gravity' in blocks
    order = [b['name'] for b in lay['blocks']]
    want = ['base_ang_vel', 'projected_gravity', 'joint_pos', 'joint_vel', 'actions'] if IMU else ['joint_pos', 'joint_vel', 'actions']
    dv = blocks['joint_vel']['delay_steps']        # this loop gives the policy the speeds one tick old: inside what it trained on (the *-Bam stand: 1-2)
    assert dv[0] <= 1 <= dv[1] and order[:len(want)] == want, (order, dv)
    print(f"{os.path.basename(a.model)}: {lay['inputs']} inputs, {'IMU' if IMU else 'blind'}, from {lay['checkpoint']}")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    sess = ort.InferenceSession(a.model, opts, providers=['CPUExecutionProvider'])
    inp = sess.get_inputs()[0].name
    rise_sess = None
    if a.rise_model:                                         # a second policy that stands it up from sitting (the sit/stand skill), then hands over
        rlay = json.load(open(os.path.splitext(a.rise_model)[0] + '.json'))
        assert rlay['joint_order'] == names and rlay['inputs'] == lay['inputs'] and rlay['standing_pose_rad'] == lay['standing_pose_rad'], \
            "the rise model must share the main model's joints, inputs and standing pose"
        rise_sess = ort.InferenceSession(a.rise_model, opts, providers=['CPUExecutionProvider'])
        print(f"rise: {os.path.basename(a.rise_model)} for {a.rise_policy_s:.0f} s, from {rlay['checkpoint']}")

    cfg = load_config(a.config)
    imu = None
    if IMU or a.imu_check:
        from duck.hardware import Bno085, SimImu
        imu = Bno085(cfg) if a.imu == 'bno085' else SimImu(a.imu)
    if a.imu_check:                                          # nose down should give gravity +x, left side down +y; level (0, 0, -1)
        t1 = time.monotonic()
        while time.monotonic() - t1 < a.imu_check_s:
            gyro, g = imu.read()
            tilt = math.degrees(math.acos(max(-1.0, min(1.0, -g[2]))))
            print(f'gravity {g[0]:+.2f} {g[1]:+.2f} {g[2]:+.2f}  (tilt {tilt:4.1f} deg)   gyro {gyro[0]:+.2f} {gyro[1]:+.2f} {gyro[2]:+.2f} rad/s'
                  f'   age {getattr(imu, "age", 0) * 1000:3.0f} ms, bad packets {getattr(imu, "errors", 0)}, restarts {getattr(imu, "restarts", 0)}', flush=True)
            time.sleep(0.2)
        return
    lim = np.array([cfg['limits'][n] for n in names])
    J = names + BEAK
    port = find_port() if a.port == 'auto' else a.port
    bus = dxl.Bus(port, timeout=0.05)
    ids = [cfg['joints'][n]['id'] for n in J]
    sign = {n: cfg['joints'][n]['direction'] for n in J}
    cap = {n: CAP['head'] if n in HEAD else CAP['beak'] if n in BEAK else a.cap for n in J}
    for i in ids:
        if not bus.ping(i):
            raise SystemExit(f'servo {i} does not answer')
    volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
    print(f'supply {volts:.1f} V')
    if volts > a.max_volts or volts < a.min_volts:
        raise SystemExit(f'{volts:.1f} V: needs {a.min_volts}-{a.max_volts} V')
    for n, i in zip(J, ids):
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        head = n in HEAD + BEAK and n != 'neck_pitch'
        if a.bam and n not in BEAK:
            # a policy trained on Pollen's measured XL330 model (BAM m6, milli-rl's *-Bam tasks): plain position mode, PWM-driven, the P it trained
            # with (legs 800, neck 1200, head 600) and no D, as BAM models the firmware; the current cap of mode 5 doesn't apply there
            bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
            bus.write(i, dxl.POSITION_P, 1200 if n == 'neck_pitch' else 600 if head else 800)
            bus.write(i, POSITION_D, 0)
        else:
            bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
            bus.write(i, GOAL_CURRENT, cap[n])
            bus.write(i, dxl.POSITION_P, a.neck_gain if n == 'neck_pitch' else a.head_gain if head else a.leg_gain)
            bus.write(i, POSITION_D, 100 if n == 'neck_pitch' else a.head_damping if head else 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)

    last_pos, last_state, misses = {}, [None], [0]

    def read_state():
        # a missed status packet (2026-11-24: one, at the hand-off to the policy, crashed the run and dropped the duck): the last reading stands
        # in for it. MAX_MISSES in a row (100 ms at 50 Hz) raise, naming the servos that no longer answer, and the run eases down from there
        try:
            raw = bus.sync_read(ids, 126, 10)              # current 2, velocity 4, position 4
            misses[0] = 0
        except dxl.DxlError as e:
            misses[0] += 1
            print(f'bus read missed ({e}): using the last reading ({misses[0]} in a row)', flush=True)
            if last_state[0] is not None and misses[0] < MAX_MISSES:
                return last_state[0]
            gone = []
            for n, i in zip(J, ids):
                try:
                    if not bus.ping(i):
                        gone.append(n)
                except dxl.DxlError:
                    gone.append(n)
            raise dxl.DxlError(f'bus read failed {misses[0]} times in a row; not answering: {", ".join(gone) or "none (all answer a ping)"}')
        cur, vel, pos = {}, {}, {}
        for n, i in zip(J, ids):
            b = raw[i]
            cur[n] = int.from_bytes(b[0:2], 'little', signed=True)
            vel[n] = int.from_bytes(b[2:6], 'little', signed=True) * dxl.VELOCITY_UNIT * sign[n]
            pos[n] = int.from_bytes(b[6:10], 'little', signed=True)
        last_pos.update(pos)
        last_state[0] = (cur, vel, pos)
        return cur, vel, pos

    _, _, p0 = read_state()
    q0 = {n: ((p0[n] - cfg['joints'][n]['centre'] + 2048) % 4096 - 2048) * K * sign[n] for n in J}

    def angle(pos, n):                                      # from the first reading, so a joint at the 0/4095 wrap can't jump a turn
        return q0[n] + (pos[n] - p0[n]) * sign[n] * K

    def goal_ticks(q):
        return [p0[n] + int(round((q[n] - q0[n]) * sign[n] / K)) for n in J]

    standing = {n: float(stand[k]) for k, n in enumerate(names)}
    standing['beak'] = 0.02                                 # just short of shut
    keys = head_script(a)
    total = sum(k[0] for k in keys)
    print('from  ' + '  '.join(f'{n}:{math.degrees(q0[n]):+.0f}' for n in LEGS))
    print('stand ' + '  '.join(f'{n}:{math.degrees(standing[n]):+.0f}' for n in LEGS))
    pad = PadDriver(a, cfg) if a.pad else None
    pub = None
    if a.telemetry:
        from duck.telemetry import Publisher
        pub = Publisher(a.telemetry)
    if pad:
        print('gamepad: ' + ('standing up now; RT + A held 1 s sits down and ends' if a.auto_stand else
              'RT + A held 1 s stands up and sits down' + ('' if a.stand_only else ' (or A and B)') + ', Menu (sitting) quits') + ', LB+RB stops')
    else:
        print(f'rise {a.rise:.0f} s, policy {total:.0f} s (walk segments: {a.walk or None}; head: {a.nods} nods, {a.nods} neck rocks, {a.turns} turns), lower {a.lower:.0f} s')

    bus.sync_write(ids, dxl.GOAL_POSITION, [p0[n] for n in J])
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)
        bus.write(i, LED, 1)
    if os.path.exists(a.log):                     # keep the last runs: the one before is moved to logs/, named by when it ended (2026-11-25:
        old = os.path.join(os.path.dirname(a.log), 'logs')     # a fall's log was overwritten by the next try)
        os.makedirs(old, exist_ok=True)
        os.replace(a.log, os.path.join(old, 'run_policy_' + time.strftime('%Y%m%d-%H%M%S', time.localtime(os.path.getmtime(a.log))) + '.csv'))
        for f in sorted(os.listdir(old))[:-30]:   # the last 30
            os.remove(os.path.join(old, f))
    log = open(a.log, 'w', newline='')
    w = csv.writer(log)
    pi_power = PiPower()
    w.writerow(['t', 'phase', 'volts', 'pi_throttled'] + [f'{n}_{k}' for n in names for k in ('goal', 'q', 'qd', 'act', 'mA')] + ['cmd_vx', 'cmd_vy', 'cmd_wz', 'cmd_neck', 'cmd_head', 'cmd_yaw', 'cmd_roll', 'grav_x', 'grav_y', 'grav_z', 'gyro_x', 'gyro_y', 'gyro_z'])
    t0 = time.monotonic()
    hw, stopped, peak = {}, None, {n: 0 for n in names}
    low_reads = 0
    hist_q, hist_v, hist_a = np.zeros((H, 14), np.float32), np.zeros((H, 14), np.float32), np.zeros((H, 14), np.float32)
    v_prev = np.zeros(14, np.float32)
    last_act = np.zeros(14, np.float32)
    phase, here, tick, last_print, t_pol, g_prev = ('wait' if pad and not a.auto_stand else 'rise'), None, 0, -1, None, None
    t_rise = 0.0
    sitting = {n: q0[n] for n in J}
    rise_target = dict(standing)
    imu_wait_t = imu_ok_since = t_risen = None
    if a.rise_to:                                            # a crouch the policy trained from (the sit/stand reset), legs only: the policy stands from there
        rise_target.update({n: v for n, v in json.load(open(a.rise_to)).items() if n in LEGS})
    nxt = time.monotonic()

    def lower_from(pos, secs, label):
        here = {n: angle(pos, n) for n in J}
        back = [(secs, {n: q0[n] for n in J})]
        t1 = time.monotonic()
        while True:
            _, qb = at(back, here, time.monotonic() - t1)
            if qb is None:
                break
            try:
                bus.sync_write(ids, dxl.GOAL_POSITION, goal_ticks(qb))
            except dxl.DxlError as e:
                print(f'during the {label}:', e)
            time.sleep(1 / RATE)

    try:
        while True:
            t = time.monotonic() - t0
            cur, vel, pos = read_state()
            q = np.array([angle(pos, n) for n in names], np.float32)
            qd = np.array([vel[n] for n in names], np.float32)
            if tick % 25 == 0:
                volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
                low_reads = low_reads + 1 if volts < a.min_volts else 0      # read every 0.5 s: a stop needs --low-volts-reads in a row
                raw = bus.sync_read(ids, HW_ERROR[0], 1)
                hw = {n: raw[i][0] for n, i in zip(J, ids)}
            cmd = (0.0,) * 7
            gyro, grav = imu.read() if imu is not None else (np.zeros(3), np.array([0.0, 0.0, -1.0]))
            tilt = math.degrees(math.acos(max(-1.0, min(1.0, -float(grav[2])))))
            events, lost = set(), 0.0
            if pad:
                pad.standing = phase == 'policy'
                pcmd, events, lost = pad.tick()
            if phase == 'wait':
                g = sitting
                act = np.zeros(14, np.float32)
                if 'Menu' in events or 'STOP' in events:
                    break
                if (('A' in events and not a.stand_only) or 'STANDSIT' in events) and lost == 0.0:
                    phase, t_rise, g_prev = 'rise', t, None
                    pad.stop_walk()
                    print('standing up', flush=True)
            if phase == 'rise':
                _, g = at([(a.rise, rise_target)], q0, t - t_rise)
                if g is None and t_risen is None:
                    t_risen = t
                if g is None and t - t_risen < a.risen_hold:  # risen: hold the standing pose a few seconds, steadied by hand, before the hand-over
                    g = rise_target
                    if pad and int(t - t_risen) != int(t - t_risen - 1 / RATE):
                        pad.pad.rumble(80, 0.5)
                elif g is None and IMU and imu is not None and (getattr(imu, 'age', 0.0) > 0.05 or tilt > a.handover_tilt):
                    # risen, but the IMU isn't reporting (it restarts itself after a dropout, about 1 s): hold the pose, still held by hand,
                    # until it has been back for a moment; the policy can't balance blind (2026-11-24: it dropped at 7 s of an 8 s rise)
                    g, imu_ok_since = rise_target, None
                    if pad and imu_wait_t is not None and int(t - imu_wait_t) != int(t - imu_wait_t - 1 / RATE):
                        pad.pad.rumble(80, 0.5)             # a tick each second: straighten it up; the long buzz is the hand-over
                        print(f'  waiting: tilt {tilt:.0f} deg, IMU age {getattr(imu, "age", 0.0):.2f} s', flush=True)
                    if imu_wait_t is None:
                        imu_wait_t = t
                        print(f'risen, waiting for the IMU and the body upright (under {a.handover_tilt:.0f} deg, now {tilt:.0f}) before handing over (keep holding)', flush=True)
                    elif t - imu_wait_t > a.imu_wait:
                        why_imu = f'IMU silent or body tilted {tilt:.0f} deg {a.imu_wait:.0f} s after the rise'
                        print(why_imu + ': sitting down', flush=True)
                        lower_from(pos, a.lower, 'lower')
                        stopped = (round(t, 1), phase, why_imu)
                        phase = 'wait'
                        break
                elif g is None and IMU and imu is not None and imu_wait_t is not None and (imu_ok_since is None or t - imu_ok_since < 0.5):
                    imu_ok_since = imu_ok_since if imu_ok_since is not None else t      # back: 0.5 s of good readings first
                    g = rise_target
                elif g is None:
                    phase, t_pol = 'policy', t
                    g = standing
                    if pad:                                   # the scripted rise is done: a long buzz, let go, the policy balances it now
                        pad.pad.rumble(700, 1.0)
                        print('risen: the policy takes over (let go)', flush=True)
                    hist_q[:] = q - stand                 # the history starts full of this moment, as an episode's first step does
                    hist_v[:] = 0.0
                    hist_a[:] = 0.0
                act = np.zeros(14, np.float32)
            if phase == 'policy':
                if pad:
                    cmd = pcmd
                    sit = ('B' in events and not a.stand_only) or 'STANDSIT' in events
                    if sit or lost > a.pad_lost:
                        print('sitting down' if sit else f'controller lost for {lost:.1f} s: sitting down', flush=True)
                        lower_from(pos, a.lower, 'lower')
                        phase, g_prev = 'wait', None
                        if a.auto_stand:                    # started standing by the launcher: sat down, back to the launcher
                            break
                        last_act, v_prev = np.zeros(14, np.float32), np.zeros(14, np.float32)
                        nxt = time.monotonic()
                        tick += 1
                        continue
                else:
                    cmd = head_at(keys, t - t_pol)
                if cmd is None:
                    break
                hist_q = np.roll(hist_q, -1, 0); hist_q[-1] = q - stand
                hist_v = np.roll(hist_v, -1, 0); hist_v[-1] = v_prev          # one step late, as trained
                hist_a = np.roll(hist_a, -1, 0); hist_a[-1] = last_act
                if IMU:
                    if a.grav_bias:                        # debugging: the IMU's pitch off by this many degrees (nose down +), as a miscalibrated IMU reads
                        b = math.radians(a.grav_bias)
                        grav = np.array([grav[0] * math.cos(b) - grav[2] * math.sin(b), grav[1], grav[0] * math.sin(b) + grav[2] * math.cos(b)])
                    obs = np.concatenate([gyro, grav, q - stand, v_prev, last_act, np.array(cmd), np.zeros(6)]).astype(np.float32)
                else:
                    obs = np.concatenate([hist_q.ravel(), hist_v.ravel(), hist_a.ravel(), np.array(cmd), np.zeros(6)]).astype(np.float32)
                rising = rise_sess is not None and t - t_pol < a.rise_policy_s
                if rising:                                    # the sit/stand skill: its command 0 is stand; head held
                    obs[-13:-6] = 0.0
                act = (rise_sess if rising else sess).run(None, {inp: obs[None]})[0][0].astype(np.float32)
                ramp = min(1.0, (t - t_pol) / a.blend) if a.blend > 0 else 1.0     # the policy's stance eased in over --blend s: its first
                target = np.clip(stand + ramp * act, lim[:, 0], lim[:, 1])         # outputs bend the knees 30+ deg off the scripted stand
                if a.rise_slew and t - t_pol < a.rise_slew_s:  # a slow rise: the goals may change only so fast, at first
                    prev_t = np.array([g_prev[n] for n in names]) if g_prev else q.copy()
                    step = math.radians(a.rise_slew) / RATE
                    target = prev_t + np.clip(target - prev_t, -step, step)
                last_act = act
                g = {n: float(target[k]) for k, n in enumerate(names)}
                g['beak'] = (pad.beak_goal if pad and pad.beak_goal is not None else
                             0.3 if pad and pad.beak_open else standing['beak'])
            v_prev = qd
            if pub and tick % 2 == 0:                          # 25 Hz to the PC's twin
                pub.send({cfg['joints'][n]['id']: pos[n] for n in J}, grav, gyro, phase=phase)
            # lag against the goal sent last tick (the servo has had a tick to follow it), not this one
            lags = {n: (angle(pos, n) - g_prev[n]) * 180 / math.pi for n in J} if g_prev else {n: 0.0 for n in J}
            bus.sync_write(ids, dxl.GOAL_POSITION, goal_ticks(g))
            g_prev = g
            for n in names:
                peak[n] = max(peak[n], abs(cur[n]))
            w.writerow([round(t, 3), phase, volts, pi_power.value] + [v for k, n in enumerate(names) for v in (round(g[n], 4), round(float(q[k]), 4), round(float(qd[k]), 3), round(float(act[k]), 4), cur[n])] + [round(c, 3) for c in cmd] + [round(float(v), 3) for v in (*grav, *gyro)])
            why = None
            if 'STOP' in events and phase != 'wait':
                why = 'LB+RB on the controller'
            elif any(hw.values()):
                why = 'hardware error: ' + ', '.join(f'{n} {v:#04x}' for n, v in hw.items() if v)
            elif imu is not None and phase == 'policy' and getattr(imu, 'age', 0.0) > a.imu_stale:
                why = f'IMU silent for {imu.age * 1000:.0f} ms'
            elif imu is not None and phase == 'policy' and tilt > a.max_tilt:
                why = f'body tipped {tilt:.0f} deg (past --max-tilt)'
            elif low_reads >= a.low_volts_reads:       # a sag that lasts, not one dip (a single 0.5 s reading stopped runs, 2026-11-24)
                why = f'supply {volts:.1f} V ({low_reads} readings in a row under {a.min_volts} V)'
            elif phase == 'wait':
                pass
            else:
                worst = max(J, key=lambda n: abs(lags[n]))
                if phase != 'policy' and abs(lags[worst]) > a.max_lag:      # the scripted moves only: a policy asks for far more than it gets, by design
                    why = f'{worst} {lags[worst]:+.1f} deg behind its goal'
                elif phase == 'policy':
                    far = max(LEGS, key=lambda n: abs(g[n] - standing[n]))
                    if abs(g[far] - standing[far]) > a.leg_range:
                        why = f'{far} goal {math.degrees(g[far] - standing[far]):+.0f} deg from standing (past --leg-range)'
            if why:
                stopped = (round(t, 1), phase, why)
                print(f'STOP at {t:.1f} s ({phase}): {why}. Easing back down over {a.abort_lower:.0f} s, then torque off.', flush=True)
                lower_from(pos, a.abort_lower, 'stop')
                break
            if int(t) != last_print:
                last_print = int(t)
                log.flush()                                 # on disk every second: a power cut can't take the whole log
                os.fsync(log.fileno())
                if pi_power.under_now():
                    print('PI UNDERVOLTAGE NOW: its 5 V is under 4.63 V', flush=True)
                worst = max(J, key=lambda n: abs(lags[n]))
                legs_off = max(abs(g[n] - standing[n]) for n in LEGS)
                print(f'{t:5.1f} s {phase:6s} {volts:.1f} V  cmd {" ".join(f"{c:+.2f}" for c in cmd[:3])} head {" ".join(f"{c:+.2f}" for c in cmd[3:])}  tilt {tilt:4.1f}  legs off stand {math.degrees(legs_off):4.1f} deg  '
                      f'worst lag {abs(lags[worst]):4.1f} deg ({worst})  max {max(abs(c) for c in cur.values())} mA'
                      + ('  pi undervolted since boot' if pi_power.under_since_boot() else ''), flush=True)
            tick += 1
            nxt += 1 / RATE
            time.sleep(max(0.0, nxt - time.monotonic()))
        if stopped is None and phase != 'wait':
            print(f'policy done: easing back down over {a.lower:.0f} s', flush=True)
            _, _, pos = read_state()
            lower_from(pos, a.lower, 'lower')
            time.sleep(0.5)
    except dxl.DxlError as e:
        print(f'STOP: {e}. Easing back down over {a.abort_lower:.0f} s from the last position read, then torque off.', flush=True)
        stopped = (round(time.monotonic() - t0, 1), phase, str(e))
        try:
            if last_pos:
                lower_from(last_pos, a.abort_lower, 'stop')
        except dxl.DxlError as e2:
            print(e2)
    except KeyboardInterrupt:
        print('Ctrl-C: easing back down', flush=True)
        try:
            _, _, pos = read_state()
            lower_from(pos, a.abort_lower, 'stop')
        except dxl.DxlError as e:
            print(e)
        stopped = (round(time.monotonic() - t0, 1), phase, 'Ctrl-C')
    finally:
        for i in ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, LED, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
                bus.write(i, POSITION_D, 0)
            except dxl.DxlError:
                pass
        log.close()
        temps = {}
        for n, i in zip(J, ids):
            try:
                temps[n] = bus.read(i, dxl.PRESENT_TEMPERATURE)
            except dxl.DxlError:
                temps[n] = None
        bus.close()
        if imu is not None:
            imu.close()
        if pad:
            pad.pad.close()
    print('\ntorque off. ' + (f'Stopped at {stopped[0]} s, {stopped[1]}: {stopped[2]}' if stopped else 'Finished.'))
    print(f'{"joint":16s} {"peak mA":>8s} {"temp C":>7s}')
    for n in names:
        print(f'{n:16s} {peak[n]:8d} {temps[n]!s:>7s}')
    print('log:', a.log)


if __name__ == '__main__':
    main()
