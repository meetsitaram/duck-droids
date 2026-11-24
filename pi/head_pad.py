"""The head and beak from the Xbox controller, the duck sitting: no policy. The legs hold the pose they're in (torque on, each goal where
it is, so they don't move: --legs-limp to leave them off), and only the 4 head joints and the beak move. For checking the head's servos,
directions and range without standing the duck.

  right stick   up/down: head pitch (stick up tips the face down, forward), left/right: head turn       held: the joint keeps moving, let go: it stays
  d-pad         up/down: neck pitch (up tips the neck back), left/right: head roll
  X             a nod                      Y   beak open / shut
  A             back to where it started   B or Menu   back to where it started, torque off, quit
  LB + RB       stop at once: torque off, quit

Safety as stand_test.py: current capped (head 600 mA, beak 300), each joint's speed limited (--speed), every goal inside the joint's
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
RATE = 50.0
JOINTS = ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'beak']
NOD = [(0.5, 0.15), (0.6, -0.12), (0.5, 0.0)]               # (seconds, head pitch offset, + is nose down): one nod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--pad', default='evdev', help='evdev (the Xbox controller), or a test script (duck/gamepad.py ScriptPad)')
    ap.add_argument('--speed', type=float, default=0.8, help='rad/s at full stick')
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--max-volts', type=float, default=6.5)
    ap.add_argument('--telemetry', type=int, default=9100)
    ap.add_argument('--legs-limp', action='store_true', help='leave the legs with torque off, instead of holding them where they are')
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
        bus.write(i, GOAL_CURRENT, CAP['beak'] if n == 'beak' else CAP['head'])
        bus.write(i, dxl.POSITION_P, 1200 if n == 'neck_pitch' else 600)
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
    print(f'legs {"holding where they are" if leg_ids else "limp"}. ' f'supply {volts:.1f} V. Head on the controller: right stick pitch and turn, d-pad neck and roll, X nod, Y beak, A recentre, '
          f'B quit, LB+RB stop. Start: ' + '  '.join(f'{n} {math.degrees(q0[n]):+.0f}' for n in JOINTS), flush=True)
    q = dict(q0)
    beak_open, nod_t, prev, stopped, tick = False, None, set(), None, 0
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
            if ('B' in new or 'Menu' in new) and back_t is None:
                back_t, q_back = time.monotonic(), dict(q)
            if back_t is not None:                          # back to the start over 2 s, then quit
                u = min(1.0, (time.monotonic() - back_t) / 2.0)
                u = u * u * (3 - 2 * u)
                q = {n: q_back[n] + u * (q0[n] - q_back[n]) for n in JOINTS}
                if u >= 1.0:
                    bus.sync_write(ids, dxl.GOAL_POSITION, ticks(q))
                    time.sleep(0.3)
                    break
            else:
                if 'A' in new:
                    q = dict(q0)
                    beak_open = False
                if 'Y' in new:
                    beak_open = not beak_open
                if 'X' in new and nod_t is None:
                    nod_t = time.monotonic()
                dt = 1 / RATE
                if s.lost:
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
            if nod_t is not None and back_t is None:
                prev_v, t_n, v = 0.0, time.monotonic() - nod_t, None
                for dur, val in NOD:
                    if t_n < dur:
                        f = t_n / dur
                        v = prev_v + f * f * (3 - 2 * f) * (val - prev_v)
                        break
                    t_n -= dur
                    prev_v = val
                if v is None:
                    nod_t = None
                else:
                    goal['head_pitch'] = min(lim['head_pitch'][1], max(lim['head_pitch'][0], q['head_pitch'] + v))
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
