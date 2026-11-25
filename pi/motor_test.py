"""Which servo is weak? No policy: the duck rises slowly to the standing pose (hold it), then each servo in turn gets a quick kick forward and back
while the rest hold still, and every kick is measured. Then it eases back down, torque off, and prints a table with the weak ones flagged.

  python motor_test.py                       on the duck (stop the launcher first: systemctl --user stop duck-launcher)
  python motor_test.py --amp 6 --only legs   smaller kicks, the legs only
  python motor_test.py --port socket://127.0.0.1:9000 --max-volts 9      against the simulator (sim/server.py)

For each kick: how long before the joint starts to move (delay), how long to get half and 90 % of the way, how far past it went (overshoot),
how far off it ended (error), the servo's peak current, its own voltage at the lowest, and a snapshot of every servo's voltage mid-kick, which
shows where along the power chain the voltage sags. Safety as stand_test.py: current-based position mode, current capped (legs --cap, head 600 mA),
a low supply stops it, Ctrl-C eases it down. Writes motor_test.json and motor_test.csv beside it (2026-11-24).
"""
import argparse
import csv
import json
import math
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
from duck.telemetry import Publisher  # noqa: E402
from stand_test import CAP, GOAL_CURRENT, HEAD, LEGS, MODE_CURRENT_POSITION, POSITION_D, at  # noqa: E402

K = 2 * math.pi / 4096
RATE = 50.0
ORDER = ['left_hip_yaw', 'left_hip_roll', 'left_hip_pitch', 'left_knee', 'left_ankle',
         'right_hip_yaw', 'right_hip_roll', 'right_hip_pitch', 'right_knee', 'right_ankle',
         'neck_pitch', 'head_pitch', 'head_yaw', 'head_roll']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--model', default=os.path.join(HERE, 'models', 'stand_nod.json'), help='its standing pose is the one held')
    ap.add_argument('--amp', type=float, default=8.0, help='deg each way, legs (head joints get --amp-head)')
    ap.add_argument('--amp-head', type=float, default=10.0)
    ap.add_argument('--kick-s', type=float, default=0.6, help='seconds measured after each kick')
    ap.add_argument('--rise', type=float, default=8.0, help='seconds of the slow rise to standing (hold the duck)')
    ap.add_argument('--settle', type=float, default=3.0, help='seconds held standing before the first kick')
    ap.add_argument('--only', choices=['all', 'legs', 'head'], default='all')
    ap.add_argument('--cap', type=int, default=800, help='leg current cap, mA (as run_policy.py)')
    ap.add_argument('--leg-gain', type=int, default=800)
    ap.add_argument('--neck-gain', type=int, default=1200)
    ap.add_argument('--head-gain', type=int, default=600)
    ap.add_argument('--min-volts', type=float, default=3.8, help='stop below this (lower than run_policy.py: the sag is what this measures)')
    ap.add_argument('--max-volts', type=float, default=6.3)
    ap.add_argument('--stress', type=int, default=0, help='after the kicks, this many steps of EVERY servo at once, + then -, the worst load the supply sees')
    ap.add_argument('--stress-period', type=float, default=0.4, help='seconds each stress step is held')
    ap.add_argument('--no-kicks', action='store_true', help='skip the one-at-a-time kicks (with --stress: the stress test alone)')
    ap.add_argument('--tune', help="a joint: standing, the controller's d-pad up/down nudges it --tune-step at a time, A saves the zero there, B leaves it")
    ap.add_argument('--tune-step', type=float, default=0.5, help='deg per d-pad press')
    ap.add_argument('--no-imu', action='store_true', help="don't read the IMU (by default it goes to the twin, and its tilt over the hold is logged)")
    a = ap.parse_args()

    cfg = load_config(a.config)
    J = cfg['joints']
    lay = json.load(open(a.model))
    stand = {n: float(v) for n, v in lay['standing_pose_rad'].items()}
    stand.setdefault('beak', 0.02)
    names = [n for n in J if n in stand]                      # every servo that has a standing angle
    ids = [J[n]['id'] for n in names]
    sign = {n: J[n]['direction'] for n in names}
    order = [n for n in ORDER if n in names and (a.only == 'all' or (a.only == 'legs') == (n in LEGS))]

    bus = dxl.Bus(find_port() if a.port == 'auto' else a.port, timeout=0.05)
    volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
    if not a.min_volts <= volts <= a.max_volts:
        raise SystemExit(f'supply {volts:.1f} V: needs {a.min_volts}-{a.max_volts} V')
    raw = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
    p0 = {n: int.from_bytes(raw[J[n]['id']], 'little', signed=True) for n in names}
    q0 = {n: ((p0[n] - J[n]['centre'] + 2048) % 4096 - 2048) * K * sign[n] for n in names}

    def angle(n, pos):                                         # from the first reading, so a joint by the 0/4095 wrap can't jump a turn
        return q0[n] + (pos - p0[n]) * sign[n] * K

    def ticks(q):
        return [p0[n] + int(round((q[n] - q0[n]) * sign[n] / K)) for n in names]

    for n in names:
        i = J[n]['id']
        head = n in HEAD
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, CAP['head'] if head else CAP['beak'] if n == 'beak' else a.cap)
        bus.write(i, dxl.POSITION_P, a.neck_gain if n == 'neck_pitch' else a.head_gain if head or n == 'beak' else a.leg_gain)
        bus.write(i, POSITION_D, 300 if head or n == 'beak' else 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)
    bus.sync_write(ids, dxl.GOAL_POSITION, ticks(q0))
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)

    def state(sel):
        """{name: (mA, rad)} for the servos in sel, in one sync read"""
        sid = [J[n]['id'] for n in sel]
        r = bus.sync_read(sid, 126, 10)
        out = {}
        for n in sel:
            b = r[J[n]['id']]
            out[n] = (int.from_bytes(b[0:2], 'little', signed=True), angle(n, int.from_bytes(b[6:10], 'little', signed=True)))
        return out

    def all_volts():
        return {n: bus.read(J[n]['id'], dxl.PRESENT_VOLTAGE) / 10 for n in names}

    pub = Publisher()                                        # the twin on the PC follows: twin.py --remote <pi>
    imu, tilt = None, []
    if not a.no_imu:
        try:
            from duck.hardware import Bno085
            imu = Bno085(cfg)
        except Exception as e:                               # noqa: BLE001  the test runs without it
            print(f'IMU not answering ({e}): servos only', flush=True)
    all_ids = sorted(j['id'] for j in J.values())

    def send():
        try:
            raw = bus.sync_read(all_ids, 126, 10)                # current 2, velocity 4, position 4
            gyro, grav = imu.read() if imu else (None, None)
            if 'target' in overlay:                              # each joint's current, for the twin's list of the joints off their goal
                overlay['target']['mA'] = {n: int.from_bytes(raw[J[n]['id']][0:2], 'little', signed=True) for n in names}
            pub.send({i: int.from_bytes(raw[i][6:10], 'little', signed=True) for i in all_ids}, grav, gyro, **overlay)
            last_grav[0] = grav
            if grav is not None and logging_tilt[0]:        # pitch + is nose down, roll + is right side down
                tilt.append((time.monotonic(), math.degrees(math.atan2(grav[0], -grav[2])), math.degrees(math.atan2(-grav[1], -grav[2]))))
        except dxl.DxlError:
            pass

    logging_tilt = [False]
    overlay, last_grav = {}, [None]

    def wait(secs):                                          # sleep, streaming to the twin
        t0 = time.monotonic()
        while time.monotonic() - t0 < secs:
            send()
            time.sleep(0.03)

    def move(target, secs):
        start = {n: v[1] for n, v in state(names).items()}
        t0 = time.monotonic()
        while True:
            t = time.monotonic() - t0
            _, g = at([(secs, target)], start, t)
            if g is None:
                bus.sync_write(ids, dxl.GOAL_POSITION, ticks(target))
                return
            bus.sync_write(ids, dxl.GOAL_POSITION, ticks(g))
            send()
            time.sleep(1 / RATE)

    def tune(n):
        """Standing: the d-pad nudges joint n; A sets its zero so that where it ends reads as the standing angle; B keeps the old one."""
        from duck.gamepad import open_pad
        pad = open_pad('evdev')
        off, step = 0.0, math.radians(a.tune_step)
        print(f'TUNE {n}: d-pad up/down = {a.tune_step:+.1f} deg, A = save the zero here, B = keep the old one', flush=True)
        pad.rumble(150, 0.5)
        prev, last_print = (0, 0), 0.0
        while True:
            st = pad.state()
            dy = int(round(st.axes['dy']))
            if dy and prev[1] == 0:
                off += dy * step
                bus.sync_write(ids, dxl.GOAL_POSITION, ticks(dict(stand, **{n: stand[n] + off})))
                overlay['target']['goal'][n] = round(stand[n] + off, 4)
            prev = (0, dy)
            g = last_grav[0]
            tilt_s = '' if g is None else f'  IMU pitch {math.degrees(math.atan2(g[0], -g[2])):+.1f} roll {math.degrees(math.atan2(-g[1], -g[2])):+.1f}'
            overlay['calib'] = dict(now=n, deg=round(math.degrees(off), 1), step='tune', warn='',
                                    hint=f'd-pad up/down nudges {a.tune_step:.1f} deg. A = save zero here, B = keep.{tilt_s}', done=[], todo=[])
            if time.monotonic() - last_print > 1.0:
                last_print = time.monotonic()
                print(f'  {n} {math.degrees(off):+.1f} deg{tilt_s}', flush=True)
            for b in ('A', 'B'):
                if b in st.held:
                    while b in pad.state().held:
                        send()
                        time.sleep(0.02)
                    overlay.pop('calib', None)
                    if b == 'A' and off:
                        c_old = J[n]['centre']
                        c_new = (c_old + int(round(off * sign[n] / K))) % 4096
                        cur = json.load(open(a.config))
                        shutil.copy(a.config, a.config + time.strftime('.%Y%m%d-%H%M%S.bak'))
                        cur['joints'][n]['centre'] = c_new
                        with open(a.config, 'w') as f:
                            json.dump(cur, f, indent=1)
                            f.write('\n')
                        print(f'saved: {n} centre {c_old} -> {c_new} ({math.degrees(off):+.1f} deg)', flush=True)
                        pad.rumble(300, 1.0)
                    else:
                        print(f'kept: {n} centre {J[n]["centre"]} (nudged {math.degrees(off):+.1f} deg)', flush=True)
                        pad.rumble(80, 0.4)
                    return
            send()
            time.sleep(0.03)

    results, trace, stress = [], [], []
    try:
        print(f'supply {volts:.1f} V. Rising to the standing pose over {a.rise:.0f} s: hold the duck.', flush=True)
        move(stand, a.rise)
        overlay['target'] = dict(goal={n: round(v, 4) for n, v in stand.items()}, tilt=[0.0, 0.0])   # the twin: where it should be (the
        logging_tilt[0] = True                                     # standing pose has the feet parallel to the body: level is 0, 0)
        wait(a.settle)
        logging_tilt[0] = False
        if tilt:
            P, R = np.array([x[1] for x in tilt]), np.array([x[2] for x in tilt])
            print(f'IMU over the {a.settle:.0f} s hold ({len(P)} readings): pitch {P.mean():+.2f} (sd {P.std():.2f}, '
                  f'{P.min():+.1f}..{P.max():+.1f}), roll {R.mean():+.2f} (sd {R.std():.2f}, {R.min():+.1f}..{R.max():+.1f}) deg. '
                  'Pitch + is nose down, roll + right side down', flush=True)
            with open(os.path.join(HERE, 'stand_tilt.csv'), 'w') as f:
                f.write('t,pitch_deg,roll_deg\n' + ''.join(f'{t - tilt[0][0]:.3f},{p:.3f},{r:.3f}\n' for t, p, r in tilt))
        base_v = all_volts()
        base = state(names)
        print('standing. still: ' + ', '.join(f'{n} {base[n][0]} mA' for n in order if abs(base[n][0]) > 40) +
              f'. Voltage {min(base_v.values()):.1f}-{max(base_v.values()):.1f} V', flush=True)
        if a.tune:
            tune(a.tune)
        for n in ([] if a.no_kicks else order):
            amp = math.radians(a.amp_head if n in HEAD else a.amp)
            for d in (+1, -1):
                goal = dict(stand)
                goal[n] = stand[n] + d * amp
                q_start = state([n])[n][1]
                bus.sync_write(ids, dxl.GOAL_POSITION, ticks(goal))
                t0 = time.monotonic()
                samples, snap, vmin = [], None, 99.0
                while (t := time.monotonic() - t0) < a.kick_s:
                    mA, q = state([n])[n]
                    samples.append((t, mA, q))
                    trace.append([n, d, round(t, 4), mA, round(math.degrees(q - stand[n]), 3)])
                    if snap is None and t > 0.1:               # mid-kick: every servo's voltage, the chain's sag
                        snap = all_volts()
                        vmin = min(vmin, snap[n])
                    elif len(samples) % 5 == 0:
                        vmin = min(vmin, bus.read(J[n]['id'], dxl.PRESENT_VOLTAGE) / 10)
                tt = np.array([s[0] for s in samples]) * 1000
                mm = np.array([s[1] for s in samples])
                prog = (np.array([s[2] for s in samples]) - q_start) / (goal[n] - q_start)    # 0 at start, 1 at the goal
                def first(th):
                    i = np.argmax(prog >= th)
                    return float(tt[i]) if prog[i] >= th else None
                res = dict(joint=n, dir='+' if d > 0 else '-', amp_deg=round(math.degrees(amp), 1),
                           delay_ms=first(0.05), t50_ms=first(0.5), t90_ms=first(0.9),
                           overshoot_pct=round(max(0.0, (prog.max() - 1) * 100), 1),
                           error_deg=round(math.degrees(abs(1 - prog[-1]) * amp), 2),
                           peak_mA=int(np.abs(mm).max()), volts_min=vmin,
                           chain_volts=snap, chain_min=min(snap.values()) if snap else None)
                results.append(res)
                print(f"  {n:16s} {res['dir']}  delay {res['delay_ms'] or float('nan'):5.0f} ms  half {res['t50_ms'] or float('nan'):5.0f}  90% {res['t90_ms'] or float('nan'):5.0f}  "
                      f"over {res['overshoot_pct']:5.1f}%  error {res['error_deg']:4.1f} deg  peak {res['peak_mA']:4d} mA  own V {vmin:.1f}  chain min {res['chain_min'] or 0:.1f} V", flush=True)
                if vmin < a.min_volts:
                    raise RuntimeError(f'supply sagged to {vmin:.1f} V at {n}')
                bus.sync_write(ids, dxl.GOAL_POSITION, ticks(stand))
                wait(0.5)
        for k in range(a.stress):
            d = 1 if k % 2 == 0 else -1
            goal = {n: stand[n] + d * math.radians(0 if n == 'beak' else a.amp_head if n in HEAD else a.amp) for n in names}
            bus.sync_write(ids, dxl.GOAL_POSITION, ticks(goal))
            t0 = time.monotonic()
            while (t := time.monotonic() - t0) < a.stress_period:
                r = bus.sync_read(ids, 126, 20)                 # current .. position .. input voltage, every servo in one read
                row = {}
                for n in names:
                    b = r[J[n]['id']]
                    row[n] = (int.from_bytes(b[0:2], 'little', signed=True),
                              math.degrees(angle(n, int.from_bytes(b[6:10], 'little', signed=True)) - goal[n]),
                              int.from_bytes(b[18:20], 'little') / 10)
                tot = sum(abs(v[0]) for v in row.values())
                vlo = min(v[2] for v in row.values())
                stress.append(dict(step=k, t=round(t, 4), total_mA=tot, v_min=vlo, **{f'{n}_mA': row[n][0] for n in names},
                                   **{f'{n}_V': row[n][2] for n in names}, **{f'{n}_err': round(row[n][1], 2) for n in names}))
                if vlo < a.min_volts:
                    raise RuntimeError(f'stress step {k}: supply sagged to {vlo:.1f} V at {tot} mA total')
            rows = [x for x in stress if x['step'] == k]
            worst = max(rows, key=lambda x: x['total_mA'])
            print(f"  stress {k + 1:2d}/{a.stress} {'+' if d > 0 else '-'}  peak total {worst['total_mA']:5d} mA  lowest {min(x['v_min'] for x in rows):.1f} V  "
                  f"worst error at the end {max(abs(rows[-1][f'{n}_err']) for n in names if n in LEGS):.1f} deg", flush=True)
        if a.stress:
            bus.sync_write(ids, dxl.GOAL_POSITION, ticks(stand))
            wait(0.5)
    except (KeyboardInterrupt, RuntimeError, dxl.DxlError) as e:
        print(f'\nstopped: {e}', flush=True)
    finally:
        try:
            overlay.clear()
            print(f'easing back down over 6 s', flush=True)
            move(q0, 6.0)
            time.sleep(0.3)
        except dxl.DxlError as e:
            print(e)
        for i in ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
                bus.write(i, POSITION_D, 0)
            except dxl.DxlError:
                pass
        pub.close()
        bus.close()
        if imu:
            imu.close()

    if stress:
        with open(os.path.join(HERE, 'motor_stress.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(stress[0]))
            w.writeheader()
            w.writerows(stress)
        I = np.array([x['total_mA'] for x in stress]) / 1000
        V = np.array([np.mean([x[f'{n}_V'] for n in names]) for x in stress])
        if np.ptp(I) > 0.3:
            slope, v0 = np.polyfit(I, V, 1)
            print()
            print(f'stress: peak {I.max():.1f} A total, servos saw {V.min():.2f}-{V.max():.2f} V; '
                  f'fit V = {v0:.2f} - {-slope:.2f} * A  (about {-slope:.2f} ohm between the supply and the servos)')
        print('lowest voltage each servo saw under stress: ' + ', '.join(f"{n} {min(x[f'{n}_V'] for x in stress):.1f}" for n in names))
        print('saved motor_stress.csv')
    if not results:
        return
    json.dump(results, open(os.path.join(HERE, 'motor_test.json'), 'w'), indent=1)
    with open(os.path.join(HERE, 'motor_test.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['joint', 'dir', 't', 'mA', 'deg_from_stand'])
        w.writerows(trace)
    # weak: slow to get there, or never gets there, against the others of its kind
    print('\nsummary (each joint, both directions; * = clearly worse than the others):')
    by = {}
    for r in results:
        by.setdefault(r['joint'], []).append(r)
    t90 = {j: max((r['t90_ms'] or a.kick_s * 1000) for r in rs) for j, rs in by.items()}
    err = {j: max(r['error_deg'] for r in rs) for j, rs in by.items()}
    med_t = np.median(list(t90.values()))
    for j, rs in by.items():
        flag = []
        if t90[j] > 1.6 * med_t or any(r['t90_ms'] is None for r in rs):
            flag.append('slow' if all(r['t90_ms'] for r in rs) else 'never reached 90%')
        if err[j] > 1.5:
            flag.append(f'ends {err[j]:.1f} deg short')
        if any(r['overshoot_pct'] > 30 for r in rs):
            flag.append('overshoots')
        print(f"  {j:16s} 90% in {t90[j]:5.0f} ms   error {err[j]:4.1f} deg   peak {max(r['peak_mA'] for r in rs):4d} mA   own V min {min(r['volts_min'] for r in rs):.1f}"
              + ('   * ' + ', '.join(flag) if flag else ''))
    chain = [r['chain_volts'] for r in results if r['chain_volts']]
    if chain:
        lo = {n: min(c[n] for c in chain) for n in names}
        print('lowest voltage each servo saw during any kick: ' + ', '.join(f'{n} {v:.1f}' for n, v in sorted(lo.items(), key=lambda kv: kv[1])))
    print('saved motor_test.json and motor_test.csv')


if __name__ == '__main__':
    main()
