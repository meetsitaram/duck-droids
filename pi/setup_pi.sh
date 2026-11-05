#!/bin/bash
# On a fresh Raspberry Pi OS Lite, 64-bit, in the folder holding this file. Not yet tried on a real Pi.
set -e
sudo apt-get update
sudo apt-get install -y python3-venv i2c-tools
sudo raspi-config nonint do_i2c 0
sudo usermod -aG dialout,i2c "$USER"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt adafruit-blinka adafruit-circuitpython-bno08x
# The Pi's micro USB as host, for the OTG lead to the bus board, in case the cable doesn't set it
grep -q '^dtoverlay=dwc2,dr_mode=host' /boot/firmware/config.txt || echo 'dtoverlay=dwc2,dr_mode=host' | sudo tee -a /boot/firmware/config.txt
echo 'Done. Reboot, then: ls /dev/ttyACM* /dev/ttyUSB* and i2cdetect -y 1 (the BNO085 is at 0x4a).'
