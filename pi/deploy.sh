#!/bin/bash
# From the PC (Git Bash): copy pi/ to the duck's Pi, without the venv, caches, logs or the simulator (but with the standing pose it reads).
#   bash pi/deploy.sh pi@duck.local            the Pi's user@address; the key ~/.ssh/duck_ed25519 (pi/README.md, Set up a new Pi)
#   bash pi/deploy.sh pi@duck.local --setup    then runs setup_pi.sh there (asks for the Pi's password, for sudo)
set -e
cd "$(dirname "$0")"
DEST=${1:?usage: bash pi/deploy.sh user@address [--setup]}
KEY=${DUCK_KEY:-$HOME/.ssh/duck_ed25519}
tar --exclude=.venv --exclude=__pycache__ --exclude='*.csv' --exclude=sim -czf - . sim/model/home.json \
  | ssh -i "$KEY" "$DEST" 'mkdir -p ~/duck && tar -xzf - -C ~/duck && echo "copied to ~/duck"'
if [ "$2" = "--setup" ]; then
  ssh -t -i "$KEY" "$DEST" 'cd ~/duck && bash setup_pi.sh 2>&1 | tee setup.log && echo "reboot to finish: sudo reboot"'
fi
