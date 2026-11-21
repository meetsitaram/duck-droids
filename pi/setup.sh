#!/bin/bash
# One setup for every machine that runs the duck's code, in pi/.venv. Run it from anywhere: bash pi/setup.sh
#   On the Raspberry Pi Zero 2 W: hands over to setup_pi.sh (its UART, I2C and Bluetooth, then the venv with everything).
#   On a PC (Windows in Git Bash, Linux, macOS): the servo tools, duck.set_id and duck.calibrate, through the bus board's USB.
#     bash setup.sh --sim   also the simulator and the policy runtime: sim/server.py, run.py
set -e
cd "$(dirname "$0")"
if grep -qs 'Raspberry Pi' /proc/device-tree/model; then
  exec bash setup_pi.sh
fi
PY=$(command -v python3 || command -v python)
[ -d .venv ] || "$PY" -m venv .venv
if [ -x .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi
"$VPY" -m pip install -q --upgrade pip
"$VPY" -m pip install -q -r requirements-pc.txt
if [ "$1" = "--sim" ]; then "$VPY" -m pip install -q -r requirements.txt mujoco; fi
"$VPY" -c "import serial, numpy; print('ready: pyserial', serial.__version__, 'numpy', numpy.__version__)"
echo "Then, in pi/: $VPY -m duck.set_id --find"
