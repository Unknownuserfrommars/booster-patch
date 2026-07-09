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

ros2 run vision calibration_node handeye ./src/vision/config/vision.yaml
sudo cp /tmp/vision.yaml /opt/booster/vision.yaml && \
  echo "[OK] Calibration result copied to /opt/booster/vision.yaml" || \
  echo "[WARN] /tmp/vision.yaml not found, system calibration file not updated"
