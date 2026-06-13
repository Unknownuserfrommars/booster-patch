# v2.1 — Experimental Auto Calibration 🦀

> Merge base: Booster K1 v1.6 SDK (competition demo `K1_5v5_Demo_v1.6`)

---

## 🐛 Bug Fixes

### Camera Topic Mismatch (Critical)

`vision_node.cpp` 使用了错误的相机 topic 名称，导致 vision 节点无法接收任何图像帧。

- **Root cause**: v2.0 merge 引入了另一个 SDK 分支的 `vision_node.cpp`，使用硬件原始 topic（例如 `/camera/camera/color/image_raw`）
- **Robot reality**: Booster 系统将所有相机统一重映射到 `/boostercamera/head/rgb`
- **Fix**: 恢复为 v1.6 原始的统一 topic 方案
- **Also fixed**: v2.0 同步修复

| Camera Type | Before (broken) | After (fixed) |
|---|---|---|
| Realsense | `/camera/camera/color/image_raw` | `/boostercamera/head/rgb` |
| ZED | `/zed/zed_node/left/image_rect_color` | `/boostercamera/head/rgb` |
| D-Robotics | `/image_left_raw` | `/boostercamera/head/rgb` |
| Orbbec | `/camera/color/image_raw` | `/boostercamera/head/rgb` |

---

## ✨ New Features

### Auto Hand-Eye Calibration (`src/vision/scripts/auto_handeye_calib.py`)

Replaces the old manual `S`-key workflow with fully or semi-automated chessboard-to-robot calibration.

#### FULL-AUTO Mode
- Robot head sweeps a 45-position pitch/yaw snake grid
- Auto-detects chessboard at each angle (same OpenCV algorithm as original C++ calibrator)
- 4D frame scoring: fill ratio (0-40) + skew angle (0-30) + corner quality (0-20) + pose diversity (0-10)
- Auto-captures when score ≥ 50; auto-computes extrinsics at 8+ frames
- Head control via `LocoApiTopicReq` / `RpcReqMsg` (same topic gamepad uses)

#### SEMI-AUTO Mode
- Manual gamepad head control, automatic capture trigger
- Real-time scoring overlay on video feed

#### `--discover` Mode
- Sniffs `/LocoApiTopicReq` for `kRotateHead` API ID
- User moves head once with gamepad → script auto-identifies the API ID
- No SDK headers needed on robot

#### Quick Start
```bash
# Step 1: Find API ID (on robot, once)
python3 auto_handeye_calib.py --discover

# Step 2: Run full-auto calibration
python3 auto_handeye_calib.py --config src/vision/config/vision.yaml --api-id <number>
```

```
Sweep Grid:  Yaw -60°→+60° (15° step, 9 cols) × Pitch -25°→-5° (5° step, 5 rows)
Total:       45 positions, snake scan pattern
Output:      YAML compatible with vision.yaml extrinsics format
Method:      OpenCV Tsai (CALIB_HAND_EYE_TSAI)
```

#### Hotkeys
| Key | Action |
|---|---|
| `q` | Quit |
| `r` | Reset captures |
| `c` | Force compute with current frames (≥3) |

---

## 🔧 Technical Details

### Sweep Grid Design
```
     Yaw:  -60  -45  -30  -15   0   +15  +30  +45  +60  (degrees)
Pitch -25  ╔══════════════════════════════════════════╗  Left→Right
      -20  ║  ←──────────────────────────────────  ║  Right→Left
      -15  ║  ──────────────────────────────────→  ║  Left→Right
      -10  ║  ←──────────────────────────────────  ║  Right→Left
       -5  ║  ──────────────────────────────────→  ║  Left→Right
           ╚══════════════════════════════════════════╝
```
Snake pattern minimizes wasted head motion.

### Files Changed
- `v2.1/src/vision/scripts/auto_handeye_calib.py` — New (~30KB)
- `v2.1/src/vision/CMakeLists.txt` — Added install rule for script
- `v2.1/src/vision/package.xml` — Added Python runtime deps (exec_depend only)
- `v2.1/src/vision/src/vision_node.cpp` — Camera topic fix
- `v2.0/src/vision/src/vision_node.cpp` — Same camera topic fix

### Dependencies
- `opencv-python` (chessboard detection, Tsai)
- `scipy` (spatial transforms)
- `pyyaml` (config read/write)
- `cv_bridge` (ROS2 image conversion)
- `booster_msgs` (RpcReqMsg for head control, AUTO mode only)

---

## ⚠️ Known Limitations
- **FULL-AUTO requires `kRotateHead` API ID** — use `--discover` on robot to find it
- **No VM/simulation testing** — `booster_gym` is for RL motor control only, not vision node simulation
- **GitHub often unreachable from China** — commit ready locally, push when VPN available

---

[Full CHANGELOG →](https://github.com/Unknownuserfrommars/booster-patch/blob/main/v2.1/CHANGELOG.md)
