#!/bin/bash
# Everything the repo needs on a PC, in one venv: pi/.venv. The servo tools, the simulator and digital twin, and the design tools.
# On the Pi it sets up the Pi instead (pi/setup_pi.sh). Then run Python as pi/.venv/Scripts/python.exe (Windows) or pi/.venv/bin/python.
exec bash "$(dirname "$0")/pi/setup.sh" --all
