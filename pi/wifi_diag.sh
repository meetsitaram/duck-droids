#!/bin/bash
# What the Wi-Fi is doing while the Bluetooth speaker plays (2026-11-25: choppy with the Wi-Fi on, clean with it off), and how its settings
# differ from the backup wifi_guard.sh took. Secrets (psk, password) are masked. Output in /tmp/wifi_diag.txt as well.
#   sudo bash wifi_diag.sh
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
U=${SUDO_USER:?run with sudo from the duck user}
RUN="sudo -u $U XDG_RUNTIME_DIR=/run/user/$(id -u "$U")"
S=$(getent passwd "$U" | cut -d: -f6)/duck/sounds/microduck
mask() { sed -E 's/((psk|password|wep-key[0-9]?|secret)[^:=]*[:=][[:space:]]*).*/\1********/I'; }
command -v iw >/dev/null || apt-get install -y iw >/dev/null
{
echo "== Wi-Fi settings now vs the backup (wifi_guard.sh, before the hotspot)"
ls -la --time-style=+%m-%d_%H:%M /etc/netplan/ /etc/duck/wifi-backup/netplan/ 2>&1
for f in /etc/netplan/*.yaml; do
  b=/etc/duck/wifi-backup/netplan/$(basename "$f")
  if [ -f "$b" ]; then echo "-- diff $b (then) -> $f (now)"; diff <(mask < "$b") <(mask < "$f") && echo "   identical"
  else echo "-- $f: no backup of it"; fi
done
for b in /etc/duck/wifi-backup/netplan/*.yaml; do [ -f "/etc/netplan/$(basename "$b")" ] || { echo "-- only in the backup: $b"; mask < "$b"; }; done
echo; echo "== the active Wi-Fi profile (no secrets)"
nmcli -f 802-11-wireless,connection,ipv4.method,ipv6.method,ipv6.addr-gen-mode connection show "$(nmcli -t -f NAME,DEVICE connection show --active | awk -F: '$2=="wlan0"{print $1}')" | grep -vE '^\s*$|--$' | mask
echo; echo "== NetworkManager and wpa_supplicant config"
ls -la /etc/NetworkManager/conf.d/ /etc/NetworkManager/system-connections/ 2>&1; cat /etc/NetworkManager/conf.d/*.conf 2>/dev/null | mask
ls -la /etc/wpa_supplicant/ 2>&1
echo; echo "== link"; iw dev wlan0 link; iw dev wlan0 get power_save; iw dev; iw reg get | head -4
echo; echo "== channel busy (survey, in use)"; iw dev wlan0 survey dump | grep -A6 "in use"
echo; echo "== station counters before"; iw dev wlan0 station dump | grep -E "tx retries|tx failed|beacon loss|rx drop|signal:|tx bitrate|rx bitrate|connected time"
echo; echo "== Wi-Fi events while 6 sounds play (scans, roams)"
timeout 30 iw event -t > /tmp/iw_events.txt 2>&1 &
for s in mmh yes no curious excited laugh; do $RUN paplay "$S/$s.wav" || true; sleep 0.6; done
sleep 1; kill %1 2>/dev/null; wait 2>/dev/null
echo "events: $(wc -l < /tmp/iw_events.txt)"; cut -c1-120 /tmp/iw_events.txt | head -20
echo; echo "== station counters after"; iw dev wlan0 station dump | grep -E "tx retries|tx failed|beacon loss|rx drop"
echo; echo "== scans and drops in the last hour"
journalctl --since "-60min" --no-pager -u wpa_supplicant | grep -cE "SCAN-STARTED|CTRL-EVENT-SCAN"; journalctl --since "-60min" --no-pager -u wpa_supplicant | grep -E "DISCONNECTED|bgscan" | tail -5
echo; echo "== nearby networks on channels 8-12 (2.4 GHz neighbours)"; nmcli -t -f CHAN,SIGNAL dev wifi list --rescan no | awk -F: '$1>=8 && $1<=12' | sort | uniq -c
} 2>&1 | tee /tmp/wifi_diag.txt
chmod 644 /tmp/wifi_diag.txt
