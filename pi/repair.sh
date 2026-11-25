#!/bin/bash
# Pair the Xbox controller again from scratch, when it connects and drops in a loop: removes the old pairing, scans, pairs with an agent,
# trusts, connects. Hold the controller's pair button when it says so.
#   bash repair.sh                 the Xbox controller the Pi already knows
#   bash repair.sh AA:BB:CC:DD:EE:FF   another one, by its MAC (bluetoothctl devices lists them)
M=${1:-$(bluetoothctl devices | awk '/Xbox/ {print $2; exit}')}
[ -n "$M" ] || { echo "no Xbox controller known: give its MAC (bluetoothctl scan on, then bluetoothctl devices)"; exit 1; }
bluetoothctl remove $M >/dev/null 2>&1
echo "old pairing removed; scanning (hold the pair button now)"
{ echo "agent NoInputNoOutput"; echo "default-agent"; echo "scan on"
  for i in $(seq 1 30); do sleep 2; bluetoothctl devices | grep -q $M && break; done
  echo "pair $M"; sleep 12; echo "trust $M"; sleep 2; echo "connect $M"; sleep 6; echo "scan off"; sleep 1; echo quit; } | bluetoothctl 2>&1 | sed "s/\x1b\[[0-9;]*m//g" | grep -E "Pairing|trust succ|Connection|Failed|Error"
bluetoothctl info $M | grep -E "Paired|Bonded|Connected"
