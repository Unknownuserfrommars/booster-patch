#!/bin/bash
set -e

install_root=${ROBOCUP_WORKSPACE:-/home/booster/Workspace/robocup_demo}

systemctl --user stop robocup_game_assist.service || true
systemctl --user disable robocup_game_assist.service || true
if [ -x "$install_root/scripts/stop.sh" ]; then
  "$install_root/scripts/stop.sh" || true
fi
rm -rf "$install_root"
systemctl --user daemon-reload
rm -f /home/booster/.config/systemd/user/robocup_game_assist.service
