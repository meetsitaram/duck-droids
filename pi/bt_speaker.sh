#!/bin/bash
# A Bluetooth speaker as the duck's audio output (the Pi Zero 2 W has no headphone jack). BlueZ pairs it, PipeWire (with WirePlumber and
# pipewire-pulse) plays to it over A2DP, and a user service connects it at every boot. Written 2026-11-24, not yet tried on the duck.
#   bash bt_speaker.sh install          once, in ~/duck (setup_pi.sh runs it): the packages, headless Bluetooth audio, the boot service
#   bash bt_speaker.sh scan             lists what's near for 30 s: put the speaker in pairing mode to find its name and MAC
#   bash bt_speaker.sh set "NAME|MAC"   chooses the speaker (into ~/.config/duck/bt_speaker.conf); or fill in config/bt_speaker.conf
#   bash bt_speaker.sh connect          pairs (first time), trusts, connects, makes it the default output, plays HELLO_SOUND
#   bash bt_speaker.sh forget           unpairs it, to pair it again
#   tail -f ~/duck/bt_speaker.log (the service's log)      systemctl --user status duck-bt-speaker      systemctl --user disable --now duck-bt-speaker
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
USERCONF=$HOME/.config/duck/bt_speaker.conf
SPEAKER_MAC='' SPEAKER_NAME='' SPEAKER_VOLUME='70%' HELLO_SOUND='yes' SCAN_SECONDS=40
. <(tr -d '\r' < "$DIR/config/bt_speaker.conf")     # tr: a Windows checkout may give the file CRLF ends
[ -f "$USERCONF" ] && . <(tr -d '\r' < "$USERCONF")
log() { echo "$(date '+%F %T') bt_speaker: $*"; }

setconf() {  # setconf KEY VALUE: into ~/.config/duck/bt_speaker.conf
  mkdir -p "$(dirname "$USERCONF")"
  touch "$USERCONF"
  sed -i "/^$1=/d" "$USERCONF"
  echo "$1=\"$2\"" >> "$USERCONF"
}

find_mac() {  # the speaker's MAC among the devices BlueZ knows (paired or just seen), by SPEAKER_MAC or by SPEAKER_NAME
  if [ -n "$SPEAKER_MAC" ]; then
    bluetoothctl devices | awk -v m="${SPEAKER_MAC^^}" 'toupper($2)==m {print $2; exit}'
  else
    bluetoothctl devices | awk -v n="${SPEAKER_NAME,,}" '{name=tolower(substr($0, index($0,$3)))} index(name, n) {print $2; exit}'
  fi
}

connected() { bluetoothctl info "$1" 2>/dev/null | grep -q 'Connected: yes'; }
paired() { bluetoothctl info "$1" 2>/dev/null | grep -q 'Paired: yes'; }

power_on() {
  rfkill unblock bluetooth 2>/dev/null || true
  for i in $(seq 1 20); do
    bluetoothctl show 2>/dev/null | grep -q 'Powered: yes' && return 0
    bluetoothctl power on >/dev/null 2>&1 || true
    sleep 1
  done
  log 'Bluetooth adapter would not power on (bluetoothctl show; is bluetooth.service running?)'
  return 1
}

do_connect() {
  if [ -z "$SPEAKER_MAC" ] && [ -z "$SPEAKER_NAME" ]; then
    log "no speaker chosen: fill in $DIR/config/bt_speaker.conf, or bash bt_speaker.sh set \"NAME or MAC\" (bash bt_speaker.sh scan to find it)"
    exit 2
  fi
  power_on
  M=$(find_mac)
  if [ -z "$M" ] || ! paired "$M"; then
    log "looking for ${SPEAKER_MAC:-a speaker named like \"$SPEAKER_NAME\"} for ${SCAN_SECONDS} s: it must be in pairing mode"
    bluetoothctl --timeout "$SCAN_SECONDS" scan on >/dev/null 2>&1 &
    SCAN=$!
    for i in $(seq 1 "$SCAN_SECONDS"); do
      sleep 1
      M=$(find_mac)
      [ -n "$M" ] && break
    done
    kill $SCAN 2>/dev/null || true
    [ -n "$M" ] || { log 'not found: is it on and in pairing mode? (it tries again)'; exit 1; }
    log "found $M ($(bluetoothctl info "$M" | sed -n 's/^\s*Name: //p')), pairing"
    # pairable on and an agent: without them the pairing isn't kept (Bonded: no) and the speaker drops a few seconds after connecting
    # (the INSMY Clip S, 2026-11-25: "Pairing successful", then Paired: no, Connected: no, and no PipeWire output)
    bluetoothctl pairable on >/dev/null 2>&1 || true
    timeout 30 bluetoothctl --agent NoInputNoOutput pair "$M" || true
    paired "$M" || { log "pairing $M failed: put it back in pairing mode (it tries again)"; exit 1; }
  fi
  bluetoothctl trust "$M" >/dev/null
  [ "${SPEAKER_MAC^^}" = "$M" ] || setconf SPEAKER_MAC "$M"     # next boot connects by MAC, without a scan
  for i in 1 2 3 4 5 6; do                                      # the first try can fail while WirePlumber registers the audio profiles
    connected "$M" && break
    timeout 20 bluetoothctl connect "$M" >/dev/null 2>&1 || true
    connected "$M" || sleep 5
  done
  connected "$M" || { log "$M is paired but won't connect: is it switched on and near? (it tries again)"; exit 1; }
  log "connected $M"

  # PipeWire's sink for it: bluez_output.<MAC with _>.1 (WirePlumber 0.5) or bluez_sink.<MAC>.a2dp_sink (0.4); found by the MAC part
  S=''
  for i in $(seq 1 20); do
    S=$(pactl list short sinks 2>/dev/null | awk -v m="${M//:/_}" 'index($2, m) {print $2; exit}')
    [ -n "$S" ] && break
    sleep 1
  done
  if [ -z "$S" ]; then
    log 'connected, but PipeWire shows no output for it: systemctl --user status wireplumber; pactl list short sinks'
    exit 1
  fi
  pactl set-default-sink "$S"
  [ -n "$SPEAKER_VOLUME" ] && pactl set-sink-volume "$S" "$SPEAKER_VOLUME"
  log "default output: $S"
  if [ -n "$HELLO_SOUND" ] && [ -x "$DIR/.venv/bin/python" ]; then
    (cd "$DIR" && .venv/bin/python -m duck.sound "$HELLO_SOUND") || true
  fi
}

do_scan() {
  power_on
  log 'scanning 30 s; the speaker in pairing mode shows as "Device <MAC> <name>":'
  bluetoothctl --timeout 30 scan on >/dev/null 2>&1 || true
  bluetoothctl devices
}

do_install() {
  # PipeWire with Bluetooth audio; pactl to pick the output; aplay as a fallback player
  PKGS='pipewire pipewire-pulse pipewire-alsa wireplumber libspa-0.2-bluetooth pulseaudio-utils alsa-utils bluez'
  dpkg -s $PKGS >/dev/null 2>&1 || { sudo apt-get update; sudo apt-get install -y $PKGS; }
  sudo usermod -aG bluetooth,audio "$USER"
  # Headless: no one logs in, so there is no active seat, and WirePlumber by default turns Bluetooth audio off without one.
  mkdir -p ~/.config/wireplumber/wireplumber.conf.d ~/.config/wireplumber/bluetooth.lua.d
  cat > ~/.config/wireplumber/wireplumber.conf.d/80-duck-headless-bluetooth.conf <<'EOF'
# The duck runs headless: keep Bluetooth audio on without a logged-in seat (WirePlumber 0.5). Written by bt_speaker.sh install.
wireplumber.profiles = {
  main = {
    monitor.bluez.seat-monitoring = disabled
  }
}
EOF
  cat > ~/.config/wireplumber/bluetooth.lua.d/80-duck-headless-bluetooth.lua <<'EOF'
-- The same for WirePlumber 0.4 (Debian 12). Written by bt_speaker.sh install.
bluez_monitor.properties["with-logind"] = false
EOF
  # A desktop login screen (lightdm, on Raspberry Pi OS with desktop) runs its own PipeWire and WirePlumber from boot, which take the
  # speaker's A2DP transport first; ours then sees an "unknown transport" and makes no output for it (2026-11-25, on the duck). Bluetooth
  # off in the login screen's WirePlumber, so the duck's own takes it.
  if id lightdm >/dev/null 2>&1; then
    LH=$(getent passwd lightdm | cut -d: -f6)
    sudo mkdir -p "$LH/.config/wireplumber/wireplumber.conf.d"
    printf '%s\n' '# Written by the duck'"'"'s bt_speaker.sh install: the login screen leaves Bluetooth audio to the duck'"'"'s PipeWire.' \
      'wireplumber.profiles = {' '  main = {' '    monitor.bluez = disabled' '    monitor.bluez-midi = disabled' '  }' '}' \
      | sudo tee "$LH/.config/wireplumber/wireplumber.conf.d/90-duck-no-bluetooth.conf" >/dev/null
    sudo chown -R lightdm: "$LH/.config"
    LU=$(id -u lightdm)
    sudo -u lightdm XDG_RUNTIME_DIR=/run/user/$LU systemctl --user restart wireplumber 2>/dev/null || sudo pkill -KILL -u lightdm -x wireplumber || true
  fi
  # User services start at boot, before anyone logs in (as for duck-launcher)
  loginctl enable-linger "$USER"
  systemctl --user daemon-reload
  systemctl --user enable pipewire.socket pipewire-pulse.socket wireplumber.service 2>/dev/null || true
  mkdir -p ~/.config/systemd/user
  cat > ~/.config/systemd/user/duck-bt-speaker.service <<EOF
[Unit]
Description=Duck Bluetooth speaker: pair, connect, default audio output (pi/bt_speaker.sh)
Wants=pipewire.service pipewire-pulse.service wireplumber.service
After=pipewire.service pipewire-pulse.service wireplumber.service
StartLimitIntervalSec=0

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 5
ExecStart=/bin/bash $DIR/bt_speaker.sh connect
Restart=on-failure
RestartSec=20
StandardOutput=append:$DIR/bt_speaker.log
StandardError=append:$DIR/bt_speaker.log

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable duck-bt-speaker.service
  systemctl --user restart pipewire pipewire-pulse wireplumber 2>/dev/null || true
  log 'installed: duck-bt-speaker connects the speaker at each boot (and retries every 20 s until it does)'
  if [ -z "$SPEAKER_MAC" ] && [ -z "$SPEAKER_NAME" ]; then
    log "now choose the speaker: bash $DIR/bt_speaker.sh set \"NAME or MAC\" (bash $DIR/bt_speaker.sh scan to find it)"
  fi
}

case "${1:-connect}" in
  install) do_install ;;
  scan) do_scan ;;
  set) [ -n "$2" ] || { echo 'usage: bash bt_speaker.sh set "NAME or MAC"'; exit 1; }
       if [[ "$2" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then setconf SPEAKER_MAC "${2^^}"; setconf SPEAKER_NAME ''
       else setconf SPEAKER_NAME "$2"; setconf SPEAKER_MAC ''; fi
       log "speaker set in $USERCONF; connecting in the background: tail -f $DIR/bt_speaker.log"
       systemctl --user --no-block restart duck-bt-speaker 2>/dev/null || true ;;
  connect) do_connect ;;
  forget) M=$(find_mac); [ -n "$M" ] && bluetoothctl remove "$M"
          [ -n "$SPEAKER_NAME" ] && setconf SPEAKER_MAC ''      # chosen by name: find it by name again next time
          log "forgot ${M:-nothing}: put it in pairing mode, then bash bt_speaker.sh connect" ;;
  *) sed -n '2,11p' "$0"; exit 1 ;;
esac
