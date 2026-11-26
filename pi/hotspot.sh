#!/bin/bash
# OPT-IN, not installed by setup_pi.sh: started at every boot (2026-11-25) it took the Pi Zero 2 W's one radio from the home Wi-Fi, the Xbox
# controller and the Bluetooth speaker; the audio broke up and the Pi went missing from the network. sudo bash hotspot.sh remove takes it off.
# The duck's own Wi-Fi hotspot, a way in when it can't join the home network (2026-11-25: it booted, the controller paired over Bluetooth,
# and it never came onto the Wi-Fi). Join it from a phone or the PC and reach the duck at 10.42.0.1 (ssh, deploy.sh, twin.py --remote).
#   at every start   the hotspot is on for BOOT_WINDOW s (5 min); nobody joins: it goes off (saving power) and the Pi joins the home Wi-Fi.
#                    Someone joins: it stays on while anyone is connected, and goes off IDLE s after the last one leaves. One radio: while
#                    the hotspot is on, the Pi isn't on the home Wi-Fi.
#   afterwards       every 5 min, if the Pi isn't on the home Wi-Fi, the hotspot comes back (with the same rule for going off).
#   sudo bash hotspot.sh install     once (setup_pi.sh runs it), and again to apply a change: the profile, its password, the services
#   bash hotspot.sh status           which network it's on
#   sudo bash hotspot.sh on | off    by hand
# Its name is duck-droid-<the Pi's hostname> (HOTSPOT_SSID=... at install for another); its password is random, made at the first install.
# Both are kept in ~/.config/duck/hotspot.conf on the Pi, never in the repo: copy them into the PC's git-ignored .env (DUCK_HOTSPOT_SSID,
# DUCK_HOTSPOT_PASS) to have them at hand.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
U=${SUDO_USER:-$USER}
H=$(getent passwd "$U" | cut -d: -f6)
CONF=$H/.config/duck/hotspot.conf
CON=duck-hotspot
BOOT_WINDOW=${BOOT_WINDOW:-300}          # s the hotspot is on at every start
IDLE=${IDLE:-300}                        # s with nobody connected before it goes off

home_connected() {        # on a Wi-Fi network that isn't our own hotspot
  nmcli -t -f TYPE,NAME,DEVICE connection show --active | grep -q "^802-11-wireless:.*:wlan0$" && \
    ! nmcli -t -f NAME connection show --active | grep -qx "$CON"
}
hotspot_up() { nmcli -t -f NAME connection show --active | grep -qx "$CON"; }
clients() { iw dev wlan0 station dump 2>/dev/null | grep -c "^Station" || true; }
hold() {                  # keep the hotspot up while anyone is connected; off after $1 s with nobody, then NetworkManager joins the home Wi-Fi
  local quiet=0
  while hotspot_up; do
    if [ "$(clients)" -gt 0 ]; then quiet=0; else quiet=$((quiet + 15)); fi
    [ "$quiet" -ge "$1" ] && break
    sleep 15
  done
  nmcli connection down "$CON" >/dev/null 2>&1 || true
  echo "hotspot off (nobody connected for $1 s): back to the home Wi-Fi"
}

unit() {                  # unit NAME CONTENT: write a systemd unit
  printf '%s\n' "$2" > "/etc/systemd/system/$1"
}

case "$1" in
install)
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  mkdir -p "$(dirname "$CONF")"
  PASS=''
  [ -f "$CONF" ] && . "$CONF"
  SSID=${HOTSPOT_SSID:-duck-droid-$(hostname)}
  [ -n "$PASS" ] || PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16)
  printf 'SSID="%s"\nPASS="%s"\n' "$SSID" "$PASS" > "$CONF"
  chown -R "$U": "$(dirname "$CONF")"; chmod 600 "$CONF"
  nmcli connection delete "$CON" >/dev/null 2>&1 || true
  nmcli connection add type wifi ifname wlan0 con-name "$CON" autoconnect no ssid "$SSID" \
    802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS" >/dev/null
  unit duck-hotspot-boot.service "[Unit]
Description=Duck: its own Wi-Fi hotspot for the first minutes after every start (pi/hotspot.sh)
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
ExecStart=/bin/bash $DIR/hotspot.sh boot

[Install]
WantedBy=multi-user.target"
  unit duck-hotspot.service "[Unit]
Description=Duck: the hotspot again when the home Wi-Fi is missing (pi/hotspot.sh)
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/bin/bash $DIR/hotspot.sh check"
  unit duck-hotspot.timer "[Unit]
Description=Duck: check the Wi-Fi every 5 min after the start window (pi/hotspot.sh)

[Timer]
OnBootSec=$((BOOT_WINDOW + 120))s
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target"
  systemctl daemon-reload
  systemctl enable duck-hotspot-boot.service
  systemctl enable --now duck-hotspot.timer
  echo "installed: hotspot \"$SSID\" (password in $CONF): on for $BOOT_WINDOW s at every start, then only when the home Wi-Fi is missing"
  ;;
boot)                     # every start: the hotspot for BOOT_WINDOW s, longer while anyone is on it
  sleep 5
  nmcli connection up "$CON" >/dev/null && echo "start: hotspot up for $BOOT_WINDOW s (10.42.0.1)"
  hold "$BOOT_WINDOW"
  ;;
check)                    # the timer: no home Wi-Fi -> the hotspot again, held as at the start
  if home_connected || hotspot_up; then exit 0; fi
  sleep 25                                                            # NetworkManager may still be joining the home Wi-Fi
  home_connected && exit 0
  nmcli connection up "$CON" >/dev/null && echo "no home Wi-Fi: hotspot up (10.42.0.1)"
  hold "$IDLE"
  ;;
remove)                   # off and gone: the services, the timer, the profile (the password file stays, for a later install)
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  systemctl disable --now duck-hotspot-boot.service duck-hotspot.timer 2>/dev/null || true
  rm -f /etc/systemd/system/duck-hotspot-boot.service /etc/systemd/system/duck-hotspot.service /etc/systemd/system/duck-hotspot.timer
  systemctl daemon-reload
  nmcli connection down "$CON" >/dev/null 2>&1 || true
  nmcli connection delete "$CON" >/dev/null 2>&1 || true
  echo "hotspot removed"
  ;;
on)  nmcli connection up "$CON" ;;
off) nmcli connection down "$CON" ;;
status)
  if hotspot_up; then echo "on its own hotspot ($(. "$CONF" 2>/dev/null; echo "$SSID")), 10.42.0.1, $(clients) connected"
  elif home_connected; then echo "on the home Wi-Fi: $(nmcli -t -f NAME,DEVICE connection show --active | grep ':wlan0$' | cut -d: -f1)"
  else echo "no Wi-Fi"; fi
  ;;
*) sed -n '2,15p' "$0"; exit 1 ;;
esac
