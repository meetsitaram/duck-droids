#!/bin/bash
# Which part of the Pi breaks up the Bluetooth speaker's sound (2026-11-25: choppy on two speakers, clean from a phone): the same
# sounds in three phases, each announced here, then everything put back. Listen and note which phase is clean.
#   sudo bash audio_ab.sh
#   1. as it is now
#   2. the Wi-Fi radio off (the one chip carries Wi-Fi and Bluetooth); back on afterwards
#   3. /etc/bluetooth/main.conf with the duck's changes commented out (FastConnectable, Privacy, the LE connection settings from
#      xbox_pair.sh), Bluetooth restarted; the file put back and Bluetooth restarted afterwards
set -e
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
U=${SUDO_USER:?run with sudo from the duck user}
# phase 2 cuts the Wi-Fi, and with it an ssh session over it: run detached, logging to a file this session follows until then
# (not for 'phone', run over the USB link, as it asks for the hotspot's password here)
if [ -z "$AB_DETACHED" ] && [ "$1" != phone ] && [ "$1" != scan ]; then
  AB_DETACHED=1 setsid nohup bash "$0" "$@" > /tmp/audio_ab.log 2>&1 < /dev/null &
  sleep 1; exec tail -f /tmp/audio_ab.log
fi
RUN="sudo -u $U XDG_RUNTIME_DIR=/run/user/$(id -u "$U")"
S=$(getent passwd "$U" | cut -d: -f6)/duck/sounds/microduck
C=/etc/bluetooth/main.conf

play() {
  echo; echo "=== PHASE $1: $2 ==="; sleep 2
  for s in mmh yes no curious excited laugh; do $RUN paplay "$S/$s.wav" || true; sleep 0.6; done
  echo "=== end of phase $1 ==="; sleep 4
}
speaker() {               # wait for the speaker's output to be back (the duck's bt_speaker service reconnects it)
  for i in $(seq 1 45); do $RUN pactl list short sinks 2>/dev/null | grep -q bluez_output && return 0; sleep 2; done
  echo 'speaker not back after 90 s'; return 1
}
restore() {
  nmcli radio wifi on || true
  [ -f $C.audio-ab ] && { mv -f $C.audio-ab $C; systemctl restart bluetooth; echo 'main.conf put back, Bluetooth restarted'; }
}
trap restore EXIT

speaker
if [ "$1" = wifi ]; then  # sudo bash audio_ab.sh wifi: six rounds, the Wi-Fi on, off, on, off, on, off, to be sure it is the Wi-Fi
  for r in 1 2 3 4 5 6; do
    if [ $((r % 2)) = 1 ]; then nmcli radio wifi on; play $r 'Wi-Fi ON'; else nmcli radio wifi off; play $r 'Wi-Fi OFF'; fi
  done
  nmcli radio wifi on; echo 'done: Wi-Fi back on. Were the OFF rounds (2, 4, 6) clean and the ON rounds (1, 3, 5) choppy?'
  exit 0
fi
if [ "$1" = phone ]; then # sudo bash audio_ab.sh phone, over the USB link: the sounds on a phone's 2.4 GHz hotspot, then the home Wi-Fi again
  HOME_CON=$(nmcli -t -f NAME,DEVICE connection show --active | awk -F: '$2=="wlan0"{print $1}')
  echo "home Wi-Fi profile: $HOME_CON; scanning for a phone hotspot (keep its settings screen open)..."
  P=''
  for i in 1 2 3 4 5 6; do
    nmcli device wifi rescan >/dev/null 2>&1 || true; sleep 5
    P=$(nmcli -t -f SSID dev wifi list --rescan no | grep -i -m1 'iphone\|android\|hotspot' || true)
    [ -n "$P" ] && break
  done
  [ -n "$P" ] || { echo 'no phone hotspot seen'; exit 1; }
  echo "found: $P"
  nmcli --ask device wifi connect "$P" ifname wlan0 name duck-phone-test
  nmcli -t -f GENERAL.CONNECTION dev show wlan0
  play 1 "on the PHONE's hotspot ($P)"
  nmcli connection up "$HOME_CON" >/dev/null && echo "back on the home Wi-Fi ($HOME_CON)"
  nmcli connection delete duck-phone-test >/dev/null 2>&1 || true
  play 2 'on the HOME Wi-Fi again'
  echo 'done: was round 1 (phone hotspot) clean, and round 2 (home Wi-Fi) choppy?'
  exit 0
fi
if [ "$1" = scan ]; then  # sudo bash audio_ab.sh scan (controllers switched off): four rounds, Bluetooth's background scan for the paired
  # controllers on, off, on, off. While a paired LE controller is away, the kernel scans for it all the time (to reconnect it), on the
  # radio the speaker needs; with one controller, connected, there was nothing to scan for. btmon's trace of each round in /tmp/btmon_N.txt
  LIST=''
  for d in $(bluetoothctl devices Paired | awk '/Xbox/{print $2}'); do
    t=1; bluetoothctl info "$d" | head -1 | grep -q random && t=2
    LIST="$LIST $d,$t"
  done
  echo "paired controllers (address,type):$LIST"
  echo "speaker link: $(timeout 5 btmgmt conn-info -t 0 "$(bluetoothctl devices Connected | awk '!/Xbox/{print $2; exit}')" 2>&1 | tr '\n' ' ')"
  for r in 1 2 3 4; do
    timeout 60 btmon > /tmp/btmon_$r.txt 2>&1 &
    sleep 1
    if [ $r = 1 ]; then L='background scan AS NOW'
    elif [ $((r % 2)) = 0 ]; then L='background scan OFF'
      for x in $LIST; do timeout 5 btmgmt del-device -t "${x#*,}" "${x%,*}" 2>&1 | tail -1; done
    else L='background scan ON again'
      for x in $LIST; do timeout 5 btmgmt add-device -a 2 -t "${x#*,}" "${x%,*}" 2>&1 | tail -1; done
    fi
    play $r "$L"
    kill %1 2>/dev/null; wait 2>/dev/null
    echo "   round $r trace: $(grep -c 'LE Advertising Report' /tmp/btmon_$r.txt) advertising reports heard; scan commands: $(grep -A3 'LE Set Scan Enable' /tmp/btmon_$r.txt | grep -E 'Scanning:' | tr -s ' ' | tr '\n' ';')"
    grep -A6 'HCI Command: LE Set Scan Paramet' /tmp/btmon_$r.txt | grep -E 'Interval|Window|Type' | head -3
  done
  for x in $LIST; do timeout 5 btmgmt add-device -a 2 -t "${x#*,}" "${x%,*}" >/dev/null 2>&1; done
  chmod 644 /tmp/btmon_*.txt
  echo 'done (the scan is back as it was). Were the scan OFF rounds (2, 4) clean?'
  exit 0
fi
if [ "$1" = bt ]; then    # sudo bash audio_ab.sh bt: four rounds, the Wi-Fi on, main.conf as it is, at the defaults, as it is, at the defaults
  cp $C $C.audio-ab
  for r in 1 2 3 4; do
    if [ $((r % 2)) = 1 ]; then cp $C.audio-ab $C; L='Bluetooth settings AS NOW'
    else sed -E 's/^(FastConnectable|Privacy|JustWorksRepairing|MinConnectionInterval|MaxConnectionInterval|ConnectionLatency|ConnectionSupervisionTimeout)\s*=/#&/' $C.audio-ab > $C; L='Bluetooth settings at the DEFAULTS'; fi
    systemctl restart bluetooth; echo "($L: Bluetooth restarted, waiting for the speaker)"
    speaker && sleep 3
    play $r "$L"
  done
  echo 'done (main.conf put back on exit). Were the DEFAULTS rounds (2, 4) clean?'
  exit 0
fi
if [ "$1" = ps ]; then    # sudo bash audio_ab.sh ps: four rounds, the Wi-Fi connected, its power saving on, off, on, off (iw, live)
  command -v iw >/dev/null || apt-get install -y iw >/dev/null
  for r in 1 2 3 4; do
    if [ $((r % 2)) = 1 ]; then iw dev wlan0 set power_save on; play $r "Wi-Fi power saving ON ($(iw dev wlan0 get power_save))"
    else iw dev wlan0 set power_save off; play $r "Wi-Fi power saving OFF ($(iw dev wlan0 get power_save))"; fi
  done
  iw dev wlan0 set power_save off; echo 'done: power saving back off (as net_setup.sh set it). Which rounds were clean?'
  exit 0
fi
play 1 'as it is now'

nmcli radio wifi off
play 2 'Wi-Fi radio OFF'
nmcli radio wifi on
echo 'Wi-Fi back on'

cp $C $C.audio-ab
sed -i -E 's/^(FastConnectable|Privacy|JustWorksRepairing|MinConnectionInterval|MaxConnectionInterval|ConnectionLatency|ConnectionSupervisionTimeout)\s*=/#&/' $C
systemctl restart bluetooth
echo 'Bluetooth restarted with the default settings, waiting for the speaker...'
speaker && sleep 3
play 3 'Bluetooth settings at the defaults'
echo; echo 'done: which phase was clean, 1, 2, 3 or none?'
