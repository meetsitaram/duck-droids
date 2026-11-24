"""What the duck's Pi reads, sent to a PC over Wi-Fi: every servo's raw position (ticks, by id) and the IMU's gravity and gyro, as one JSON
line per reading, to every PC connected on TCP --port (9100). The digital twin draws it: `python twin.py --remote <pi address>`.

Only one program can own the servo bus, so whichever one does sends this: `telemetry.py` (read only, nothing moves) or `run_policy.py
--telemetry` (while the Pi drives the duck). A PC that is slow or gone is dropped; the Pi never waits for one.
"""
import json
import socket
import threading

PORT = 9100


class Publisher:
    def __init__(self, port=PORT):
        self.clients = []
        self.lock = threading.Lock()
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('0.0.0.0', port))
        self.srv.listen(4)
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            try:
                c, addr = self.srv.accept()
            except OSError:
                return
            c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            c.setblocking(False)
            print(f'telemetry: {addr[0]} connected', flush=True)
            with self.lock:
                self.clients.append(c)

    def send(self, ticks, grav=None, gyro=None, **extra):
        """ticks: {servo id: raw position}; grav, gyro: 3 floats each, in the robot's frame (as the policy sees them)."""
        if not self.clients:
            return
        msg = {'ticks': {str(k): int(v) for k, v in ticks.items()}}
        if grav is not None:
            msg['grav'] = [round(float(x), 4) for x in grav]
        if gyro is not None:
            msg['gyro'] = [round(float(x), 4) for x in gyro]
        msg.update(extra)
        line = (json.dumps(msg) + '\n').encode()
        with self.lock:
            for c in list(self.clients):
                try:
                    c.send(line)
                except (BlockingIOError, OSError):        # full or gone: drop it rather than hold the control loop
                    self.clients.remove(c)
                    c.close()

    def close(self):
        self.srv.close()


class Receiver:
    """On the PC: the latest message from the Pi, read in a thread. .latest is None until the first arrives."""

    def __init__(self, addr):
        host, _, port = addr.partition(':')
        self.addr = (host, int(port or PORT))
        self.latest = None
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        import time
        while True:
            try:
                s = socket.create_connection(self.addr, timeout=3)
                s.settimeout(3)
                buf = b''
                while True:
                    data = s.recv(65536)
                    if not data:
                        break
                    buf += data
                    *lines, buf = buf.split(b'\n')
                    if lines:
                        self.latest = json.loads(lines[-1])
            except OSError:
                pass
            self.latest = None
            time.sleep(1)
