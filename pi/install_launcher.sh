#!/bin/bash
# Install launcher.py as a service that starts at boot and restarts if it stops: the controller then starts the modes, nothing typed.
#   sudo bash install_launcher.sh             in the folder holding this file (~/duck), after setup_pi.sh
#   sudo bash install_launcher.sh --allow-stand    Menu + X on the controller also starts the stand policy (stand_nod)
#   sudo bash install_launcher.sh --allow-walk     Menu + A on the controller also starts the walk policy
#   sudo systemctl disable --now duck-launcher     to remove it from boot
set -e
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
DIR=$(cd "$(dirname "$0")" && pwd)
U=${SUDO_USER:-$(stat -c %U "$DIR")}
cat > /etc/systemd/system/duck-launcher.service <<EOF
[Unit]
Description=Duck controller launcher (pi/launcher.py)
After=bluetooth.target network.target

[Service]
User=$U
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python -u $DIR/launcher.py $*
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now duck-launcher
sleep 2
systemctl --no-pager status duck-launcher | head -5
echo 'B on the controller: head mode on and off. Logs: journalctl -u duck-launcher -f'
