#!/bin/bash

cd "$(dirname "$0")"
cd ..

CONFIG_PATH="${VISION_CONFIG:-src/vision/config/vision.yaml}"
AUTO_SCRIPT="src/vision/scripts/auto_handeye_calib.py"

usage() {
  cat <<EOF
Usage:
  ./scripts/auto_calib.sh semi [extra args...]
  ./scripts/auto_calib.sh discover
  ./scripts/auto_calib.sh auto <kRotateHead_api_id> [extra args...]

Defaults:
  ./scripts/auto_calib.sh        Same as semi-auto mode.

Environment:
  VISION_CONFIG=/path/to/vision.yaml   Override config path.

Examples:
  ./scripts/auto_calib.sh semi
  ./scripts/auto_calib.sh discover
  ./scripts/auto_calib.sh auto 2004 --save-system-config
EOF
}

source_if_exists() {
  if [ -f "$1" ]; then
    # shellcheck disable=SC1090
    source "$1"
  fi
}

source_if_exists /opt/ros/humble/setup.bash
source_if_exists /opt/booster/BoosterRos2/install/setup.bash
source_if_exists /opt/booster/BoosterRos2Interface/install/setup.bash
source_if_exists ./install/setup.bash

if [ ! -f "$AUTO_SCRIPT" ]; then
  echo "[ERROR] Cannot find $AUTO_SCRIPT"
  echo "Run this script from the patch root, or rebuild/install the vision package."
  exit 1
fi

CMD="${1:-semi}"
shift || true

case "$CMD" in
  -h|--help|help)
    usage
    exit 0
    ;;

  discover)
    echo "[AUTO CALIB] Discovering kRotateHead API id."
    echo "[AUTO CALIB] Move the head once with the gamepad when prompted."
    python3 "$AUTO_SCRIPT" --discover "$@"
    ;;

  auto)
    API_ID="${1:-}"
    if [ -z "$API_ID" ]; then
      echo "[ERROR] Full-auto mode needs the kRotateHead API id."
      echo "First run: ./scripts/auto_calib.sh discover"
      exit 1
    fi
    shift
    echo "[AUTO CALIB] Full-auto mode, api-id=$API_ID"
    python3 "$AUTO_SCRIPT" --config "$CONFIG_PATH" --mode auto --api-id "$API_ID" "$@"
    ;;

  semi)
    echo "[AUTO CALIB] Semi-auto mode."
    echo "[AUTO CALIB] Move the head with the gamepad; captures happen automatically."
    python3 "$AUTO_SCRIPT" --config "$CONFIG_PATH" --mode semi "$@"
    ;;

  *)
    echo "[ERROR] Unknown mode: $CMD"
    usage
    exit 1
    ;;
esac
