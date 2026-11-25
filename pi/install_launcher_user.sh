#!/bin/bash
# The controller launcher as a user service: starts at boot, restarts if it stops, and needs no sudo (2026-11-24).
#   bash install_launcher_user.sh                 in ~/duck: B head mode, Menu + X stand (stand_nod), from boot
#   bash install_launcher_user.sh --allow-walk    also Menu + A for the walk policy
#   systemctl --user status duck-launcher         tail -f ~/duck/launcher.log        systemctl --user disable --now duck-launcher
# "loginctl enable-linger" (allowed for your own user without sudo) starts the user's services at boot, before anyone logs in.
# install_launcher.sh does the same as a system service, with sudo; use one or the other.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
loginctl enable-linger "$USER"
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/duck-launcher.service <<EOF
[Unit]
Description=Duck controller launcher (pi/launcher.py)
After=default.target

[Service]
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python -u $DIR/launcher.py --allow-stand $*
Restart=always
RestartSec=3
StandardOutput=append:$DIR/launcher.log
StandardError=append:$DIR/launcher.log

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now duck-launcher
sleep 3
systemctl --user --no-pager status duck-launcher | head -6
echo 'On the controller: B head mode, Menu + X stand. Log: tail -f ~/duck/launcher.log'
