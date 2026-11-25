"""The head and beak from the Xbox controller, the duck sitting: no policy. The legs hold the pose they're in (torque on, each goal where
it is, so they don't move: --legs-limp to leave them off), and only the 4 head joints and the beak move. For checking the head's servos,
directions and range without standing the duck.

  right stick   up/down: head pitch (stick up tips the face down, forward), left/right: head turn       held: the joint keeps moving, let go: it stays
  d-pad         up/down: neck pitch (up tips the neck back), left/right: head roll
  on start      the IMU read once: the neck's rest shifted by how much more upright (or reclined) the body sits than at the capture,
                so the face looks the same way however the duck is seated (--imu none: off)
  on start      sitting, the head rises (with the mmh sound; RB + B lowers it with the sad sound) to its rest pose (poses/sit_emote.json: the neck raised as the user set it), at most 0.6 rad/s
  RB / LB       play the next / previous of microduck's 13 emotions at once (a short buzz; the name is printed; it cuts off one playing)
  X             play the same one again    Y   beak open / shut
                Sitting, the head and
                beak follow Pollen's keyframes around the sit pose (poses/sit_emote.json, captured from the duck; emote.py's sitting mapping:
                the neck and head pitch never forward of it, at most 0.5 / 0.6 rad back), the sound starts on the speaker, and the head eases
                in from where it is and back to it afterwards. The stick and d-pad wait till it ends. Preview: python emote.py --all --sit --preview
  A             back to the head's rest pose (sitting), eased   RB + B held 1 s   back to where it started, torque off, quit (buzzes)
  LB + RB       stop at once: torque off, quit

Safety as stand_test.py: current capped (neck 1000 mA, the rest of the head 600, beak 300), each joint's speed limited (--speed), every goal inside the joint's
limits (widened to where it starts, if it starts past them: the limp neck sits past its +9 deg), a hardware error or a low supply stops it.
Streams to the PC's twin (python twin.py --remote <pi>).

  python head_pad.py
  python head_pad.py --speed 0.5           slower
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from duck.gamepad import deadzone, open_pad  # noqa: E402
from stand_test import CAP, GOAL_CURRENT, HW_ERROR, LED, MODE_CURRENT_POSITION, POSITION_D  # noqa: E402

K = 2 * math.pi / dxl.TICKS_PER_REV
POSITION_I = (82, 2)                                        # XL330 / XC330 control table: position I gain
RATE = 50.0
JOINTS = ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'beak']
SIT_NEAR = math.radians(25)                                 # emotions play only with the neck this near the sit pose; the head pitch
# flops to a different angle each sit (-36 and -93 deg against the captured -77, 2026-11-25), so it eases in from wherever it is
TILT_SHIFT_MAX = math.radians(40)                           # the body-tilt correction of the neck, at most
RAISE_SPEED = 0.6                                           # rad/s at most, raising the head from the crouch to its rest when it starts
EASE_SPEED = 1.0                                            # rad/s at most in the ease-in and back: a far head takes longer
START_SOUND, END_SOUND = 'mmh', 'sad'                       # as the head rises at the start, and as it lowers at RB + B
EASE0 = 0.8                                                  # s into an emotion's first pose from where the head is, and back after


def body_tilt_shift(cfg, sit, imu_kind):
    """The neck offset (rad) that points the head as it was when the sit pose was captured, with the body tilted as the IMU reads it now:
    the captured body pitch minus today's (2026-11-25: the duck sat 35 deg more upright than at the capture, and the same head angles
    left the face looking down; in the sim this offset brought the head back within 0.4 deg). 0 without an IMU or a captured tilt."""
    g0 = sit.get('grav_imu') or sit.get('grav')
    if not g0 or imu_kind == 'none':
        print('the neck not corrected for the body tilt (no IMU, or no tilt in the sit pose)', flush=True)
        return 0.0
    try:
        from duck.hardware import Bno085, SimImu
        imu = Bno085(cfg) if imu_kind == 'bno085' else SimImu(imu_kind)
        t0, gs = time.monotonic(), []
        while time.monotonic() - t0 < 3.0 and len(gs) < 10:
            if getattr(imu, 'age', 0.0) < 0.2:
                gs.append(imu.read()[1])
            time.sleep(0.05)
        if hasattr(imu, 'close'):
            imu.close()
    except Exception as e:                                  # no IMU: carry on without the correction
        print(f'IMU not read ({e}): the neck not corrected for the body tilt', flush=True)
        return 0.0
    if not gs:
        print('IMU silent: the neck not corrected for the body tilt', flush=True)
        return 0.0
    g = [sum(v[i] for v in gs) / len(gs) for i in range(3)]
    pitch = lambda v: math.atan2(-v[0], -v[2])
    shift = max(-TILT_SHIFT_MAX, min(TILT_SHIFT_MAX, pitch(g0) - pitch(g)))
    print(f'body pitch {math.degrees(pitch(g)):+.0f} deg (at the capture {math.degrees(pitch(g0)):+.0f}): the neck rest shifted '
          f'{math.degrees(shift):+.0f} deg', flush=True)
    return shift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--hold-s', type=float, default=1.0, help='seconds RB + B must be held to quit')
    ap.add_argument('--pad', default='evdev', help='evdev (the Xbox controller), or a test script (duck/gamepad.py ScriptPad)')
    ap.add_argument('--speed', type=float, default=0.8, help='rad/s at full stick')
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--max-volts', type=float, default=6.5)
    ap.add_argument('--telemetry', type=int, default=9100)
    ap.add_argument('--legs-limp', action='store_true', help='leave the legs with torque off, instead of holding them where they are')
    ap.add_argument('--imu', default='bno085', help="bno085, a simulator address (127.0.0.1:9001), or none: the body's tilt, for the neck's correction")
    ap.add_argument('--sit', default=None, help='the sit pose the emotions move around (default poses/sit_emote.json, captured from the duck)')
    ap.add_argument('--audio-lead', type=float, default=0.3, help="s the sound starts before the motion: the Bluetooth speaker's lag (SBC ~0.15-0.2 s) and the player's start (~0.2 s on the Pi Zero)")
    ap.add_argument('--emote-scale', type=float, default=1.0, help='every emotion move scaled by this')
    ap.add_argument('--neck-cap', type=int, default=1000, help="mA for the neck, which holds the whole head out on its arm: at 600 it sagged 36 deg sitting (2026-11-25)")
    ap.add_argument('--hold-i', type=int, default=300, help='position I gain for the neck and head pitch, so a steady sag closes (0 off)')
    ap.add_argument('--leg-cap', type=int, default=800, help='mA, the legs holding')
    ap.add_argument('--leg-gain', type=int, default=800)
    a = ap.parse_args()

    cfg = load_config(a.config)
    ids = [cfg['joints'][n]['id'] for n in JOINTS]
    sign = {n: cfg['joints'][n]['direction'] for n in JOINTS}
    all_ids = sorted(j['id'] for j in cfg['joints'].values())
    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
    if not a.min_volts <= volts <= a.max_volts:
        raise SystemExit(f'supply {volts:.1f} V: needs {a.min_volts}-{a.max_volts} V')
    cleared = bus.clear_overloads(all_ids)                  # an overload alarm latched in a run before (2026-11-25)
    if cleared:
        print(f'cleared a latched overload alarm (rebooted) on servo IDs {cleared}', flush=True)
    for i in all_ids:                                       # everything off first, whatever a run before left on
        bus.write(i, dxl.TORQUE_ENABLE, 0)
    legs = [] if a.legs_limp else [n for n in cfg['joints'] if n not in JOINTS]
    leg_ids = [cfg['joints'][n]['id'] for n in legs]
    for i in leg_ids:
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, a.leg_cap)
        bus.write(i, dxl.POSITION_P, a.leg_gain)
        bus.write(i, POSITION_D, 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
    for n, i in zip(JOINTS, ids):
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, CAP['beak'] if n == 'beak' else a.neck_cap if n == 'neck_pitch' else CAP['head'])
        bus.write(i, dxl.POSITION_P, 1200 if n == 'neck_pitch' else 600)
        bus.write(i, POSITION_I, a.hold_i if n in ('neck_pitch', 'head_pitch') else 0)   # the steady sag under the head's weight closed
        bus.write(i, POSITION_D, 100 if n == 'neck_pitch' else 300)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
    raw = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
    p0 = {n: int.from_bytes(raw[i], 'little', signed=True) for n, i in zip(JOINTS, ids)}
    q0 = {n: ((p0[n] - cfg['joints'][n]['centre'] + 2048) % 4096 - 2048) * K * sign[n] for n in JOINTS}
    design = dict(cfg['limits'], beak=cfg['limits'].get('beak', (0.0, 0.38)))     # the beak's 0-22 deg from the model, as the twin shows it
    lim = {n: (min(design[n][0], q0[n]), max(design[n][1], q0[n])) for n in JOINTS}
    ticks = lambda q: [p0[n] + int(round((q[n] - q0[n]) * sign[n] / K)) for n in JOINTS]

    pub = None
    if a.telemetry:
        from duck.telemetry import Publisher
        pub = Publisher(a.telemetry)
    pad = open_pad(a.pad)
    print('waiting for the controller...', flush=True)
    t1 = time.monotonic()
    while pad.state().lost:
        if time.monotonic() - t1 > 10:
            raise SystemExit('no controller: press its Xbox button, then run again')
        time.sleep(0.1)

    bus.sync_write(ids, dxl.GOAL_POSITION, [p0[n] for n in JOINTS])
    if leg_ids:                                             # the legs: goal = where each is now, then torque on, so nothing moves
        r = bus.sync_read(leg_ids, dxl.PRESENT_POSITION[0], 4)
        bus.sync_write(leg_ids, dxl.GOAL_POSITION, [int.from_bytes(r[i], 'little', signed=True) for i in leg_ids])
    for i in ids + leg_ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)
        bus.write(i, LED, 1)
    print(f'legs {"holding where they are" if leg_ids else "limp"}. ' f'supply {volts:.1f} V. Head on the controller: right stick pitch and turn, d-pad neck and roll, LB/RB pick an emotion, X plays it, Y beak, A recentre, '
          f'RB + B held 1 s quits, LB+RB stops. Start: ' + '  '.join(f'{n} {math.degrees(q0[n]):+.0f}' for n in JOINTS), flush=True)
    q = dict(q0)
    from duck.gamepad import Holds
    holds = Holds({'HEADMODE': {'RB', 'B'}}, a.hold_s)     # RB + B held 1 s: back to the start, torque off, quit (the launcher's toggle)
    import emote
    from duck import sound
    sit = emote.load_sit(a.sit)                             # the head moves around the captured sit pose, never forward of it
    shift = body_tilt_shift(cfg, sit, a.imu)                # the duck sits differently each time: the neck takes the body's tilt difference
    if shift:
        sit = dict(sit, neck_pitch=sit['neck_pitch'] + shift)
    emotions = [(n, emote.track(n, cfg, a.emote_scale, sit=sit)[0]) for n in emote.names()]
    for j, (lo, hi) in emote.sit_limits(sit).items():       # the sit pose's neck is past the standing design limits: let the emotions reach it
        lim[j] = (min(lim[j][0], lo), max(lim[j][1], hi))
    sel, emo = 0, None                                      # emo: (name, track, start time, the pose it started from)
    print('emotions: LB / RB to pick, X to play: ' + ', '.join(n for n, _ in emotions), flush=True)
    rest = dict(q0, **{j: sit[j] for j in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}, beak=max(0.02, lim['beak'][0]))
    crouch_neck = sit.get('crouch', {}).get('neck_pitch', sit['neck_pitch'])
    sit_ok = min(abs(q0['neck_pitch'] - crouch_neck), abs(q0['neck_pitch'] - sit['neck_pitch'])) <= SIT_NEAR
    rise = None
    if sit_ok:                                              # raise the head to its rest pose (the user's, 2026-11-25), then the emotions
        dur = max(0.5, max(abs(rest[j] - q0[j]) for j in JOINTS) / RAISE_SPEED)
        rise = (time.monotonic(), dur, dict(q0))
        print(f'raising the head to its rest pose over {dur:.1f} s', flush=True)
        sound.play(START_SOUND)                             # waking up (the user, 2026-11-25)
    else:
        print(f'the neck ({math.degrees(q0["neck_pitch"]):+.0f} deg) is far from the sit pose: not raising the head, and no emotions '
              f'(sit the duck, or recapture poses/sit_emote.json)', flush=True)
    beak_open, prev, stopped, tick = False, set(), None, 0
    last_goal = dict(q0)
    back_t = None
    nxt = time.monotonic()
    try:
        while True:
            s = pad.state()
            new = s.held - prev
            prev = s.held
            if {'LB', 'RB'} <= s.held:
                stopped = 'LB+RB'
                break
            if holds.check(s) == 'HEADMODE' and back_t is None:
                pad.rumble(300)
                sound.play(END_SOUND)                       # going back down (the user, 2026-11-25)
                back_t, q_back = time.monotonic(), dict(q)
            if back_t is not None:                          # back to the start over 2 s, then quit
                u = min(1.0, (time.monotonic() - back_t) / 2.0)
                u = u * u * (3 - 2 * u)
                q = {n: q_back[n] + u * (q0[n] - q_back[n]) for n in JOINTS}
                if u >= 1.0:
                    bus.sync_write(ids, dxl.GOAL_POSITION, ticks(q))
                    time.sleep(0.3)
                    break
            elif rise is not None:                          # raising the head first: the controller waits
                u = min(1.0, (time.monotonic() - rise[0]) / rise[1])
                u = u * u * (3 - 2 * u)
                q = {n: rise[2][n] + u * (rest[n] - rise[2][n]) for n in JOINTS}
                if u >= 1.0:
                    rise = None
                    print('head at rest: LB / RB pick an emotion, X plays it', flush=True)
            else:
                if 'A' in new and emo is None:              # back to the rest pose (sitting) or the start, eased
                    beak_open = False
                    to = rest if sit_ok else q0
                    rise = (time.monotonic(), max(0.5, max(abs(to[j] - q[j]) for j in JOINTS) / RAISE_SPEED), dict(q))
                    rest = to
                if 'Y' in new:
                    beak_open = not beak_open
                play = 'X' in new                           # X: the picked one again
                if new & {'LB', 'RB'} and not {'LB', 'RB'} <= s.held:   # RB / LB: the next / previous one, at once (cutting one off)
                    sel = (sel + (1 if 'RB' in new else -1)) % len(emotions)
                    print(f'emotion: {emotions[sel][0]}', flush=True)
                    pad.rumble(60, 0.3)
                    play = True
                if play:
                    off = abs(q['neck_pitch'] - sit['neck_pitch'])
                    if not sit_ok or off > SIT_NEAR:                      # the neck far from the sit pose: the ease-in would swing the head a long way
                        print(f'not playing: the neck is {math.degrees(off):.0f} deg from the sit pose (poses/sit_emote.json); '
                              f'sit the duck as captured, or recapture the pose', flush=True)
                        pad.rumble(150, 1.0)
                    else:
                        emo = (emotions[sel][0], emotions[sel][1], time.monotonic(), dict(last_goal))   # eased from where the head is
                        print(f'playing {emo[0]} ({emo[1][-1][0]:.1f} s)', flush=True)
                dt = 1 / RATE
                if s.lost or emo is not None:
                    rates = {}
                else:
                    ax = s.axes
                    rates = {'head_pitch': deadzone(ax['ry']), 'head_yaw': deadzone(ax['rx']),
                             'neck_pitch': ax['dy'], 'head_roll': ax['dx']}
                for n, r in rates.items():
                    q[n] = min(lim[n][1], max(lim[n][0], q[n] + r * a.speed * dt))
                tgt_beak = 0.3 if beak_open else max(0.02, lim['beak'][0])
                q['beak'] += max(-a.speed * dt, min(a.speed * dt, tgt_beak - q['beak']))
            goal = dict(q)
            if emo is not None and back_t is None:          # ease in, the keyframes (the sound starts with them), ease back
                name, tr, t_e, q_from = emo[:4]
                t_n, dur = time.monotonic() - t_e, tr[-1][0]
                EASE = max(EASE0, max(abs(q_from[j] - tr[0][1][j]) for j in JOINTS) / EASE_SPEED)
                if t_n >= EASE - a.audio_lead and not emo[4:]:     # the sound ahead of the motion, for the speaker's lag
                    sound.play(name)
                    emo = emo + (True,)
                if t_n < EASE:
                    u = t_n / EASE
                    u, k = u * u * (3 - 2 * u), tr[0][1]
                    goal = {n: q_from[n] + u * (k[n] - q_from[n]) for n in JOINTS}
                elif t_n < EASE + dur:
                    goal = dict(emote.sample(tr, t_n - EASE))
                elif t_n < 2 * EASE + dur:
                    u = (t_n - EASE - dur) / EASE
                    u, k = u * u * (3 - 2 * u), tr[-1][1]
                    goal = {n: k[n] + u * (q_from[n] - k[n]) for n in JOINTS}
                else:
                    emo = None
                goal = {n: min(lim[n][1], max(lim[n][0], goal[n])) for n in JOINTS}
            last_goal = dict(goal)
            bus.sync_write(ids, dxl.GOAL_POSITION, ticks(goal))
            if tick % 25 == 0:
                volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
                hw = bus.sync_read(ids + leg_ids, HW_ERROR[0], 1)
                bad = {n: hw[i][0] for n, i in zip(JOINTS + legs, ids + leg_ids) if hw[i][0]}
                if bad or volts < a.min_volts:
                    stopped = f'hardware error {bad}' if bad else f'supply {volts:.1f} V'
                    break
                print('  ' + '  '.join(f'{n} {math.degrees(goal[n]):+5.0f}' for n in JOINTS) + f'   {volts:.1f} V' + ('   controller lost' if s.lost else ''), flush=True)
            if pub and tick % 2 == 0:
                r = bus.sync_read(all_ids, dxl.PRESENT_POSITION[0], 4)
                pub.send({i: int.from_bytes(r[i], 'little', signed=True) for i in all_ids})
            tick += 1
            nxt += 1 / RATE
            time.sleep(max(0.0, nxt - time.monotonic()))
    except KeyboardInterrupt:
        stopped = 'Ctrl-C'
    finally:
        for i in ids + leg_ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, LED, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
                bus.write(i, POSITION_D, 0)
            except dxl.DxlError:
                pass
        bus.close()
        pad.close()
        if pub:
            pub.close()
    print('torque off. ' + (f'Stopped: {stopped}' if stopped else 'Done.'))


if __name__ == '__main__':
    main()
