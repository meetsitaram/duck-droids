#!/bin/bash
# The Bluetooth speaker's sound broke up whenever a paired Xbox controller was switched off (2026-11-25, found
# after three hours: it began when a second controller was paired, so one was always off). While a paired LE device is away the kernel scans
# for it, to reconnect it, and by default for 30 ms of every 60: half of the Pi Zero 2 W's one radio, which the speaker (and the Wi-Fi) also
# need. Proven with audio_ab.sh scan: the scan off, the sound clean; on, choppy; twice. This sets the scan to 11.25 ms of every 320 (3.5 %):
# the speaker plays clean, and a controller switched on still reconnects within a second or two.
#   sudo bash bt_scan.sh             set it and restart Bluetooth (setup_pi.sh runs this)
#   sudo bash bt_scan.sh check       the same, then play the duck's sounds and show the scan timing the kernel was given (btmon)
#   sudo bash bt_scan.sh default     back to BlueZ's default
set -e
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
C=/etc/bluetooth/main.conf
INTERVAL=512              # x 0.625 ms = 320 ms
WINDOW=18                 # x 0.625 ms = 11.25 ms

setkey() {                # setkey Key value: in main.conf's [LE] section, commented or not
  if grep -qE "^#?\s*$1\s*=" $C; then sed -i -E "s/^#?\s*$1\s*=.*/$1 = $2/" $C
  else sed -i -E 's/^#\s*\[LE\]/[LE]/' $C; grep -q '^\[LE\]' $C || printf '\n[LE]\n' >> $C; sed -i "/^\[LE\]/a $1 = $2" $C; fi
}

case "${1:-install}" in
default)
  sed -i -E 's/^(ScanIntervalAutoConnect|ScanWindowAutoConnect)\s*=.*/#\1=/' $C
  systemctl restart bluetooth
  echo 'back to the default scan (30 ms of every 60)'
  ;;
install|check)
  [ "$1" = check ] && { timeout 90 btmon > /tmp/btmon_scan.txt 2>&1 & sleep 1; }
  setkey ScanIntervalAutoConnect $INTERVAL
  setkey ScanWindowAutoConnect $WINDOW
  systemctl restart bluetooth
  echo "scan for absent controllers: $WINDOW x 0.625 ms of every $INTERVAL x 0.625 ms; Bluetooth restarted"
  if [ "$1" = check ]; then
    U=${SUDO_USER:?run with sudo from the duck user}
    RUN="sudo -u $U XDG_RUNTIME_DIR=/run/user/$(id -u "$U")"
    echo 'waiting for the speaker...'
    for i in $(seq 1 45); do $RUN pactl list short sinks 2>/dev/null | grep -q bluez_output && break; sleep 2; done
    sleep 3
    for s in mmh yes no curious excited laugh angry sad; do $RUN paplay "$(getent passwd "$U" | cut -d: -f6)/duck/sounds/microduck/$s.wav" || true; sleep 0.6; done
    kill %1 2>/dev/null; wait 2>/dev/null
    echo 'what the kernel was told (the last scan parameters in the trace):'
    grep -A6 'HCI Command: LE Set Scan Paramet' /tmp/btmon_scan.txt | grep -E 'Type|Interval|Window' | tail -3
    echo "connected: $(bluetoothctl devices Connected | cut -d' ' -f3- | tr '\n' ',')"
  fi
  ;;
*) sed -n '2,10p' "$0"; exit 1 ;;
esac
