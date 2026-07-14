#!/bin/bash
echo "[START MANUAL HAND-EYE CALIBRATION]"
cd `dirname $0`
cd ..

if [ ! -f ./install/setup.bash ]; then
  echo "[ERROR] ./install/setup.bash not found - the workspace has not been built."
  echo "        On the robot, run:  ./scripts/build.sh"
  exit 1
fi

source ./install/setup.bash
#export FASTRTPS_DEFAULT_PROFILES_FILE=./configs/fastdds.xml

if ! ros2 pkg prefix vision >/dev/null 2>&1; then
  echo "[ERROR] ROS package 'vision' not found in this workspace."
  echo "        The vision package failed to build or was skipped. Notes:"
  echo "        - vision only builds ON THE ROBOT (needs CUDA/TensorRT), not on a PC."
  echo "        - Run:  ./scripts/build.sh   and scroll up for 'vision' errors,"
  echo "          or:   colcon build --packages-up-to vision"
  echo "        - If you run the calibration command manually in a new shell,"
  echo "          you must 'source ./install/setup.bash' first."
  exit 1
fi

# 时间标记: 只接受"本次运行"新生成的 /tmp/vision.yaml
MARKER=$(mktemp)

ros2 run vision calibration_node handeye ./src/vision/config/vision.yaml

# 原来这里无条件 cp /tmp/vision.yaml -> /opt/booster/vision.yaml:
# 如果校准节点已直接写入 /opt/booster, 而 /tmp/vision.yaml 是残留的旧文件/半截文件,
# 会把好配置覆盖成坏的 (缺 camera.type 等), 导致 vision_node 启动时 bad conversion 崩溃.
if [ -f /tmp/vision.yaml ] && [ /tmp/vision.yaml -nt "$MARKER" ]; then
  sudo cp /tmp/vision.yaml /opt/booster/vision.yaml && \
    echo "[OK] Calibration result copied to /opt/booster/vision.yaml"
else
  echo "[INFO] No fresh /tmp/vision.yaml from this run (calibration node may have saved /opt/booster directly)."
fi
rm -f "$MARKER"

# 完整性检查: vision_node 需要 camera.type 与 detection_model, 缺了会起不来.
if [ -f /opt/booster/vision.yaml ] && \
   grep -q "detection_model:" /opt/booster/vision.yaml && \
   grep -q "type:" /opt/booster/vision.yaml; then
  echo "[OK] /opt/booster/vision.yaml completeness check passed."
else
  echo "[ERROR] /opt/booster/vision.yaml missing or incomplete (needs camera.type + detection_model)."
  echo "        Repairing from package config (contains your latest calibration if you answered 'y' to overwrite input config)."
  if [ -f /opt/booster/vision.yaml ]; then
    sudo cp /opt/booster/vision.yaml "/opt/booster/vision.yaml.broken-$(date +%Y%m%d-%H%M%S)"
  fi
  sudo cp ./src/vision/config/vision.yaml /opt/booster/vision.yaml && \
    echo "[OK] Restored /opt/booster/vision.yaml from package config."
fi
