#!/bin/bash
set -e

script_path=$(readlink -f "$0")

echo "Script path: $script_path"
# 提取父目录路径作为根路径
root_path=$(dirname $script_path)
echo "Proj root path: $root_path"

install_root=${ROBOCUP_WORKSPACE:-/home/booster/Workspace/robocup_demo}
echo "Install root: $install_root"

if [ -d "$install_root" ]; then
  backup_root="${install_root}.backup-$(date +%Y%m%d-%H%M%S)"
  echo "Existing install found; moving it to $backup_root"
  mv "$install_root" "$backup_root"
fi

mkdir -p "$install_root"

cp -r "$root_path"/* "$install_root"
bash "$install_root/utils/install_auto_start_assist.sh" #自启动
echo "Install success"
