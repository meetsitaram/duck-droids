"""Powered tests on the real duck: the legs ease it from where it is (sitting) to the standing pose, and back down. Someone
supports the duck throughout. With --show, at standing it also nods, tilts its head up and down, and opens and closes its beak.

  python stand_test.py                          rise 10 s, hold 20 s, lower 10 s, torque off: legs only, head limp
  python stand_test.py --rise 6 --lower 6 --show the head's show at standing instead of the hold
  python stand_test.py --preview --show          the same, on the model in a MuJoCo window: no physics, no servos
  python stand_test.py --port socket://127.0.0.1:9000 --max-volts 9   against the simulator (sim/server.py)

Safety:
- current-based position mode (5), each servo's current capped: --cap for the legs (800 mA), 600 for the head, 300 for the beak
  (stall is about 1470 at 5 V): a jammed joint or a part in the way gets no more than that.
- torque comes on with every goal where its joint already is, and every goal is the present reading plus the change asked for,
  so a joint whose zero sits at the 0/4095 wrap (the hip yaws) can't spin a turn.
- if a servo reports a hardware error, the supply falls under --min-volts, or a joint lags its goal by more than --max-lag degrees,
  it stops and eases back down to the pose it started in (sitting) over --abort-lower seconds, and only then turns the torque off.
  It never lets go mid-move.
- the beak closes to just short of shut, never pressing into itself; every move is inside the design's limits.
The standing pose is sim/model/home.json, the trained stance. Every tick is logged to --log as CSV.
"""
import argparse
import csv
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

K = 2 * math.pi / dxl.TICKS_PER_REV
LEGS = ['right_ankle', 'right_knee', 'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
        'left_ankle', 'left_knee', 'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw']
HEAD = ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll']
BEAK = ['beak']
ALL = LEGS + HEAD + BEAK
CAP = {'head': 600, 'beak': 300}          # mA; the legs take --cap
MODE_CURRENT_POSITION = 5
GOAL_CURRENT = (102, 2)
HW_ERROR = (70, 1)
LED = (65, 1)


def smooth(a):
    return a * a * (3 - 2 * a)


_FACE = {}
RISE_FRAMES = [1]         # how many frames the rise takes: 2 with --rise-lean


def face_forward_pitch(level):
    """The head pitch that points the face straight ahead, with the legs and neck as in `level` and the feet flat on the floor:
    from the model's geometry (not its balance, which doesn't match the real duck's weights yet)."""
    import mujoco
    import twin
    from duck.hardware import load_config
    if 'm' not in _FACE:
        cfg = load_config(os.path.join(HERE, 'config', 'dynamixel.json'))
        _FACE['m'], _FACE['d'], _FACE['adr'] = twin.load_model(cfg, soles=False)
        _FACE['head'] = mujoco.mj_name2id(_FACE['m'], mujoco.mjtObj.mjOBJ_BODY, 'jaw_soft')
    m, d, adr, head = _FACE['m'], _FACE['d'], _FACE['adr'], _FACE['head']

    def nose(hp):
        q = {n: level.get(n, 0.0) for n in adr}
        q['head_pitch'] = hp
        twin.pose(m, d, adr, q)
        f = d.xmat[head].reshape(3, 3)[:, 0]
        return math.degrees(math.asin(max(-1.0, min(1.0, f[2]))))
    lo, hi = -1.6, 1.6                          # nose() falls as head_pitch rises (positive tips the nose down)
    for _ in range(40):
        mid = (lo + hi) / 2
        if nose(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def timeline(a, q0, stand):
    """Keyframes [(seconds, pose)] from the start pose: rise, the head's show at standing (with --show), lower. Each step eases from the last."""
    level = dict(stand)
    for n in HEAD:
        level[n] = 0.0
    # the head tipped back, nose up about 11 deg, with the neck leaning forward to keep the mass over the middle of the feet
    # (searched on the model, feet flat: 0.2 mm from the feet's centre, as with the head level)
    level['neck_pitch'], level['head_pitch'] = a.neck_pitch, a.head_pitch
    if a.keep_head:                            # the neck and head as they were set by hand before the start
        for n in HEAD:
            level[n] = q0[n]
    level['neck_pitch'] += math.radians(a.neck_offset)    # nudges on top: negative leans the neck forward
    level['head_pitch'] += math.radians(a.head_offset)    # positive tips the nose down
    if a.face_forward:
        level['head_pitch'] = face_forward_pitch(level) + math.radians(a.head_offset)
    if a.stand_pose:                           # a pose found by hand where the duck balances: legs, neck and head, exactly
        found = json.load(open(a.stand_pose))
        for n in LEGS + HEAD:
            if n in found:
                level[n] = found[n]
    level['beak'] = 0.02                       # just short of shut: never pressing into itself
    hp = level['head_pitch']
    frames = [(a.rise, level), (1.0, level)]
    if a.rise_lean:
        # the first part of the rise with the neck leaning further forward: unfolding from the crouch swings the body back over the
        # heels, and the weight forward holds it (the duck tipped back early in the rise, 2026-11-21, the user)
        mid = {n: q0[n] + 0.4 * (level[n] - q0[n]) for n in level}
        mid['neck_pitch'] = level['neck_pitch'] + math.radians(a.rise_lean)
        for n in ('head_pitch', 'head_yaw', 'head_roll', 'beak'):
            mid[n] = level[n]
        frames = [(0.45 * a.rise, mid), (0.55 * a.rise, level), (1.0, level)]
    RISE_FRAMES[0] = 2 if a.rise_lean else 1
    if a.show:
        def with_(**kw):
            f = dict(level)
            f.update(kw)
            return f
        # the head's moves kept small and slow front to back, as fast or big ones there tip the duck (2026-11-21, the user);
        # side to side it can swing more, as that barely moves the weight forward or back
        hy = level['head_yaw']
        for _ in range(2):                     # side to side
            frames += [(0.8, with_(head_yaw=hy + 0.26)), (0.8, with_(head_yaw=hy - 0.26))]
        frames += [(0.8, level), (0.5, level)]
        for _ in range(2):                     # a small, slow nod
            frames += [(0.8, with_(head_pitch=hp + 0.10)), (0.8, with_(head_pitch=hp - 0.10))]
        frames += [(0.8, level), (0.5, level)]
        for _ in range(3):                     # the beak
            frames += [(0.4, with_(beak=0.3)), (0.4, level)]
        frames += [(1.0, level)]
    else:
        frames += [(a.hold, level)]
    frames += [(a.lower, dict(q0))]
    return frames


def at(frames, q0, t):
    """The pose at t s into the timeline, and its step's name, or (None, None) past the end."""
    prev = q0
    for i, (dur, f) in enumerate(frames):
        if t < dur:
            s_ = smooth(t / dur) if dur > 0 else 1.0
            phase = 'lower' if i == len(frames) - 1 else ('rise' if i < RISE_FRAMES[0] else 'stand')
            return phase, {n: prev[n] + s_ * (f[n] - prev[n]) for n in prev}
        t -= dur
        prev = f
    return None, None


def face_track(frames, q0, offset=0.0):
    """The head pitch that keeps the face straight ahead through the rise and the lower, the body tilting as the legs unfold:
    worked out at 40 points of each before the start (too slow for every tick), then blended. A function of t, or None while standing."""
    total = sum(f[0] for f in frames)
    t_rise = sum(f[0] for f in frames[:RISE_FRAMES[0]])
    t_low0 = total - frames[-1][0]
    pts = []
    for t0, t1 in ((0.0, t_rise), (t_low0, total)):
        for k in range(41):
            t = t0 + (t1 - t0) * k / 40
            _, q = at(frames, q0, min(t, total - 1e-6))
            pts.append((t, face_forward_pitch(q) + offset))

    def pitch(t):
        if t_rise <= t < t_low0:
            return None
        seg = pts[:41] if t < t_rise else pts[41:]
        for (ta, pa), (tb, pb) in zip(seg, seg[1:]):
            if ta <= t <= tb:
                return pa + (pb - pa) * (t - ta) / max(tb - ta, 1e-9)
        return seg[-1][1]
    return pitch


def standing(cfg, home):
    lim = cfg['limits']
    return {n: min(max(home.get(n, 0.0), lim[n][0]), lim[n][1]) for n in LEGS}


def preview(a, cfg, home):
    """The routine as the real run does it, on the model with no physics: the feet flat on the floor and the body following."""
    import mujoco
    import mujoco.viewer
    import twin
    if a.start:
        start = json.load(open(a.start))
    else:
        port = find_port() if a.port == 'auto' else a.port
        bus = dxl.Bus(port, timeout=0.05)
        start = twin.angles(twin.read_ticks(bus, [cfg['joints'][n]['id'] for n in ALL]), cfg, ALL)
        bus.close()
    q0 = {n: start.get(n, 0.0) for n in ALL}
    frames = timeline(a, q0, standing(cfg, home))
    total = sum(f[0] for f in frames)
    track = face_track(frames, q0, math.radians(a.head_offset)) if a.face_forward else None
    m, d, adr = twin.load_model(cfg, soles=False)
    print(f'preview: {total:.0f} s, then again. Close the window to stop.')
    with mujoco.viewer.launch_passive(m, d, show_left_ui=False, show_right_ui=False) as v:
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 0.75, 150, -15
        t0 = time.monotonic()
        while v.is_running():
            t = (time.monotonic() - t0) % (total + 2)
            _, q = at(frames, q0, t)
            if q and track is not None and track(t) is not None:
                q = dict(q, head_pitch=track(t))
            with v.lock():
                twin.pose(m, d, adr, q or q0)
                v.cam.lookat[:] = d.subtree_com[1]
            v.sync()
            time.sleep(1 / 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='auto')
    ap.add_argument('--config', default=os.path.join(HERE, 'config', 'dynamixel.json'))
    ap.add_argument('--rise', type=float, default=10.0, help='seconds from sitting to standing')
    ap.add_argument('--hold', type=float, default=20.0, help='seconds standing, without --show')
    ap.add_argument('--lower', type=float, default=10.0, help='seconds back to where it started')
    ap.add_argument('--show', action='store_true', help='at standing: the head side to side, a small slow nod, the beak open and shut')
    ap.add_argument('--stand-pose', help='a JSON of joint angles (twin.py --save-pose) to stand in: the legs, neck and head as found by hand')
    ap.add_argument('--keep-head', action='store_true', help='hold the neck and head as they are set by hand at the start; nod and tilt about that')
    ap.add_argument('--rise-lean', type=float, default=0.0, help='degrees the neck leans further forward in the first part of the rise (negative is forward), back by the end')
    ap.add_argument('--face-forward', action='store_true', help='at standing, the head pitched so the face points straight ahead (from the model geometry)')
    ap.add_argument('--neck-offset', type=float, default=0.0, help='degrees added to the standing neck: negative leans it forward (the weight forward)')
    ap.add_argument('--head-offset', type=float, default=0.0, help='degrees added to the standing head pitch: positive tips the nose down')
    ap.add_argument('--neck-pitch', type=float, default=-0.20, help='rad, at standing: leaning forward a little (0 is upright)')
    ap.add_argument('--head-pitch', type=float, default=-0.40, help='rad, at standing: tipped back, nose up (0 is level, negative is nose up)')
    ap.add_argument('--cap', type=int, default=800, help='current cap per leg servo, mA (head 600, beak 300)')
    ap.add_argument('--gain', type=int, default=800, help='position P gain (factory 400: a loaded joint sags 4 deg at 400)')
    ap.add_argument('--min-volts', type=float, default=4.6)
    ap.add_argument('--max-volts', type=float, default=6.0, help='the XL330 maximum; the simulator says 7.8 V, so give it 9 there')
    ap.add_argument('--max-lag', type=float, default=15.0, help='degrees a joint may trail its goal')
    ap.add_argument('--abort-lower', type=float, default=8.0, help='after a stop: seconds to ease back down to sitting, before the torque goes off')
    ap.add_argument('--hz', type=float, default=25.0)
    ap.add_argument('--preview', action='store_true', help='play the routine in a MuJoCo window, no physics, no servos: feet flat on the floor, as when supported')
    ap.add_argument('--start', help='with --preview: a JSON of joint angles to start from (twin.py --save-pose), else the real duck is read')
    ap.add_argument('--view', action='store_true', help='a MuJoCo window showing the joint angles the servos measure, live; a 5 s countdown first, to start a recording')
    ap.add_argument('--wait-for', help='with --view: show the duck live, torque off, until this file exists; then count down and run')
    ap.add_argument('--stop-at', type=float, help='for testing: force a stop this many seconds in')
    ap.add_argument('--log', default=os.path.join(HERE, 'stand_test_log.csv'))
    a = ap.parse_args()

    cfg = load_config(a.config)
    home = json.load(open(os.path.join(HERE, 'sim', 'model', 'home.json')))['joint_pos']
    if a.preview:
        return preview(a, cfg, home)
    port = find_port() if a.port == 'auto' else a.port
    bus = dxl.Bus(port, timeout=0.05)
    J = ALL if a.show else LEGS                  # without --show the neck, head and beak stay limp
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

    for n, i in zip(J, ids):                    # with torque off: the mode, the cap, the gain
        bus.write(i, dxl.TORQUE_ENABLE, 0)
        bus.write(i, dxl.OPERATING_MODE, MODE_CURRENT_POSITION)
        bus.write(i, GOAL_CURRENT, cap[n])
        bus.write(i, dxl.POSITION_P, a.gain)
        bus.write(i, dxl.PROFILE_VELOCITY, 0)

    def read_state():
        raw = bus.sync_read(ids, 126, 10)              # current 2, velocity 4, position 4
        cur, pos = {}, {}
        for n, i in zip(J, ids):
            b = raw[i]
            cur[n] = int.from_bytes(b[0:2], 'little', signed=True)
            pos[n] = int.from_bytes(b[6:10], 'little', signed=True)
        return cur, pos

    _, p0 = read_state()
    q0 = {}
    for n in J:
        c = cfg['joints'][n]['centre']
        q0[n] = ((p0[n] - c + 2048) % 4096 - 2048) * K * sign[n]
    full0 = {n: q0.get(n, 0.0) for n in ALL}
    frames = [(dur, {n: f[n] for n in J}) for dur, f in timeline(a, full0, standing(cfg, home))]

    def goal_ticks(q):
        return {n: p0[n] + int(round((q[n] - q0[n]) * sign[n] / K)) for n in J}

    track = None

    print('from  ' + '  '.join(f'{n}:{math.degrees(q0[n]):+.0f}' for n in J))
    print('stand ' + '  '.join(f'{n}:{math.degrees(frames[0][1][n]):+.0f}' for n in J))
    print(f'{sum(f[0] for f in frames):.0f} s in all' + (', with the head show' if a.show else ''))

    viewer = None
    if a.view:                                   # the twin, live from the servos' own readings
        import mujoco.viewer
        import twin
        vm, vd, vadr = twin.load_model(cfg, soles=False)
        seen = {n: full0.get(n, 0.0) for n in vadr}
        twin.pose(vm, vd, vadr, seen)
        viewer = mujoco.viewer.launch_passive(vm, vd, show_left_ui=False, show_right_ui=False)
        viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 0.75, 150, -15
        viewer.cam.lookat[:] = vd.subtree_com[1]
        viewer.sync()
        if a.wait_for:                          # live, read only, till the start signal
            if os.path.exists(a.wait_for):
                os.remove(a.wait_for)
            print('ready: showing the duck live, torque off. Waiting for the start signal.', flush=True)
            while not os.path.exists(a.wait_for):
                if not viewer.is_running():
                    raise SystemExit('window closed: nothing ran')
                _, pw = read_state()
                for n in J:
                    seen[n] = ((pw[n] - cfg['joints'][n]['centre'] + 2048) % 4096 - 2048) * K * sign[n]
                with viewer.lock():
                    twin.pose(vm, vd, vadr, seen)
                    viewer.cam.lookat[:] = vd.subtree_com[1]
                viewer.sync()
                time.sleep(0.04)
            os.remove(a.wait_for)
            _, p0 = read_state()                # the pose may have changed while waiting: start from where it is now
            for n in J:
                q0[n] = ((p0[n] - cfg['joints'][n]['centre'] + 2048) % 4096 - 2048) * K * sign[n]
            full0.update(q0)
            frames[:] = [(dur, {n: f[n] for n in J}) for dur, f in timeline(a, full0, standing(cfg, home))]
        for k in range(5, 0, -1):
            print(f'starting in {k} s', flush=True)
            for _ in range(25):
                time.sleep(0.04)
                if viewer.is_running():
                    viewer.sync()

    if a.face_forward and a.show:
        print('working out the face-forward head pitch along the rise and the lower...', flush=True)
        track = face_track(frames, q0, math.radians(a.head_offset))
        frames[0] = (frames[0][0], dict(frames[0][1], head_pitch=track(frames[0][0] - 1e-6)))     # the rise's own target agrees

    bus.sync_write(ids, dxl.GOAL_POSITION, [p0[n] for n in J])     # torque on, every goal where its joint is now
    for i in ids:
        bus.write(i, dxl.TORQUE_ENABLE, 1)
        bus.write(i, LED, 1)

    log = open(a.log, 'w', newline='')
    w = csv.writer(log)
    w.writerow(['t', 'phase', 'volts'] + [f'{n}_{k}' for n in J for k in ('goal_deg', 'deg', 'lag_deg', 'mA')])
    t0, last_slow, hw = time.monotonic(), 0.0, {}
    peak = {n: 0 for n in J}
    stand_cur = {n: [] for n in J}
    stopped, last_print = None, -1

    try:
        while True:
            t = time.monotonic() - t0
            phase, q = at(frames, q0, t)
            if phase is None:
                break
            if track is not None and 'head_pitch' in q:
                hpt = track(t)
                if hpt is not None:
                    q = dict(q)
                    q['head_pitch'] = hpt
            g = goal_ticks(q)
            bus.sync_write(ids, dxl.GOAL_POSITION, [g[n] for n in J])
            cur, pos = read_state()
            if t - last_slow > 0.5:
                last_slow = t
                volts = bus.read(ids[0], dxl.PRESENT_VOLTAGE) / 10
                raw = bus.sync_read(ids, HW_ERROR[0], 1)
                hw = {n: raw[i][0] for n, i in zip(J, ids)}
            row, lags = [round(t, 3), phase, volts], {}
            for n in J:
                lag = (pos[n] - g[n]) * 360 / 4096
                lags[n] = lag
                peak[n] = max(peak[n], abs(cur[n]))
                if phase == 'stand':
                    stand_cur[n].append(abs(cur[n]))
                deg = math.degrees(q0[n]) + (pos[n] - p0[n]) * sign[n] * 360 / 4096
                row += [round(math.degrees(q[n]), 2), round(deg, 2), round(lag, 2), cur[n]]
            w.writerow(row)
            if viewer is not None and viewer.is_running():
                for n in J:
                    seen[n] = q0[n] + (pos[n] - p0[n]) * sign[n] * K
                with viewer.lock():
                    twin.pose(vm, vd, vadr, seen)
                    viewer.cam.lookat[:] = vd.subtree_com[1]
                viewer.sync()
            why = None
            if a.stop_at is not None and t >= a.stop_at:
                why = f'forced stop at {a.stop_at} s (--stop-at)'
            elif any(hw.values()):
                why = 'hardware error: ' + ', '.join(f'{n} {v:#04x}' for n, v in hw.items() if v)
            elif volts < a.min_volts:
                why = f'supply {volts:.1f} V'
            else:
                worst = max(J, key=lambda n: abs(lags[n]))
                if abs(lags[worst]) > a.max_lag:
                    why = f'{worst} {lags[worst]:+.1f} deg behind'
            if why:
                # never let go mid-move: ease back down to where it started (sitting), then torque off. Lowering takes
                # less current than holding, as the weight helps, so a sagging supply can still do it. (Holding 15 s and
                # then turning the torque off dropped the duck from half standing, 2026-11-21, the user)
                stopped = (round(t, 1), phase, why)
                print(f'STOP at {t:.1f} s ({phase}): {why}. Easing back down to sitting over {a.abort_lower:.0f} s, then torque off.', flush=True)
                _, pos = read_state()
                here = {n: q0[n] + (pos[n] - p0[n]) * sign[n] * K for n in J}
                back = [(a.abort_lower, {n: q0[n] for n in J})]
                t1 = time.monotonic()
                while True:
                    tb = time.monotonic() - t1
                    _, qb = at(back, here, tb)
                    if qb is None:
                        break
                    gb = goal_ticks(qb)
                    try:
                        bus.sync_write(ids, dxl.GOAL_POSITION, [gb[n] for n in J])
                        cur, pos = read_state()
                    except dxl.DxlError as e:
                        print('during the way down:', e)
                    rowb = [round(time.monotonic() - t0, 3), 'stop-lower', volts]
                    for n in J:
                        degb = math.degrees(q0[n]) + (pos[n] - p0[n]) * sign[n] * 360 / 4096
                        rowb += [round(math.degrees(qb[n]), 2), round(degb, 2), round((pos[n] - gb[n]) * 360 / 4096, 2), cur[n]]
                    w.writerow(rowb)
                    if viewer is not None and viewer.is_running():
                        for n in J:
                            seen[n] = q0[n] + (pos[n] - p0[n]) * sign[n] * K
                        with viewer.lock():
                            twin.pose(vm, vd, vadr, seen)
                        viewer.sync()
                    time.sleep(1 / a.hz)
                time.sleep(0.5)                 # seated: settle, then let go
                break
            if int(t) != last_print:
                last_print = int(t)
                worst = max(J, key=lambda n: abs(lags[n]))
                print(f'{t:5.1f} s {phase:5s} {volts:.1f} V  worst lag {abs(lags[worst]):4.1f} deg ({worst})  '
                      f'current {sum(abs(c) for c in cur.values())} mA total, max {max(abs(c) for c in cur.values())} mA')
            time.sleep(max(0.0, 1 / a.hz - (time.monotonic() - t0 - t)))
    finally:
        for i in ids:
            try:
                bus.write(i, dxl.TORQUE_ENABLE, 0)
                bus.write(i, LED, 0)
                bus.write(i, dxl.OPERATING_MODE, dxl.MODE_POSITION)
            except dxl.DxlError:
                pass
        log.close()
        if viewer is not None:
            time.sleep(2)
            viewer.close()
        temps = {}
        for n, i in zip(J, ids):
            try:
                temps[n] = bus.read(i, dxl.PRESENT_TEMPERATURE)
            except dxl.DxlError:
                temps[n] = None
        bus.close()

    print('\ntorque off. ' + (f'Stopped at {stopped[0]} s, {stopped[1]}: {stopped[2]}' if stopped else 'Finished.'))
    print(f'{"joint":16s} {"peak mA":>8s} {"stand mA":>9s} {"of cap":>7s} {"temp C":>7s}')
    for n in J:
        h = sum(stand_cur[n]) / len(stand_cur[n]) if stand_cur[n] else float('nan')
        print(f'{n:16s} {peak[n]:8d} {h:9.0f} {h / cap[n] * 100:6.0f}% {temps[n]!s:>7s}')
    print('log:', a.log)


if __name__ == '__main__':
    main()
