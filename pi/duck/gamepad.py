"""A gamepad for run_policy.py --pad: an Xbox controller over Bluetooth on the Pi (Linux evdev, read straight from /dev/input, no extra
package), or a scripted one for testing against the simulator. Both give the same Pad.state(): sticks in -1..1 with up and left positive (the
robot's +x and +y, and a left turn), triggers 0..1, the d-pad -1/0/1 (up and left positive), and the set of buttons held. A pad that has
vanished (Bluetooth dropped) reads as lost; the controller sends nothing while nothing moves, so silence alone is not lost.

  python -m duck.gamepad            prints what the controller sends (no servos), to check the mapping
"""
import os
import re
import struct
import threading
import time

# Linux input event codes (linux/input-event-codes.h), as an Xbox Series controller over Bluetooth shows them (hid-generic or xpadneo)
BUTTONS = {304: 'A', 305: 'B', 307: 'X', 308: 'Y', 310: 'LB', 311: 'RB', 158: 'View', 314: 'View', 315: 'Menu', 139: 'Menu',
           316: 'Xbox', 172: 'Xbox', 317: 'LS', 318: 'RS', 167: 'Share'}
# axes: name, and whether up/left is the low end (then flipped, so up and left come out positive)
AXES = {0: ('lx', True), 1: ('ly', True), 2: ('rx', True), 5: ('ry', True), 3: ('rx', True), 4: ('ry', True),
        9: ('rt', False), 10: ('lt', False), 16: ('dx', True), 17: ('dy', True)}
EV_KEY, EV_ABS, EV_FF = 1, 3, 0x15
FF_RUMBLE = 0x50
# struct ff_effect on 64-bit Linux (48 bytes): type, id, direction, trigger (button, interval), replay (length, delay), then the union at
# offset 16, whose rumble part is (strong_magnitude, weak_magnitude)
FF_EFFECT = struct.Struct('<HhHHHHH2xHH28x')
EVIOCSFF = (1 << 30) | (FF_EFFECT.size << 16) | (ord('E') << 8) | 0x80
TRIGGER_DOWN = 0.5                              # a trigger past half way counts as held, as 'RT' or 'LT', for button combos
EVENT = struct.Struct('llHHi')                  # struct input_event on 64-bit Linux: time (2 longs), type, code, value
ABSINFO = struct.Struct('6i')                   # struct input_absinfo: value, minimum, maximum, fuzz, flat, resolution


def _eviocgabs(code):
    return (2 << 30) | (ABSINFO.size << 16) | (ord('E') << 8) | (0x40 + code)


class State:
    def __init__(self):
        self.axes = {k: 0.0 for k in ('lx', 'ly', 'rx', 'ry', 'lt', 'rt', 'dx', 'dy')}
        self.held = set()
        self.lost = True

    def copy(self):
        s = State()
        s.axes, s.held, s.lost = dict(self.axes), set(self.held), self.lost
        for t, b in (('rt', 'RT'), ('lt', 'LT')):         # the triggers as buttons too, for combos like RT + A
            if s.axes[t] > TRIGGER_DOWN:
                s.held.add(b)
        return s


class Holds:
    """Button combos that act only when held together for `seconds` (1 s), so a brush or a mashed button does nothing. check(state) returns
    the combo's name once per hold, at the moment it completes; let go of it to arm it again."""

    def __init__(self, combos, seconds=1.0):
        self.combos = {name: frozenset(bs) for name, bs in combos.items()}
        self.seconds = seconds
        self.since = {}
        self.fired = set()

    def check(self, state):
        now = time.monotonic()
        out = None
        for name, bs in self.combos.items():
            if not state.lost and bs <= state.held:
                t0 = self.since.setdefault(name, now)
                if now - t0 >= self.seconds and name not in self.fired:
                    self.fired.add(name)
                    out = out or name
            else:
                self.since.pop(name, None)
                self.fired.discard(name)
        return out

    def holding(self, state):
        """True while any combo is held (complete or not), so its buttons' single presses can be ignored meanwhile."""
        return any(bs <= state.held for bs in self.combos.values())


def deadzone(v, dz=0.12):
    """Rescaled so the stick's edge is still 1 and its slack round the middle is 0."""
    if abs(v) < dz:
        return 0.0
    return (abs(v) - dz) / (1 - dz) * (1 if v > 0 else -1)


class EvdevPad:
    """The first input device whose name has 'Xbox' (or --pad-name), read in a thread, reopened whenever it comes back after a drop."""

    def __init__(self, name='Xbox'):
        self.name = name
        self._s = State()
        self._lock = threading.Lock()
        self._stop = False
        self.device = None
        self._fd = None
        self._effect = None
        threading.Thread(target=self._run, daemon=True).start()

    def rumble(self, ms=250, strength=0.8):
        """Vibrate the controller (force feedback through hid-microsoft); quietly nothing if it can't."""
        import fcntl
        fd = self._fd
        if fd is None:
            return
        m = int(max(0.0, min(1.0, strength)) * 0xFFFF)
        try:
            buf = bytearray(FF_EFFECT.pack(FF_RUMBLE, -1 if self._effect is None else self._effect, 0, 0, 0, int(ms), 0, m, m))
            fcntl.ioctl(fd, EVIOCSFF, buf)
            self._effect = FF_EFFECT.unpack(buf)[1]
            os.write(fd, EVENT.pack(0, 0, EV_FF, self._effect, 1))
        except OSError:
            self._effect = None

    def _find(self):
        try:
            text = open('/proc/bus/input/devices').read()
        except OSError:
            return None
        for blk in text.split('\n\n'):
            if self.name.lower() in blk.lower():
                m = re.search(r'\b(event\d+)\b', blk)
                if m:
                    return '/dev/input/' + m.group(1)
        return None

    def _run(self):
        import fcntl
        import select
        while not self._stop:
            path = self._find()
            if not path:
                time.sleep(0.3)
                continue
            try:
                fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)      # read and write: writing plays the rumble
            except OSError:
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                except OSError:
                    time.sleep(0.3)
                    continue
            rng = {}
            for code in AXES:
                buf = bytearray(ABSINFO.size)
                try:
                    fcntl.ioctl(fd, _eviocgabs(code), buf)
                    _, lo, hi, *_ = ABSINFO.unpack(buf)
                    if hi > lo:
                        rng[code] = (lo, hi)
                except OSError:
                    pass
            with self._lock:
                self._s = State()
                self._s.lost = False
            self.device = path
            self._fd, self._effect = fd, None
            try:
                while not self._stop:
                    r, _, _ = select.select([fd], [], [], 0.2)
                    if not r:
                        if not os.path.exists(path):
                            raise OSError('gone')
                        continue
                    data = os.read(fd, EVENT.size * 64)
                    with self._lock:
                        for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
                            _, _, typ, code, val = EVENT.unpack_from(data, i)
                            if typ == EV_KEY and code in BUTTONS:
                                (self._s.held.add if val else self._s.held.discard)(BUTTONS[code])
                            elif typ == EV_ABS and code in AXES and code in rng:
                                name, flip = AXES[code]
                                lo, hi = rng[code]
                                if name in ('lt', 'rt'):
                                    v = (val - lo) / (hi - lo)
                                else:
                                    v = 2 * (val - lo) / (hi - lo) - 1
                                    v = -v if flip else v
                                self._s.axes[name] = max(-1.0, min(1.0, v))
            except OSError:
                pass
            finally:
                self._fd = None
                os.close(fd)
                self.device = None
                with self._lock:
                    self._s = State()                     # lost: everything released
            time.sleep(0.3)

    def state(self):
        with self._lock:
            return self._s.copy()

    def close(self):
        self._stop = True


class ScriptPad:
    """For the simulator: 'seconds:what;...' from when it is made, each what one of A, B, X, Y, LB+RB (a press), ly=0.8 or rx=-0.5 (held
    until changed), or lost / found. e.g. '1:A;14:ly=0.8;20:ly=0;22:rx=0.6;26:rx=0;28:X;34:B;50:Menu'"""

    def __init__(self, script):
        self.events = []
        for item in filter(None, (s.strip() for s in script.split(';'))):
            t, what = item.split(':', 1)
            self.events.append((float(t), what.strip()))
        self.t0 = time.monotonic()
        self._s = State()
        self._s.lost = False
        self._press = {}                                  # button -> release time
        self.device = 'script'

    def state(self):
        now = time.monotonic() - self.t0
        while self.events and self.events[0][0] <= now:
            _, what = self.events.pop(0)
            if '=' in what and what.split('=')[0].strip().isupper():     # A=1 holds A down, A=0 lets go (for 1 s holds)
                k, v = (x.strip() for x in what.split('='))
                (self._s.held.add if float(v) else self._s.held.discard)(k)
            elif '=' in what:
                k, v = what.split('=')
                self._s.axes[k.strip()] = float(v)
            elif what == 'lost':
                self._s.lost = True
            elif what == 'found':
                self._s.lost = False
            else:
                for b in what.split('+'):
                    self._s.held.add(b)
                    self._press[b] = now + 0.2
        for b, until in list(self._press.items()):
            if now >= until:
                self._s.held.discard(b)
                del self._press[b]
        return self._s.copy()

    def rumble(self, ms=250, strength=0.8):
        print(f'(rumble {ms} ms)', flush=True)

    def close(self):
        pass


def open_pad(spec='evdev', name='Xbox'):
    return EvdevPad(name) if spec == 'evdev' else ScriptPad(spec)


if __name__ == '__main__':
    pad = EvdevPad()
    last = None
    print('move the sticks and press buttons; Ctrl-C to stop')
    try:
        while True:
            s = pad.state()
            line = ('LOST' if s.lost else pad.device) + '  ' + '  '.join(f'{k} {v:+.2f}' for k, v in s.axes.items()) + '  held ' + (' '.join(sorted(s.held)) or '-')
            if line != last:
                print(line, flush=True)
                last = line
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
