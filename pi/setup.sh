#!/bin/bash
# One venv, pi/.venv, for everything that runs the duck's code. Run it from anywhere: bash pi/setup.sh [--sim] [--tools] [--all]
#   On the Raspberry Pi Zero 2 W: hands over to setup_pi.sh (its UART, I2C and Bluetooth, then requirements.txt).
#   On a PC (Windows in Git Bash, Linux, macOS):
#     (nothing)  the servo tools: duck.set_id, duck.calibrate (requirements-pc.txt)
#     --sim      also the simulator, the policy runtime and the digital twin: sim/server.py, run.py, twin.py (requirements-sim.txt)
#     --tools    also the design tools: spec/, tools/, the gates, the sim model, renders (../requirements-tools.txt)
#     --all      all of them. The repo root's setup.sh runs this.
# Nothing goes into the system Python: run everything with the venv's Python, .venv/Scripts/python.exe on Windows, .venv/bin/python elsewhere.
set -e
cd "$(dirname "$0")"
if grep -qs 'Raspberry Pi' /proc/device-tree/model; then
  exec bash setup_pi.sh
fi
SIM=; TOOLS=
for a in "$@"; do
  case "$a" in
    --sim) SIM=1 ;;
    --tools) TOOLS=1 ;;
    --all) SIM=1; TOOLS=1 ;;
    *) echo "unknown option $a"; exit 1 ;;
  esac
done
PY=$(command -v python3 || command -v python)
[ -d .venv ] || "$PY" -m venv .venv
if [ -x .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi
"$VPY" -m pip install -q --upgrade pip
REQ=(-r requirements-pc.txt)
[ -n "$SIM" ] && REQ+=(-r requirements-sim.txt)
[ -n "$TOOLS" ] && REQ+=(-r ../requirements-tools.txt)
"$VPY" -m pip install -q "${REQ[@]}"
"$VPY" -c "import serial, numpy; print('ready: pyserial', serial.__version__, 'numpy', numpy.__version__)"
[ -n "$SIM" ] && "$VPY" -c "import mujoco; print('       mujoco', mujoco.__version__)"
[ -n "$TOOLS" ] && "$VPY" -c "import manifold3d, trimesh, scipy, shapely, imageio; print('       tools: trimesh', trimesh.__version__, 'scipy', scipy.__version__, 'shapely', shapely.__version__)"
echo "Python: pi/$VPY"
