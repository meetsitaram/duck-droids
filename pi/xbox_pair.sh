#!/bin/bash
# Pair an Xbox Series X|S controller (Bluetooth LE) with the Pi's built-in Bluetooth, past its connect-drop loop (logo flashing, the Pi
# saying Connected then not, bluetoothd logging "Report Map read failed"). The fixes from xpadneo's docs/TROUBLESHOOTING.md for the
# Raspberry Pi's internal adapter: LE privacy, short LE connection intervals and a longer supervision timeout, then the same per device.
#   sudo bash xbox_pair.sh            hold the controller's pair button when asked
# Pairing again (or holding the pair button for another device) drops the per-device part: run this again.
set -e
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
C=/etc/bluetooth/main.conf

setkey() {  # setkey SECTION 'Key = value': set or add a key, the section's header uncommented first
  local sec=$1 kv=$2 k
  k=$(echo "${kv%%=*}" | xargs)
  sed -i -E "s/^#\s*\[$sec\]/[$sec]/" $C
  grep -q "^\[$sec\]" $C || printf '\n[%s]\n' "$sec" >> $C
  if grep -qE "^#?\s*$k\s*=" $C; then sed -i -E "s/^#?\s*$k\s*=.*/$kv/" $C; else sed -i "/^\[$sec\]/a $kv" $C; fi
}
setkey General 'Privacy = device'
setkey General 'JustWorksRepairing = always'
setkey General 'FastConnectable = true'
setkey LE 'MinConnectionInterval = 7'
setkey LE 'MaxConnectionInterval = 9'
setkey LE 'ConnectionLatency = 0'
setkey LE 'ConnectionSupervisionTimeout = 200'
rfkill unblock bluetooth
systemctl restart bluetooth
sleep 3
bluetoothctl power on >/dev/null

ADAPTER=$(bluetoothctl show | awk '/^Controller/{print $2; exit}')
for old in $(bluetoothctl devices | awk '/Xbox/{print $2}'); do bluetoothctl remove "$old" >/dev/null; done
echo
echo '>>> Hold the pair button on the controller (top edge, by the USB-C port) until the logo flashes FAST. Scanning for 60 s...'
M=''
bluetoothctl --timeout 60 scan on > /tmp/xbox_scan.txt 2>&1 &
for i in $(seq 1 60); do
  sleep 1
  M=$(bluetoothctl devices | awk '/Xbox/{print $2; exit}')
  [ -n "$M" ] && break
done
[ -n "$M" ] || { echo 'no controller found: run again, holding the pair button'; exit 1; }
echo "found $M, pairing"
bluetoothctl pair "$M" || true
bluetoothctl trust "$M"
bluetoothctl connect "$M" || true
kill %1 2>/dev/null || true

INFO=/var/lib/bluetooth/$ADAPTER/$M/info
if [ -f "$INFO" ]; then
  systemctl stop bluetooth
  sed -i '/^\[ConnectionParameters\]/,/^$/d' "$INFO"
  printf '\n[ConnectionParameters]\nMinInterval=6\nMaxInterval=6\nLatency=0\nTimeout=300\n' >> "$INFO"
  systemctl start bluetooth
  sleep 3
  bluetoothctl power on >/dev/null
  echo 'per-device connection parameters written'
else
  echo "no pairing record at $INFO: pairing failed, run again"
  exit 1
fi
echo
echo '>>> Now press the Xbox button once. The logo should go steady within a few seconds.'
for i in $(seq 1 30); do
  sleep 1
  bluetoothctl info "$M" | grep -q 'Connected: yes' && { echo "connected: $M"; exit 0; }
done
echo 'not connected yet: press the Xbox button again, or tell Claude'
