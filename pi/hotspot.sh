#!/bin/bash
# The duck's own Wi-Fi hotspot, as a backup for when it can't join the home network (2026-11-25: it booted, the controller paired over
# Bluetooth, and it never came onto the Wi-Fi). At boot it waits WAIT s for the home Wi-Fi; if it hasn't joined, it starts an access point,
# and the PC joins that and reaches the duck at 10.42.0.1 (ssh, deploy.sh, twin.py --remote 10.42.0.1). While it's on its hotspot with
# nobody connected, every 5 min it tries the home Wi-Fi again and stays there if it joins.
#   sudo bash hotspot.sh install     once: the hotspot profile (NetworkManager), its password, and the boot check (setup_pi.sh runs it)
#   bash hotspot.sh status           which network it's on
#   sudo bash hotspot.sh on | off    by hand
# The name and password are in ~/.config/duck/hotspot.conf on the Pi (made at install, a random password; never in the repo): copy them into
# the PC's git-ignored .env (DUCK_HOTSPOT_SSID, DUCK_HOTSPOT_PASS) to have them at hand.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
U=${SUDO_USER:-$USER}
H=$(getent passwd "$U" | cut -d: -f6)
CONF=$H/.config/duck/hotspot.conf
CON=duck-hotspot
WAIT=${WAIT:-60}

home_connected() {        # on a Wi-Fi network that isn't our own hotspot
  nmcli -t -f TYPE,NAME,DEVICE connection show --active | grep -q "^802-11-wireless:.*:wlan0$" && \
    ! nmcli -t -f NAME connection show --active | grep -qx "$CON"
}
hotspot_up() { nmcli -t -f NAME connection show --active | grep -qx "$CON"; }

case "$1" in
install)
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  mkdir -p "$(dirname "$CONF")"
  if [ ! -f "$CONF" ]; then
    printf 'SSID="duck-%s"\nPASS="%s"\n' "$(tr -dc a-z0-9 </dev/urandom | head -c 4)" "$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16)" > "$CONF"
    chown -R "$U": "$(dirname "$CONF")"; chmod 600 "$CONF"
  fi
  . "$CONF"
  nmcli connection delete "$CON" >/dev/null 2>&1 || true
  nmcli connection add type wifi ifname wlan0 con-name "$CON" autoconnect no ssid "$SSID" \
    802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS" >/dev/null
  cat > /etc/systemd/system/duck-hotspot.service <<EOF
[Unit]
Description=Duck: its own Wi-Fi hotspot when the home Wi-Fi isn't there (pi/hotspot.sh)
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/bin/bash $DIR/hotspot.sh check
EOF
  cat > /etc/systemd/system/duck-hotspot.timer <<EOF
[Unit]
Description=Duck: check the Wi-Fi at boot and every 5 min (pi/hotspot.sh)

[Timer]
OnBootSec=${WAIT}s
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable --now duck-hotspot.timer
  echo "installed: hotspot \"$SSID\" (password in $CONF), checked ${WAIT} s after boot and every 5 min"
  ;;
check)                    # the timer: no home Wi-Fi -> hotspot; on the hotspot with nobody on it -> try the home Wi-Fi
  if home_connected; then exit 0; fi
  if hotspot_up; then
    [ -n "$(iw dev wlan0 station dump 2>/dev/null)" ] && exit 0      # someone is connected to the duck: leave it
    nmcli connection down "$CON" >/dev/null 2>&1 || true
    sleep 25                                                          # NetworkManager autoconnects the home Wi-Fi if it's there
    home_connected && { echo "back on the home Wi-Fi"; exit 0; }
  fi
  nmcli connection up "$CON" >/dev/null && echo "no home Wi-Fi: hotspot up (10.42.0.1)"
  ;;
on)  nmcli connection up "$CON" ;;
off) nmcli connection down "$CON" ;;
status)
  if hotspot_up; then echo "on its own hotspot ($(. "$CONF" 2>/dev/null; echo "$SSID")), 10.42.0.1"
  elif home_connected; then echo "on the home Wi-Fi: $(nmcli -t -f NAME,DEVICE connection show --active | grep ':wlan0$' | cut -d: -f1)"
  else echo "no Wi-Fi"; fi
  ;;
*) sed -n '2,12p' "$0"; exit 1 ;;
esac
