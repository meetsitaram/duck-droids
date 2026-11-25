"""Watch the duck from a PC on the same Wi-Fi: the live twin (MuJoCo, the real duck's joints and body angle, from the stream every run sends
on port 9100) and the duck's launcher log (over SSH), together, until Ctrl-C.

  python watch.py                                  the Pi in the repo root's .env (DUCK_USER, DUCK_HOST, DUCK_KEY; git-ignored)
  python watch.py ADDRESS --user pi --key ~/.ssh/duck_ed25519   another Pi
  python watch.py ADDRESS --no-log                 the twin only (no SSH needed)
  python watch.py ADDRESS --no-twin                the log only

The twin needs nothing on the Pi but a running mode: the stand, walk and head modes send their state (servo positions, IMU) on port 9100 with
--telemetry, and the twin reconnects by itself whenever a mode starts. With the launcher idle nothing is sent, and the window keeps the last pose.
The log is ~/duck/launcher.log on the Pi (install_launcher_user.sh), the IMU library's debug dumps left out. Run it with the repo's Python
(pi/.venv, from setup.sh): the twin needs MuJoCo.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = ('DBG::', '\t\t', '*******', '[0x')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    from duck import env
    env.load()
    ap.add_argument('address', nargs='?', default=os.environ.get('DUCK_HOST'), help="the duck's Pi on the network, e.g. 192.168.1.50 or duck.local")
    ap.add_argument('--user', default=os.environ.get('DUCK_USER', 'pi'), help='SSH user on the Pi (or set DUCK_USER)')
    ap.add_argument('--key', default=os.environ.get('DUCK_KEY', os.path.expanduser('~/.ssh/duck_ed25519')), help='SSH key (or set DUCK_KEY)')
    ap.add_argument('--port', type=int, default=9100, help='telemetry port')
    ap.add_argument('--no-log', action='store_true')
    ap.add_argument('--no-twin', action='store_true')
    a = ap.parse_args()
    if not a.address:
        ap.error("no Pi address: copy .env.example to .env at the repo root (DUCK_HOST), or give it")

    procs = []
    if not a.no_twin:
        twin = subprocess.Popen([sys.executable, '-u', os.path.join(HERE, 'twin.py'), '--remote', f'{a.address}:{a.port}' if a.port != 9100 else a.address],
                                cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(twin)
        print(f'twin: window opening; it shows the duck whenever a mode is running on {a.address}', flush=True)
    log = None
    if not a.no_log:
        cmd = ['ssh', '-o', 'ConnectTimeout=8', '-o', 'ServerAliveInterval=5']
        if a.key and os.path.exists(a.key):
            cmd += ['-i', a.key]
        cmd += [f'{a.user}@{a.address}', 'echo "connected: $(hostname), $(uptime -p), $(vcgencmd get_throttled 2>/dev/null)"; '
                'systemctl --user is-active duck-launcher | sed "s/^/launcher: /"; tail -n 20 -F ~/duck/launcher.log']
        log = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        procs.append(log)
    try:
        if log:
            for line in log.stdout:
                if not any(n in line for n in NOISE) and line.strip():
                    print(line.rstrip(), flush=True)
            print('log: connection ended (is the Pi on? the address right?)', flush=True)
        while procs[0].poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()


if __name__ == '__main__':
    main()
