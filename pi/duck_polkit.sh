#!/bin/bash
# The launcher's controller combos that need the system, allowed for the duck's user without a password, and only these (2026-11-25):
#   RT + LT + RB + LB   shut down (systemctl poweroff): unplugging instead risks the card, as power cuts mid-write lost the Wi-Fi settings twice
#   LT + d-pad up / down   the Wi-Fi radio on / off (nmcli radio wifi): the Wi-Fi breaks up the Bluetooth speaker's sound
#   sudo bash duck_polkit.sh          (setup_pi.sh runs it)
set -e
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
U=${SUDO_USER:?run with sudo from the duck user}
cat > /etc/polkit-1/rules.d/50-duck.rules <<RULES
// pi/duck_polkit.sh: the duck launcher's shutdown and Wi-Fi combos
polkit.addRule(function(action, subject) {
  if (subject.user != "$U") return polkit.Result.NOT_HANDLED;
  if (/^org\.freedesktop\.login1\.(power-off|reboot)(-multiple-sessions|-ignore-inhibit)?$/.test(action.id)) return polkit.Result.YES;
  if (action.id == "org.freedesktop.NetworkManager.enable-disable-wifi") return polkit.Result.YES;
  return polkit.Result.NOT_HANDLED;
});
RULES
rm -f /etc/polkit-1/rules.d/50-duck-poweroff.rules
systemctl restart polkit 2>/dev/null || true
echo "polkit rule written for $U: shutdown and the Wi-Fi on/off without a password"
