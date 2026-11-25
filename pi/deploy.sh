#!/bin/bash
# From the PC (Git Bash): copy pi/ to the duck's Pi, without the venv, caches, logs or the simulator (but with the standing pose it reads).
#   bash pi/deploy.sh                  to the Pi in the repo root's .env (DUCK_USER, DUCK_HOST, DUCK_KEY; git-ignored, template .env.example)
#   bash pi/deploy.sh --setup          then runs setup_pi.sh there (asks for the Pi's password, for sudo)
#   bash pi/deploy.sh pi@duck.local    another Pi, by user@address
set -e
cd "$(dirname "$0")"
[ -f ../.env ] && set -a && . ../.env && set +a
if [ -n "$1" ] && [ "$1" != "--setup" ]; then DEST=$1; shift; else DEST=${DUCK_USER:?no Pi: copy .env.example to .env, or bash pi/deploy.sh user@address}@${DUCK_HOST:?set DUCK_HOST in .env}; fi
KEY=${DUCK_KEY:-$HOME/.ssh/duck_ed25519}
KEY=${KEY/#\~/$HOME}
tar --exclude=.venv --exclude=__pycache__ --exclude='*.csv' --exclude=sim -czf - . sim/model/home.json \
  | ssh -i "$KEY" "$DEST" 'mkdir -p ~/duck && tar -xzf - -C ~/duck && echo "copied to ~/duck"'
if [ "$1" = "--setup" ]; then
  ssh -t -i "$KEY" "$DEST" 'cd ~/duck && bash setup_pi.sh 2>&1 | tee setup.log && echo "reboot to finish: sudo reboot"'
fi
