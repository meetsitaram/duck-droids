#!/bin/bash
# Keep the duck's Wi-Fi settings from vanishing. Twice (2026-11-24 and -25) a power cut while the Pi rewrote its Wi-Fi profile left it
# missing: the Pi booted, the controller paired over Bluetooth, and it never joined the Wi-Fi; only an SD card fix on a PC brought it back
# (docs/dynamixel/TROUBLESHOOTING.md). This keeps a copy of the settings and puts it back at boot:
#   save      whenever wlan0 joins a Wi-Fi network (a NetworkManager dispatcher hook, so the settings are known good): /etc/netplan/*.yaml and
#             /etc/NetworkManager/system-connections/* copied to /etc/duck/wifi-backup/, written through to the card (sync)
#   restore   at every boot, before NetworkManager: if no Wi-Fi settings are left (no wifis in netplan, no wifi profile), the backup is put
#             back and netplan regenerates NetworkManager's profiles, so the Pi joins as usual
#   lock      the netplan files holding the Wi-Fi made immutable (chattr +i): nothing, root included, can rewrite, replace or delete them, so a
#             power cut can't catch one half-written. NetworkManager and cloud-init re-save them now and then for nothing the duck needs; their
#             writes just fail. To change the Wi-Fi on purpose: sudo bash wifi_guard.sh unlock, change it, then lock.
#   sudo bash wifi_guard.sh install    once (setup_pi.sh runs it): the boot check, the hook, a first backup, and the lock
#   sudo bash wifi_guard.sh status     what's backed up, and whether settings are present now
# pi/hotspot.sh stays the last resort, for when even this fails.
set -e
B=/etc/duck/wifi-backup
DIR=$(cd "$(dirname "$0")" && pwd)

has_wifi() {              # any Wi-Fi settings present: netplan wifis, or a NetworkManager wifi profile (our hotspot aside)
  grep -qs "wifis:" /etc/netplan/*.yaml && return 0
  grep -ls "type=wifi" /etc/NetworkManager/system-connections/*.nmconnection 2>/dev/null | grep -v duck-hotspot | grep -q . && return 0
  return 1
}

case "$1" in
install)
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  mkdir -p "$B"; chmod 700 "$B"
  install -m 755 "$DIR/wifi_guard.sh" /usr/local/sbin/duck-wifi-guard          # a copy outside ~/duck: it runs before any user session
  cat > /etc/systemd/system/duck-wifi-guard.service <<'EOF'
[Unit]
Description=Duck: put the Wi-Fi settings back if a power cut lost them (pi/wifi_guard.sh)
DefaultDependencies=no
After=local-fs.target
Before=NetworkManager.service network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/duck-wifi-guard restore

[Install]
WantedBy=multi-user.target
EOF
  cat > /etc/NetworkManager/dispatcher.d/90-duck-wifi-backup <<'EOF'
#!/bin/sh
# pi/wifi_guard.sh: wlan0 joined a network, so its settings are good: back them up (our own hotspot aside)
[ "$1" = wlan0 ] && [ "$2" = up ] && [ "$CONNECTION_ID" != duck-hotspot ] && /usr/local/sbin/duck-wifi-guard save
exit 0
EOF
  chmod 755 /etc/NetworkManager/dispatcher.d/90-duck-wifi-backup
  systemctl daemon-reload
  systemctl enable duck-wifi-guard.service
  if has_wifi; then /usr/local/sbin/duck-wifi-guard save; /usr/local/sbin/duck-wifi-guard lock; fi
  echo "installed: backed up on every Wi-Fi join, restored at boot if lost, the Wi-Fi files locked"
  ;;
save)
  has_wifi || exit 0
  mkdir -p "$B/netplan" "$B/nm"
  cp -a /etc/netplan/*.yaml "$B/netplan/" 2>/dev/null || true
  cp -a /etc/NetworkManager/system-connections/. "$B/nm/" 2>/dev/null || true
  date -Is > "$B/saved"
  sync
  ;;
restore)
  if has_wifi; then exit 0; fi
  [ -d "$B/netplan" ] || [ -d "$B/nm" ] || { echo "duck-wifi-guard: no Wi-Fi settings and no backup"; exit 0; }
  echo "duck-wifi-guard: the Wi-Fi settings were lost; restoring the backup from $(cat "$B/saved" 2>/dev/null)"
  for f in /etc/netplan/*.yaml; do chattr -i "$f" 2>/dev/null || true; done
  cp -a "$B/netplan/." /etc/netplan/ 2>/dev/null || true
  cp -a "$B/nm/." /etc/NetworkManager/system-connections/ 2>/dev/null || true
  chmod 600 /etc/netplan/*.yaml /etc/NetworkManager/system-connections/* 2>/dev/null || true
  command -v netplan >/dev/null && netplan generate || true
  for f in $(grep -ls "wifis:" /etc/netplan/*.yaml); do chattr +i "$f" 2>/dev/null || true; done
  sync
  ;;
lock)
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  for f in $(grep -ls "wifis:" /etc/netplan/*.yaml); do chattr +i "$f" && echo "locked $f"; done
  ;;
unlock)
  [ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
  for f in /etc/netplan/*.yaml; do chattr -i "$f" 2>/dev/null && echo "unlocked $f"; done
  echo "change the Wi-Fi now, then: sudo bash wifi_guard.sh lock"
  ;;
status)
  echo "Wi-Fi settings present now: $(has_wifi && echo yes || echo NO)"
  echo "backup: $(cat "$B/saved" 2>/dev/null || echo none) ($(ls "$B/netplan" "$B/nm" 2>/dev/null | grep -c . || true) files)"
  systemctl is-enabled duck-wifi-guard.service 2>/dev/null | sed 's/^/boot check: /'
  for f in /etc/netplan/*.yaml; do echo "$(lsattr "$f" 2>/dev/null | cut -c5 | sed 's/i/locked/;s/-/not locked/')  $f"; done
  ;;
*) sed -n '2,14p' "$0"; exit 1 ;;
esac
