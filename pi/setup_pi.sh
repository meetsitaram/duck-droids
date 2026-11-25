#!/bin/bash
# On a fresh Raspberry Pi OS Lite, 64-bit (Debian 13), in the folder holding this file. Tried on the duck's Pi Zero 2 W, 2026-11-23.
#   bash setup_pi.sh            the bus board on USB (jumpers at B): the default since 2026-11-23
#   bash setup_pi.sh --uart     the bus board on the Pi's UART instead (jumpers at A): the fallback in docs/dynamixel/WIRING.md
set -e
cd "$(dirname "$0")"
sudo apt-get update
sudo apt-get install -y python3-venv i2c-tools rfkill
sudo raspi-config nonint do_i2c 0
# The BNO085 IMU stretches the I2C clock, which the Pi handles badly: at the default 100 kHz the Adafruit library got garbled packets every
# few seconds and the IMU stopped reporting (2026-11-23). 400 kHz is the usual setting for this chip on a Pi. Takes effect after a reboot.
grep -q '^dtparam=i2c_arm_baudrate=' /boot/firmware/config.txt || echo 'dtparam=i2c_arm_baudrate=400000' | sudo tee -a /boot/firmware/config.txt
sudo usermod -aG dialout,i2c,input,bluetooth "$USER"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt adafruit-blinka adafruit-circuitpython-bno08x

# Bluetooth, for an Xbox controller (Series X|S, over Bluetooth LE). Raspberry Pi OS starts with it soft-blocked.
sudo rfkill unblock bluetooth
# The settings that stop the Xbox controller's connect-drop-reconnect loop (logo flashing slowly while the Pi says Connected):
# a fixed device address for LE privacy, re-pairing allowed without a prompt, fast reconnects, and HID handled in userspace.
C=/etc/bluetooth/main.conf
for kv in 'Privacy = device' 'JustWorksRepairing = always' 'FastConnectable = true'; do
  k=${kv%% =*}
  if grep -qE "^#?\s*$k\s*=" $C; then sudo sed -i -E "s/^#?\s*$k\s*=.*/$kv/" $C; else sudo sed -i "/^\[General\]/a $kv" $C; fi
done
I=/etc/bluetooth/input.conf
if grep -qE '^#?\s*UserspaceHID\s*=' $I; then sudo sed -i -E 's/^#?\s*UserspaceHID\s*=.*/UserspaceHID=true/' $I; else echo 'UserspaceHID=true' | sudo tee -a $I; fi
echo 'options bluetooth disable_ertm=Y' | sudo tee /etc/modprobe.d/bluetooth-xbox.conf
sudo systemctl restart bluetooth

if [ "$1" = "--uart" ]; then
  # The bus board on the Pi's UART (GPIO 14 and 15, pins 8 and 10): the full UART (PL011) on those pins, and no login console on it.
  # Bluetooth moves to the mini UART (miniuart-bt), which needs a fixed core clock (core_freq=250). A gamepad sends little, but expect it
  # to be less steady there.
  sudo raspi-config nonint do_serial_cons 1
  sudo raspi-config nonint do_serial_hw 0
  sudo sed -i '/^dtoverlay=disable-bt/d' /boot/firmware/config.txt
  for line in 'enable_uart=1' 'dtoverlay=miniuart-bt' 'core_freq=250'; do
    grep -q "^$line" /boot/firmware/config.txt || echo "$line" | sudo tee -a /boot/firmware/config.txt
  done
  echo 'Done (UART). Reboot, then: .venv/bin/python -m duck.set_id --scan --port /dev/serial0 (jumpers at A).'
else
  echo 'Done (USB). Reboot, then: .venv/bin/python -m duck.set_id --scan (jumpers at B; the port is found by itself).'
fi
# The controller launcher at boot, as a user service (no sudo): B head mode, Menu + X stand. Walking stays off until the power is proven: --allow-walk
sudo -u "${SUDO_USER:-$USER}" bash install_launcher_user.sh
echo 'And i2cdetect -y 1 (the BNO085 is at 0x4a or 0x4b). For the gamepad: bluetoothctl, then scan on, pair, trust and connect.'
