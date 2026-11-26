#!/bin/sh
# A short record of the duck's network at every start, kept on the card: twice a boot (90 s and 5 min after power on) a few lines go to
# /var/log/duck-netlog.log: the Wi-Fi settings present (and any locked), the profiles, the radio, what it sees and what it joined, its
# address; and when it hasn't joined, the boot's NetworkManager and Wi-Fi driver messages and netplan's check. Not the full journal (the Pi
# keeps that in memory only): a handful of lines, for when the duck comes up off the network and only the SD card can say why (2026-11-25).
#   sudo bash netlog.sh install     once (not run by setup_pi.sh, and not yet tried on the duck): the script in /usr/local/sbin and a timer at 90 s and 5 min after boot
#   sudo sh netlog.sh               one record now
L=/var/log/duck-netlog.log
if [ "$1" = install ]; then
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  install -m 755 "$0" /usr/local/sbin/duck-netlog
  printf '%s\n' '[Unit]' 'Description=Duck: a short record of the network at start (pi/netlog.sh)' '' '[Service]' 'Type=oneshot' \
    'ExecStart=/usr/local/sbin/duck-netlog' > /etc/systemd/system/duck-netlog.service
  printf '%s\n' '[Unit]' 'Description=Duck: the network record, 90 s and 5 min after start (pi/netlog.sh)' '' '[Timer]' 'OnBootSec=90s' \
    'OnBootSec=300s' '' '[Install]' 'WantedBy=timers.target' > /etc/systemd/system/duck-netlog.timer
  systemctl daemon-reload
  systemctl enable --now duck-netlog.timer
  echo "installed: $L, written 90 s and 5 min after each start"
  exit 0
fi
{
  echo "=== $(date '+%F %T') boot $(cut -c1-8 /proc/sys/kernel/random/boot_id) up $(cut -d' ' -f1 /proc/uptime) s"
  echo "netplan files (bytes name): $(ls -la /etc/netplan 2>&1 | awk 'NR>3 {printf "%s %s, ", $5, $9}')"
  echo "locked (immutable): $(lsattr /etc/netplan/*.yaml 2>/dev/null | awk '$1 ~ /i/ {printf "%s ", $2}')"
  echo "profiles in /etc/NetworkManager: $(ls /etc/NetworkManager/system-connections 2>/dev/null | wc -l)"
  echo "radio: $(rfkill list wifi 2>/dev/null | grep -i blocked | tr -s ' \t\n' ' ')"
  echo "wlan0: $(nmcli -t -f DEVICE,STATE,CONNECTION device status 2>&1 | grep '^wlan0')"
  echo "address: $(ip -4 -o addr show wlan0 2>/dev/null | awk '{print $4}')"
  echo "sees (ssid:signal): $(nmcli -t -f SSID,SIGNAL device wifi list 2>/dev/null | head -6 | tr '\n' ' ')"
  if ! nmcli -t -f DEVICE,STATE device status 2>/dev/null | grep -q '^wlan0:connected'; then
    echo "--- NOT CONNECTED. NetworkManager this boot:"
    journalctl -b -u NetworkManager --no-pager -o short-monotonic 2>/dev/null | tail -40
    echo "--- Wi-Fi driver this boot:"
    journalctl -b -k --no-pager -o short-monotonic 2>/dev/null | grep -i -E 'brcmf|wlan0|cfg80211' | tail -15
    echo "--- netplan's check:"
    netplan generate 2>&1 | tail -5
  fi
} >> "$L" 2>&1
tail -n 2000 "$L" > "$L.tmp" && mv "$L.tmp" "$L"
