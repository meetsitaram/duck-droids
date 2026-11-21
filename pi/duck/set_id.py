"""Give one servo its joint's id and the duck's baud rate. Plug in ONE servo only: a new XL330 is id 1, and two at id 1 answer over each other.

  python -m duck.set_id left_knee --port COM5          (a PC, through the Waveshare board's USB-C, jumpers at B)
  python -m duck.set_id left_knee --port /dev/serial0  (the Pi, jumpers at A)
  python -m duck.set_id --all                          (all 15, one at a time: right leg, left leg, neck, head, bottom up)
  python -m duck.set_id --all --start left_ankle       (carry on from a joint)
  python -m duck.set_id --find                         (the servo plugged in: its id, baud rate and voltage; changes nothing)
  python -m duck.set_id --scan                         (every servo on the bus at 1 Mbps, with its joint)

--port is found by itself on a PC; name it (COM5, /dev/serial0) if there's more than one.

It finds the servo at any id and at 57600 (a new XL330) or 1 Mbps, turns its torque off, writes the id from config/dynamixel.json,
then the baud rate, and checks it answers at the new id at 1 Mbps. Then a bench test: 10 degrees each way, slowly, LED on, so you see which servo
it is and that it reaches its targets, and back where it was. Where you set it by hand is kept as its middle position. No big moves. Label it.
What it is and how it tested are kept in config/servos.json, by id. Only on the bench: in the robot, a move could hit a joint's limit.
"""
import argparse
import datetime
import json
import os
import time

from . import dxl
from .hardware import load_config

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CFG = os.path.join(HERE, 'config', 'dynamixel.json')
MODEL_NUMBER = (0, 2)
ID = (7, 1)
LED = (65, 1)
HW_ERROR = (70, 1)
MOVING = (122, 1)
PRESENT_CURRENT = (126, 2)       # mA
FIRMWARE = (6, 1)
DEFAULT_POSITION = 2048          # mid-range, tick 2048: only with park=True, a move that can be big
TEST_STEP = 114                  # ticks each way in the bench test, 10 degrees: inside every joint's design range
MODELS = {1200: 'XL330-M288', 1190: 'XL330-M077', 1220: 'XC330-M288', 1210: 'XC330-M181'}
MAX_VOLTS = 6.0       # ROBOTIS's maximum; past 7.0 V it also shuts its torque off
BAUDS = {57600: 1, 1_000_000: 3, 115200: 2, 2_000_000: 4, 9600: 0}   # bps: the value at address 8. Not 3-4.5 Mbps: they can wedge the CH343's driver on Windows


def find_port():
    """The bus board's USB serial port, on a PC. The Pi uses /dev/serial0."""
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    wch = [p for p in ports if p.vid == 0x1A86]          # WCH, the maker of the board's USB chip (CH340/CH343)
    pick = wch or [p for p in ports if p.vid is not None]
    if len(pick) == 1:
        print(f'port {pick[0].device} ({pick[0].description})')
        return pick[0].device
    listing = '\n'.join(f'  {p.device}  {p.description}' for p in ports) or '  none: is the board plugged in, and its USB driver installed?'
    raise SystemExit(f'pick the bus board with --port:\n{listing}')


def find_one(port):
    """(baud, id) of the one servo on the bus, from a broadcast ping at each baud rate."""
    for baud in BAUDS:
        bus = dxl.Bus(port, baud=baud, timeout=0.05)
        try:
            bus._send(dxl.packet(dxl.BROADCAST, dxl.PING))
            found = []
            try:
                while True:
                    found.append(bus._status()[0])
            except dxl.DxlError as e:
                if 'CRC' in str(e):      # two servos at one id answer at once, and garble each other
                    raise SystemExit(f'garbled answers at {baud} bps: more than one servo is plugged in. Unplug all but one')
        finally:
            bus.close()
        if len(found) > 1:
            raise SystemExit(f'{len(found)} servos answered at {baud} bps (ids {sorted(found)}): unplug all but one')
        if found:
            return baud, found[0]
    raise SystemExit('no servo answered at any baud rate: check its power (the board\'s green terminals), the jumpers, and the plug')


KEPT_BEFORE_RESET = {'homing_offset': (20, 4), 'min_position_limit': (52, 4), 'max_position_limit': (48, 4), 'drive_mode': (10, 1),
                     'operating_mode': (11, 1), 'position_p': (84, 2), 'current_limit': (38, 2)}
FACTORY_RESET = 0x06


def reset_all_but_id_and_baud(bus, ident):
    """Factory settings, but its id and baud rate kept. A servo set up for another robot (Seeed's Reachy Mini servos come
    with a homing offset and narrow position limits) would refuse the bench test and shift every position the duck reads."""
    bus.write(ident, dxl.TORQUE_ENABLE, 0)
    bus._send(dxl.packet(ident, FACTORY_RESET, b''))
    try:
        bus._status()
    except dxl.DxlError:
        pass
    time.sleep(1.0)                     # it reboots
    for _ in range(20):
        try:
            if bus.ping(ident):
                break
        except dxl.DxlError:
            time.sleep(0.1)
    else:
        raise SystemExit(f'id {ident} does not answer after its factory reset: run again')
    off, lo, hi = bus.read(ident, (20, 4), signed=True), bus.read(ident, (52, 4)), bus.read(ident, (48, 4))
    if (off, lo, hi) != (0, 0, 4095):
        raise SystemExit(f'factory reset did not take: homing offset {off}, limits {lo}-{hi}')


def go(bus, ident, target, timeout=4.0, close=8):
    """Move to a tick and wait till it gets there, or stops changing short of it. (reached tick, peak current mA, seconds).
    Not the Moving flag: it reads 0 before a move starts, and again while a slow move creeps in its last few ticks."""
    bus.write(ident, dxl.GOAL_POSITION, target)
    t0, peak, hist = time.monotonic(), 0, []
    while True:
        time.sleep(0.02)
        peak = max(peak, abs(bus.read(ident, PRESENT_CURRENT, signed=True)))
        pos = bus.read(ident, dxl.PRESENT_POSITION, signed=True)
        dt = time.monotonic() - t0
        hist.append((dt, pos))
        if abs(pos - target) <= 2:
            break
        settled = [p for t, p in hist if t > dt - 0.3]
        if dt > 0.6 and max(settled) - min(settled) <= 1:
            break                       # still for 0.3 s: as close as it gets
        if dt > timeout:
            break
    return pos, peak, round(dt, 2)


def nudge_step(cfg, joint):
    """10 degrees, or 80% of the joint's smaller limit from its middle if that's less: the neck goes only 8.6 degrees up.
    A joint with no limits in the config (the beak) gets 5 degrees."""
    import math
    lim = cfg.get('limits', {}).get(joint)
    if not lim:
        return 57
    return int(min(TEST_STEP, 0.8 * min(abs(lim[0]), abs(lim[1])) * 4096 / (2 * math.pi)))


def bench_test(bus, ident, park=False, step=TEST_STEP):
    """On the bench: 10 degrees each way, slowly, LED on, so you see which servo it is and that it reaches its targets, then
    back where it was. Where it was is kept as its middle position, as set by hand. park=True would move it to mid-range, tick 2048,
    which can be a big turn: not used before assembly. Torque off afterwards. Returns what it measured."""
    bus.write(ident, dxl.TORQUE_ENABLE, 0)
    bus.write(ident, dxl.OPERATING_MODE, dxl.MODE_POSITION)
    bus.write(ident, dxl.PROFILE_VELOCITY, 15)            # slow enough to watch
    here = bus.read(ident, dxl.PRESENT_POSITION, signed=True)
    r = dict(position_found=here, middle_position=here)    # where it was set by hand: kept, not moved
    base = min(max(here, step), 4095 - step)                 # position mode takes 0-4095
    bus.write(ident, LED, 1)
    bus.write(ident, dxl.TORQUE_ENABLE, 1)
    moves, worst = [], 0
    for t in [base + step, base - step] + ([DEFAULT_POSITION] if park else [here]):
        got, peak, secs = go(bus, ident, t, timeout=6)
        time.sleep(1.0)                                   # a pause at each end, to see it
        worst = max(worst, abs(got - t))
        moves.append(dict(target=t, reached=got, peak_mA=peak, s=secs))
    time.sleep(0.3)
    r['idle_mA'] = abs(bus.read(ident, PRESENT_CURRENT, signed=True))
    bus.write(ident, dxl.TORQUE_ENABLE, 0)
    bus.write(ident, LED, 0)
    r.update(moves=moves, worst_error_ticks=worst, passed=worst <= 20, hardware_error=bus.read(ident, HW_ERROR))
    if park:
        r['parked_at'] = moves[-1]['reached']
    print(f"  moved {'+'.join(str(m['reached']) for m in moves)} ticks, worst error {worst} ({worst * 360 / 4096:.1f} deg), "
          f"peak {max(m['peak_mA'] for m in moves)} mA, idle {r['idle_mA']} mA: {'OK' if r['passed'] else 'FAILED: it did not reach its targets'}")
    if r['hardware_error']:
        print(f"  hardware error flags {r['hardware_error']:#04x}: see Hardware Error Status in ROBOTIS's manual")
    return r


def record(cfg_path, ident, joint, info):
    """Keep what each servo is and how it tested, in config/servos.json, by id: for later, and to tell servos apart."""
    path = os.path.join(os.path.dirname(cfg_path), 'servos.json')
    try:
        data = json.load(open(path, encoding='utf-8'))
    except FileNotFoundError:
        data = {'about': 'One entry per servo, by id: written by python -m duck.set_id. Positions are ticks, 4096 a turn; '
                         'middle_position is where it was set by hand when its id was set; it is not moved there or from there.', 'servos': {}}
    old = data['servos'].get(str(ident), {})
    if old.get('joint') == joint and 'settings_before_reset' in old:
        info['settings_before_reset'] = old['settings_before_reset']      # what it came with: a rerun sees its own reset
    data['servos'][str(ident)] = dict(joint=joint, **info)
    data['servos'] = dict(sorted(data['servos'].items(), key=lambda kv: int(kv[0])))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    print(f'  saved to {os.path.relpath(path)}')


def set_id(port, joint, cfg, move=True, cfg_path=None):
    cfg_path = cfg_path or DEFAULT_CFG
    new = cfg['joints'][joint]['id']
    baud, old = find_one(port)
    bus = dxl.Bus(port, baud=baud, timeout=0.05)
    model = bus.read(old, MODEL_NUMBER)
    volts = bus.read(old, dxl.PRESENT_VOLTAGE) / 10
    print(f'found {MODELS.get(model, f"model {model}")} at id {old}, {baud} bps, {volts:.1f} V')
    if volts > MAX_VOLTS:
        bus.close()
        raise SystemExit(f'{volts:.1f} V is past the XL330\'s {MAX_VOLTS} V maximum: power the board from 5 V')
    bus.write(old, dxl.TORQUE_ENABLE, 0)        # the id and baud are in EEPROM, writable only with torque off
    if old != new:
        bus.write(old, ID, new)
    if baud != 1_000_000:
        bus._send(dxl.packet(new, dxl.WRITE, bytes((dxl.BAUD_RATE[0], 0, BAUDS[1_000_000]))))
        time.sleep(0.1)                         # it may answer at the old rate, or not at all: check below instead
    bus.close()
    bus = dxl.Bus(port, baud=1_000_000, timeout=0.05)
    if not bus.ping(new):
        raise SystemExit(f'it does not answer at id {new}, 1 Mbps: run again')
    before = {k: bus.read(new, r, signed=k == 'homing_offset') for k, r in KEPT_BEFORE_RESET.items()}
    reset_all_but_id_and_baud(bus, new)
    print(f'{joint}: id {new}, 1 Mbps, factory settings. Label it "{new} {joint}".')
    info = dict(model=MODELS.get(model, model), model_number=model, firmware=bus.read(new, FIRMWARE), baud=1_000_000,
                id_set_on=datetime.date.today().isoformat(), volts=volts, temperature_c=bus.read(new, dxl.PRESENT_TEMPERATURE),
                default_position=DEFAULT_POSITION, settings_before_reset=before)
    if move:
        info['bench_test'] = bench_test(bus, new, step=nudge_step(cfg, joint))
        info['middle_position'] = info['bench_test']['middle_position']
    bus.close()
    record(cfg_path, new, joint, info)


ORDER = ['right_ankle', 'right_knee', 'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
         'left_ankle', 'left_knee', 'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw',
         'neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'beak']      # right leg, left leg, neck, head: each from the bottom up


def set_all(port, cfg, move=True, start=None, cfg_path=None):
    """Every joint in ORDER, from `start`: plug in its servo alone, press Enter, label it, unplug it."""
    joints = [n for n in ORDER if n in cfg['joints']] + [n for n in cfg['joints'] if n not in ORDER]
    if start:
        joints = joints[joints.index(start):]
    done = []
    for n in joints:
        i = cfg['joints'][n]['id']
        while True:
            k = input(f'\nPlug in ONLY the servo for {n} (id {i}). Enter to set it, s to skip, q to quit: ').strip().lower()
            if k == 'q':
                return print('done:', ', '.join(done) or 'none')
            if k == 's':
                break
            try:
                set_id(port, n, cfg, move=move, cfg_path=cfg_path)
                done.append(f'{i} {n}')
                break
            except (SystemExit, dxl.DxlError) as e:
                print('not set:', e)
    print('\ndone:', ', '.join(done))


def scan(port, cfg):
    by_id = {j['id']: n for n, j in cfg['joints'].items()}
    bus = dxl.Bus(port, baud=1_000_000, timeout=0.03)     # a USB adapter on Windows can take over 10 ms to hand back an answer
    seen = []
    for i in range(253):
        try:
            if bus.ping(i):
                seen.append(i)
                model = bus.read(i, MODEL_NUMBER)
                print(f'id {i:3d}  {MODELS.get(model, model)!s:12s} {by_id.get(i, "NOT A DUCK JOINT")}')
        except dxl.DxlError:
            pass
    bus.close()
    missing = sorted(set(by_id) - set(seen))
    print(f'{len(seen)} answered.', 'Missing: ' + ', '.join(f'{i} {by_id[i]}' for i in missing) if missing else 'All 15 joints answered.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('joint', nargs='?', help='a joint name from the config, e.g. left_knee')
    ap.add_argument('--port', default='auto', help='auto (the board on a PC\'s USB), /dev/serial0 on the Pi, or COM5 etc.')
    ap.add_argument('--config', default=DEFAULT_CFG)
    ap.add_argument('--scan', action='store_true', help='list every servo on the bus at 1 Mbps')
    ap.add_argument('--find', action='store_true', help='find the one servo plugged in, at any id and baud rate, and change nothing')
    ap.add_argument('--all', action='store_true', help='all 15 joints in order, one servo at a time')
    ap.add_argument('--nudge', type=int, metavar='ID', help='only the 10 degree nudge of the bench test, each way and back, on a servo already set: changes no setting')
    ap.add_argument('--start', help='with --all: begin at this joint, to carry on after a break')
    ap.add_argument('--no-move', action='store_true', help="don't turn the horn afterwards")
    a = ap.parse_args()
    cfg = load_config(a.config)
    port = find_port() if a.port == 'auto' else a.port
    if a.nudge is not None:
        bus = dxl.Bus(port, baud=1_000_000, timeout=0.05)
        bench_test(bus, a.nudge)
        bus.close()
    elif a.scan:
        scan(port, cfg)
    elif a.find:
        baud, i = find_one(port)
        bus = dxl.Bus(port, baud=baud, timeout=0.05)
        m = bus.read(i, MODEL_NUMBER)
        print(f'{MODELS.get(m, f"model {m}")} at id {i}, {baud} bps, {bus.read(i, dxl.PRESENT_VOLTAGE) / 10:.1f} V')
    elif a.all:
        set_all(port, cfg, move=not a.no_move, start=a.start, cfg_path=a.config)
    elif a.joint in cfg['joints']:
        set_id(port, a.joint, cfg, move=not a.no_move, cfg_path=a.config)
    else:
        raise SystemExit('name a joint, or use --all, --find or --scan. Joints: ' + ', '.join(cfg['joints']))
