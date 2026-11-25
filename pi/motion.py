"""Record a motion by moving the duck by hand, torque off, and play it back on the servos.

  python motion.py record wave --countdown 5 --view   5 s to get ready, then move the duck by hand; Ctrl-C ends it: motions/wave.json
  python motion.py play wave                        the servos play it back, then ease back to where the duck started
  python motion.py play wave --speed 0.5 --view     half speed, with the live twin window
  python motion.py play wave --preview              on the model only, no servos

Recording: every servo limp, every joint read 25 times a second, as angles (rad, the config's zeros and directions), lightly
smoothed. --wait-for FILE starts it when the file appears, --stop-file FILE ends it; --view shows the twin as you move.

Playing back, the safety of stand_test.py: current-based position mode with each servo's current capped (legs 800 mA, head 600,
beak 300), the legs stiff (gain 1500) and the neck, head and beak softer and damped (600, D 300: stiffer, the head yaw hunts);
torque on with every goal where its joint is; every goal the present reading plus the change asked for (the hip yaws' zeros sit
at the 0/4095 wrap). It eases into the first recorded pose, plays, and eases back to the pose it started in before the torque
goes off. A servo error, the supply under --min-volts or a joint more than --max-lag degrees behind stops it, and it eases back
the same way: it never lets go mid-move. Nothing balances it: someone steadies the duck.
"""
import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from duck import dxl  # noqa: E402
from duck.hardware import load_config  # noqa: E402
from duck.set_id import find_port  # noqa: E402
import stand_test as st  # noqa: E402

K = 2 * math.pi / dxl.TICKS_PER_REV
MOTIONS = os.path.join(HERE, 'motions')
MAX_LOOP_DEG = 20.0      # a recording's end this close to its start, joint by joint, or playback refuses it
MAX_START_DEG = 15.0     # the duck this close to the recording's first pose, joint by joint, before the torque comes on


def motion_path(name):
    return name if name.endswith('.json') else os.path.join(MOTIONS, name + '.json')


def angles_of(raw, cfg, names):
    return {n: ((raw[n] - cfg['joints'][n]['centre'] + 2048) % 4096 - 2048) * K * cfg['joints'][n]['direction'] for n in names}


def read_positions(bus, cfg, names):
    ids = [cfg['joints'][n]['id'] for n in names]
    raw = bus.sync_read(ids, dxl.PRESENT_POSITION[0], 4)
    return {n: int.from_bytes(raw[i], 'little', signed=True) for n, i in zip(names, ids)}


def open_view(cfg, q):
    import mujoco.viewer
    import twin
    m, d, adr = twin.load_model(cfg, soles=False)
    twin.pose(m, d, adr, q)
    v = mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False)
    v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
    v.cam.lookat[:] = d.subtree_com[1]
    v.sync()

    def show(qn):
        if v.is_running():
            with v.lock():
                twin.pose(m, d, adr, qn)
                v.cam.lookat[:] = d.subtree_com[1]
            v.sync()
    return v, show


def smooth_frames(frames, k=2):
    """A centred moving average over 2k+1 frames: takes out the readings' jitter, not the motion."""
    out = []
    for i in range(len(frames)):
        win = frames[max(0, i - k):i + k + 1]
        out.append([frames[i][0]] + [sum(f[j] for f in win) / len(win) for j in range(1, len(frames[i]))])
    return out


def record(a, cfg):
    names = st.ALL
    port = find_port() if a.port == 'auto' else a.port
    bus = dxl.Bus(port, timeout=0.05)
    for n in names:
        bus.write(cfg['joints'][n]['id'], dxl.TORQUE_ENABLE, 0)        # limp: moved by hand
    q = angles_of(read_positions(bus, cfg, names), cfg, names)
    view, show = open_view(cfg, q) if a.view else (None, None)
    if a.wait_for:
        if os.path.exists(a.wait_for):
            os.remove(a.wait_for)
        print('ready: torque off. Waiting for the start signal.', flush=True)
        while not os.path.exists(a.wait_for):
            if show:
                show(angles_of(read_positions(bus, cfg, names), cfg, names))
            time.sleep(0.04)
        os.remove(a.wait_for)
    for k in range(int(a.countdown), 0, -1):
        print(f'recording in {k} s', flush=True)
        t_end = time.monotonic() + 1
        while time.monotonic() < t_end:
            if show:
                show(angles_of(read_positions(bus, cfg, names), cfg, names))
            time.sleep(0.04)
    if a.stop_file and os.path.exists(a.stop_file):
        os.remove(a.stop_file)
    print(f'RECORDING: move the duck. Ends on the stop signal, Ctrl-C, or after {a.max_seconds:.0f} s.', flush=True)
    frames, t0, last = [], time.monotonic(), -1
    try:
        while True:
            t = time.monotonic() - t0
            if t > a.max_seconds or (a.stop_file and os.path.exists(a.stop_file)):
                break
            try:
                q = angles_of(read_positions(bus, cfg, names), cfg, names)
            except dxl.DxlError as e:
                print('read failed:', e)
                continue
            frames.append([round(t, 3)] + [q[n] for n in names])
            if show:
                show(q)
            if int(t) != last:
                last = int(t)
                print(f'  {t:4.0f} s', flush=True)
            time.sleep(max(0.0, 1 / a.hz - (time.monotonic() - t0 - t)))
    except KeyboardInterrupt:
        pass
    bus.close()
    if a.stop_file and os.path.exists(a.stop_file):
        os.remove(a.stop_file)
    if len(frames) < 5:
        raise SystemExit('too short to keep')
    frames = smooth_frames(frames)
    os.makedirs(MOTIONS, exist_ok=True)
    path = motion_path(a.name)
    json.dump({'about': 'Joint angles (rad) over time, recorded by hand with torque off: python motion.py record. Each frame is [t s, '
                        'then one angle per joint in "joints"].', 'recorded': time.strftime('%Y-%m-%d %H:%M'), 'hz': a.hz,
               'joints': names, 'frames': [[round(v, 5) for v in f] for f in frames]}, open(path, 'w'), indent=None)
    span = {n: (min(f[j + 1] for f in frames), max(f[j + 1] for f in frames)) for j, n in enumerate(names)}
    moved = [f'{n} {math.degrees(hi - lo):.0f}' for n, (lo, hi) in span.items() if math.degrees(hi - lo) > 3]
    print(f'saved {path}: {frames[-1][0]:.1f} s, {len(frames)} frames. Joints that moved (deg): ' + (', '.join(moved) or 'none'))
    gap = {n: math.degrees(abs(frames[-1][j + 1] - frames[0][j + 1])) for j, n in enumerate(names)}
    far = {n: g for n, g in gap.items() if g > MAX_LOOP_DEG}
    w_ = max(gap, key=gap.get)
    print(f'start to end: largest gap {gap[w_]:.0f} deg ({w_}).' + (
        f' Over {MAX_LOOP_DEG:.0f} deg on ' + ', '.join(f'{n} {g:.0f}' for n, g in far.items()) +
        ': playback will refuse it. Record again, ending where it began.' if far else ' Close enough to play back.'))
    if view:
        view.close()


def load_motion(name):
    m = json.load(open(motion_path(name)))
    js = m['joints']
    return js, [(f[0], dict(zip(js, f[1:]))) for f in m['frames']]


def sample(track, t):
    """The recorded pose at t, between frames."""
    if t <= track[0][0]:
        return track[0][1]
    for (ta, qa), (tb, qb) in zip(track, track[1:]):
        if ta <= t <= tb:
            w = (t - ta) / max(tb - ta, 1e-9)
            return {n: qa[n] + w * (qb[n] - qa[n]) for n in qa}
    return track[-1][1]


def play(a, cfg):
    names, track = load_motion(a.name)
    if a.speed != 1.0:
        track = [(t / a.speed, q) for t, q in track]
    dur = track[-1][0]
    if a.preview:
        import mujoco.viewer
        import twin
        m, d, adr = twin.load_model(cfg, soles=False)
        print(f'preview: {dur:.1f} s, then again. Close the window to stop.')
        with mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False) as v:
            v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
            t0, lap = time.monotonic(), -1
            while v.is_running():
                t = (time.monotonic() - t0) % (dur + 1.5)
                if a.sound and int((time.monotonic() - t0) // (dur + 1.5)) != lap:
                    from duck import sound
                    lap = int((time.monotonic() - t0) // (dur + 1.5))
                    sound.play(a.sound)
                with v.lock():
                    twin.pose(m, d, adr, sample(track, t))
                    v.cam.lookat[:] = d.subtree_com[1]
                v.sync()
                time.sleep(1 / 60)
        return

    J = [n for n in names if n in cfg['joints']]
    loop = {n: math.degrees(abs(track[-1][1][n] - track[0][1][n])) for n in J}
    far = {n: g for n, g in loop.items() if g > a.max_loop}
    if far:
        raise SystemExit(f'the recording ends far from where it starts (over {a.max_loop:.0f} deg): ' + ', '.join(f'{n} {g:.0f}' for n, g in far.items()) +
                         '. Easing back from there would be a big move that was never recorded: record it again, ending where it began.')
    port = find_port() if a.port == 'auto' else a.port
    bus = dxl.Bus(port, timeout=0.05)
    ids = [cfg['joints'][n]['id'] for n in J]
    sign = {n: cfg['joints'][n]['direction'] for n in J}
    for i in ids:
        if not bus.ping(i):
            raise SystemExit(f'servo {i} does not answer')
    volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
    print(f'supply {volts:.1f} V')
    if volts > a.max_volts or volts < a.min_volts:
        raise SystemExit(f'{volts:.1f} V: needs {a.min_volts}-{a.max_volts} V')
    for n, i in zip(J, ids):
        head = (n in st.HEAD or n in st.BEAK) and n != 'neck_pitch'      # the neck carries the whole head: stiff, like the legs
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, st.MODE_CURRENT_POSITION)
        # the neck lifts the whole head: the leg cap (at the head's 600 mA it trailed 15 deg lifting the head back into a clip's
        # leaned-back posture, 2026-11-24)
        bus.write(i, st.GOAL_CURRENT, a.cap if n == 'neck_pitch' else st.CAP['head'] if n in st.HEAD else st.CAP['beak'] if n in st.BEAK else a.cap)
        bus.write(i, dxl.POSITION_P, a.neck_gain if n == 'neck_pitch' else a.head_gain if head else a.gain)
        bus.write(i, st.POSITION_D, a.neck_damping if n == 'neck_pitch' else a.head_damping if head else 0)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)

    pub, imu, logw, logf = None, None, None, None
    if a.telemetry:                               # the twin on the PC (twin.py --remote <pi>): the duck, the IMU, and the goal as a see-through duck
        from duck.telemetry import Publisher
        pub = Publisher()
        try:
            from duck.hardware import Bno085
            imu = Bno085(cfg)
        except Exception as e:                    # noqa: BLE001  plays without it
            print(f'IMU not answering ({e}): no IMU in the stream or the log', flush=True)
    if a.log:
        import csv
        logf = open(a.log, 'w', newline='')
        logw = csv.writer(logf)
        logw.writerow(['t', 'phase', 'volts'] + [f'{n}_{k}' for n in J for k in ('goal', 'q', 'mA')] + ['grav_x', 'grav_y', 'grav_z', 'gyro_x', 'gyro_y', 'gyro_z'])
    last = [None, None]

    def state():
        raw = bus.sync_read(ids, 126, 10)
        cur = {n: int.from_bytes(raw[i][0:2], 'little', signed=True) for n, i in zip(J, ids)}
        pos = {n: int.from_bytes(raw[i][6:10], 'little', signed=True) for n, i in zip(J, ids)}
        last[:] = [cur, pos]
        return cur, pos

    def record(t, phase, q):
        """stream to the twin and log one row: the goal q, the measured angles, the currents, the IMU"""
        if last[0] is None:
            return
        cur, pos = last
        meas = {n: q0[n] + (pos[n] - p0[n]) * sign[n] * K for n in J}
        gyro, grav = imu.read() if imu else (None, None)
        if pub:
            pub.send({cfg['joints'][n]['id']: pos[n] for n in J}, grav, gyro,
                     target=dict(goal={n: round(q[n], 4) for n in J}, tilt=[0.0, 0.0], mA=cur), phase=phase)
        if logw:
            logw.writerow([round(t, 3), phase, volts] + [v for n in J for v in (round(q[n], 4), round(meas[n], 4), cur[n])] +
                          [round(float(x), 4) for x in (*(grav if grav is not None else (0, 0, 0)), *(gyro if gyro is not None else (0, 0, 0)))])

    _, p0 = state()
    q0 = angles_of(p0, cfg, J)
    view, show = open_view(cfg, q0) if a.view else (None, None)

    if a.wait_for:
        if os.path.exists(a.wait_for):
            os.remove(a.wait_for)
        print('ready: torque off. Waiting for the start signal.', flush=True)
        while not os.path.exists(a.wait_for):
            _, pw = state()
            if show:
                show(angles_of(pw, cfg, J))
            time.sleep(0.04)
        os.remove(a.wait_for)
        _, p0 = state()
        q0 = angles_of(p0, cfg, J)
        if show:
            for k in range(5, 0, -1):
                print(f'starting in {k} s', flush=True)
                time.sleep(1)

    lim = cfg.get('limits', {})

    def clip(n, v):
        # every goal inside the config's limits, as run_policy.py does: a retargeted clip leans the neck back to +42 deg, past the real
        # duck's stop at +32 (2026-11-24, by hand) and the config's +8.6 (wires); it pressed into the stop at the full cap for 30 s
        return min(max(v, lim[n][0]), lim[n][1]) if n in lim else v

    def goal(q, limit=True):
        # limit=False for the eases in and back, which run between the clipped first pose and wherever the duck is (a limp joint can
        # hang outside its limits: clipping there made the first goal jump 27 deg, 2026-11-24)
        return [p0[n] + int(round(((clip(n, q[n]) if limit else q[n]) - q0[n]) * sign[n] / K)) for n in J]

    first = {n: clip(n, v) for n, v in track[0][1].items()}
    off = {n: math.degrees(abs(first[n] - q0[n])) for n in J}
    far = {n: g for n, g in off.items() if g > a.max_start}
    if far:
        for i in ids:
            bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
        bus.close()
        if view:
            view.close()
        raise SystemExit(f'the duck is not in the start pose of the recording (over {a.max_start:.0f} deg off): ' +
                         ', '.join(f'{n} {g:.0f}' for n, g in sorted(far.items(), key=lambda kv: -kv[1])) + '. Move those joints closer, then try again. Nothing moved.')
    w_ = max(off, key=off.get)
    print(f'start pose: within {off[w_]:.0f} deg on every joint (largest {w_})', flush=True)

    ease_in = max(2.0, max(abs(first[n] - q0[n]) for n in J) / math.radians(25))      # about 25 deg a second at most
    plan = [(ease_in, {n: first[n] for n in J})]
    bus.sync_write(ids, dxl.GOAL_POSITION, [p0[n] for n in J])
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)
    print(f'easing into the first pose ({ease_in:.1f} s), playing {dur:.1f} s, easing back', flush=True)

    t0, stopped, peak, worst = time.monotonic(), None, {n: 0 for n in J}, 0.0
    total = ease_in + dur
    hw, last_slow, started_sound = {}, 0.0, False
    try:
        while True:
            t = time.monotonic() - t0
            if t >= total:
                break
            if t < ease_in:
                _, q = st.at(plan, q0, t)
            else:
                if a.sound and not started_sound:      # the sound starts with the motion, not with the ease in
                    from duck import sound
                    sound.play(a.sound)
                    started_sound = True
                q = sample(track, t - ease_in)
            g = goal(q, limit=t >= ease_in)
            bus.sync_write(ids, dxl.GOAL_POSITION, g)
            cur, pos = state()
            record(t, 'ease in' if t < ease_in else 'play', q)
            if show:
                show({n: q0[n] + (pos[n] - p0[n]) * sign[n] * K for n in J})
            if t - last_slow > 0.5:
                last_slow = t
                volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
                raw = bus.sync_read(ids, st.HW_ERROR[0], 1)
                hw = {n: raw[i][0] for n, i in zip(J, ids)}
            lags = {n: (pos[n] - gi) * 360 / 4096 for n, gi in zip(J, g)}
            for n in J:
                peak[n] = max(peak[n], abs(cur[n]))
            w_ = max(J, key=lambda n: abs(lags[n]))
            worst = max(worst, abs(lags[w_]))
            why = None
            if any(hw.values()):
                why = 'hardware error: ' + ', '.join(f'{n} {v:#04x}' for n, v in hw.items() if v)
            elif volts < a.min_volts:
                why = f'supply {volts:.1f} V'
            elif abs(lags[w_]) > a.max_lag:
                why = f'{w_} {lags[w_]:+.1f} deg behind'
            if why:
                stopped = (round(t, 1), why)
                print(f'STOP at {t:.1f} s: {why}', flush=True)
                break
            time.sleep(max(0.0, 1 / a.hz - (time.monotonic() - t0 - t)))
        # back to where it started, then let go: never mid-move
        _, pos = state()
        here = {n: q0[n] + (pos[n] - p0[n]) * sign[n] * K for n in J}
        back = [(a.ease_back, dict(q0))]
        print(f'easing back to where it started ({a.ease_back:.0f} s), then torque off', flush=True)
        t1 = time.monotonic()
        while True:
            tb = time.monotonic() - t1
            _, qb = st.at(back, here, tb)
            if qb is None:
                break
            try:
                bus.sync_write(ids, dxl.GOAL_POSITION, goal(qb, limit=False))
                if pub or logw:
                    state()
                    record(time.monotonic() - t0, 'ease back', qb)
                if show:
                    _, pos = state()
                    show({n: q0[n] + (pos[n] - p0[n]) * sign[n] * K for n in J})
            except dxl.DxlError as e:
                print('on the way back:', e)
            time.sleep(1 / a.hz)
        time.sleep(0.5)
    finally:
        for i in ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
                bus.write(i, st.POSITION_D, 0)
            except dxl.DxlError:
                pass
        bus.close()
        if view:
            time.sleep(1)
            view.close()
        if pub:
            pub.close()
        if imu:
            imu.close()
        if logf:
            logf.close()
    print('torque off. ' + (f'Stopped at {stopped[0]} s: {stopped[1]}' if stopped else 'Finished.') + f' Worst lag {worst:.1f} deg.')
    print('peak mA: ' + ', '.join(f'{n} {v}' for n, v in sorted(peak.items(), key=lambda kv: -kv[1])[:6]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['record', 'play'])
    ap.add_argument('name', help='a motion name (motions/<name>.json) or a path')
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--hz', type=float, default=25.0)
    ap.add_argument('--view', action='store_true', help='the live twin window')
    ap.add_argument('--wait-for', help='start when this file appears (a countdown of 5 s first when playing with --view)')
    ap.add_argument('--countdown', type=float, default=0, help='record: seconds to count down before recording starts')
    ap.add_argument('--stop-file', help='record: end when this file appears')
    ap.add_argument('--max-seconds', type=float, default=60.0, help='record: the longest recording')
    ap.add_argument('--speed', type=float, default=1.0, help='play: 0.5 is half speed')
    ap.add_argument('--preview', action='store_true', help='play: on the model only, no servos')
    ap.add_argument('--sound', help='play: a sound (pi/sounds/microduck name or a wav) started as the motion starts, after the ease in (emote.py uses it)')
    ap.add_argument('--telemetry', action='store_true', help='play: stream to the twin on the PC (twin.py --remote <pi>): the duck, the IMU, the goal pose')
    ap.add_argument('--log', help='play: a CSV of every tick: the goal, measured angle and current per joint, and the IMU')
    ap.add_argument('--ease-back', type=float, default=6.0, help='play: seconds to ease back to where it started, before the torque goes off')
    ap.add_argument('--cap', type=int, default=800, help='play: current cap per leg servo, mA')
    ap.add_argument('--gain', type=int, default=1500, help='play: leg position gain')
    ap.add_argument('--neck-gain', type=int, default=1200, help='play: the neck lifts the whole head; at 600 with damping it trailed 18 deg on a fast lift')
    ap.add_argument('--neck-damping', type=int, default=100)
    ap.add_argument('--head-gain', type=int, default=600)
    ap.add_argument('--head-damping', type=int, default=300)
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--max-volts', type=float, default=6.0)
    ap.add_argument('--max-lag', type=float, default=15.0)
    ap.add_argument('--max-start', type=float, default=MAX_START_DEG, help='play: degrees any joint may be from the first pose of the recording before it refuses')
    ap.add_argument('--max-loop', type=float, default=MAX_LOOP_DEG, help='play: degrees the end of a recording may be from its start')
    a = ap.parse_args()
    cfg = load_config(a.config)
    record(a, cfg) if a.mode == 'record' else play(a, cfg)


if __name__ == '__main__':
    main()
