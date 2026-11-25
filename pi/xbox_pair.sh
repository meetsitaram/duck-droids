#!/bin/bash
# Pair an Xbox Series X|S controller (Bluetooth LE) with the Pi's built-in Bluetooth, past its connect-drop loop (logo flashing, the Pi
# saying Connected then not, bluetoothd logging "Report Map read failed"). The fixes from xpadneo's docs/TROUBLESHOOTING.md for the
# Raspberry Pi's internal adapter: LE privacy, short LE connection intervals and a longer supervision timeout, then the same per device.
#   sudo bash xbox_pair.sh            hold the controller's pair button when asked (every Xbox controller paired before is unpaired)
#   sudo bash xbox_pair.sh --add      another controller beside the ones already paired: they stay, only the new one is paired and fixed
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
KNOWN=''
if [ "$1" = "--add" ]; then
  KNOWN=$(bluetoothctl devices Paired | awk '/Xbox/{print $2}')
  echo "keeping the paired controller(s): ${KNOWN:-none}"
  for d in $(bluetoothctl devices | awk '/Xbox/{print $2}'); do                   # one seen but never bonded: start it afresh
    echo "$KNOWN" | grep -q "$d" || bluetoothctl remove "$d" >/dev/null 2>&1 || true
  done
else
  for old in $(bluetoothctl devices | awk '/Xbox/{print $2}'); do bluetoothctl remove "$old" >/dev/null; done
fi
echo
echo '>>> Hold the pair button on the controller (top edge, by the USB-C port) until the logo flashes FAST. Scanning for 60 s...'
M=''
bluetoothctl --timeout 60 scan on > /tmp/xbox_scan.txt 2>&1 &
for i in $(seq 1 60); do
  sleep 1
  M=$(bluetoothctl devices | awk -v k="$KNOWN" '/Xbox/ && index(k, $2) == 0 {print $2; exit}')
  [ -n "$M" ] && break
done
[ -n "$M" ] || { echo 'no controller found: run again, holding the pair button'; exit 1; }
echo "found $M, pairing"
# pairable on and an agent: without them the pairing isn't kept (Paired: no, Bonded: no) and the controller, unencrypted, refuses its HID
# description ("Request attribute has encountered an unlikely error"), its logo flashing on (the second controller, 2026-11-25; the
# speaker the same that morning)
# one interactive session, its agent registered as the default before pairing: a one-shot 'bluetoothctl --agent ... pair' left none to
# answer the controller ("No agent available for request type 2", auth failed 0x05; repair.sh's way, which bonded the first controller)
kill %1 2>/dev/null || true
{ echo "pairable on"; echo "agent NoInputNoOutput"; echo "default-agent"; sleep 1
  echo "pair $M"; sleep 15; echo "trust $M"; sleep 2; echo "connect $M"; sleep 6; echo quit; } \
  | bluetoothctl 2>&1 | tr -d '\033' | grep -E "Pairing|Paired|Bonded|trust succ|Connection|Failed|Error|Request"
bluetoothctl info "$M" | grep -q "Bonded: yes" || { echo "not bonded: hold the pair button again and run this again"; exit 1; }
echo "bonded"

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
