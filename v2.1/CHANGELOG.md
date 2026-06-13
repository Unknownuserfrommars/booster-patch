# Patch v2.1 — CHANGELOG

## v2.1 — Auto Hand-Eye Calibration (2026-06-13)

### 🦀 Our Patches
- **🐛 FIX: Camera topic mismatch** — `vision_node.cpp` had wrong camera topic names
  (`/camera/camera/color/image_raw` → `/boostercamera/head/rgb`).
  Restored to v1.6 unified topic scheme. Vision node was subscribing to topics
  that the booster camera bridge doesn't publish to, so vision.log never refreshed.
  Same fix applied to v2.0.
- **Auto Hand-Eye Calibration**: `src/vision/scripts/auto_handeye_calib.py`
  - **FULL-AUTO mode**: Sweeps robot head through 45-position pitch/yaw grid, auto-detects
    chessboard at each angle, auto-captures 8+ diverse frames, auto-computes extrinsics
  - **SEMI-AUTO mode**: Manual gamepad head control, auto-capture replaces manual S key
  - Scoring: fill ratio (0-40) + skew angle (0-30) + corner quality (0-20) + pose diversity (0-10)
  - Uses OpenCV Tsai method (`cv2.calibrateHandEye`), outputs YAML compatible with vision.yaml
  - Requires `--api-id <kRotateHead>` for full-auto mode (find on robot via SDK headers)

---

# Patch v2.0 — CHANGELOG

## v2.0 — Merged onto Booster v1.6 SDK (2026-06-10)

### 🏭 Official v1.6 SDK Changes (from BoosterRobotics)
- **RLVisionKick v1/v2**: `RLVisionKick.visual_kick_version` param (kV1/kV2), uses public `LocoApiId::kVisualKick`
- **Camera topics unified**: `/boostercamera/head/rgb` and `/boostercamera/head/depth`
- **New API**: `changeRobocupMode()` — switches to kSoccer mode + exits VisualKick
- **robocupWalk() changed**: now only exits VisualKick, no longer changes gait
- **Locator relaxed**: `min_marker_count` 5→4, `max_residual` 0.35→0.4

### 🦀 Our Patches (v1.1 → v1.3.1, carried forward)
- **v1.3 Goalie overhaul**: ShotDetector, DivingSave, QuickClear, ImprovedGoaliePosition
- **v1.3.1 BT XML fix**: Wrapped StrikerFreekick BehaviorTree children in single Sequence
- **v1.3.1 try-catch**: Error handling on all 3 main.cpp threads
- **v1.2 Striker defense**: Steal/clear/defend, 5-state possession detection
- **v1.1 Kicking**: Free-kick power shot, quick shot, deflection shot
- **v1.2.4 Crash fix**: Removed broken Script node, duplicate Kick sequence

---

# Patch v1.3 — CHANGELOG

## v1.3 — Goalie Overhaul: Shot Detection & Diving Saves (2026-05-28)

**New nodes for goalie:**
- **`ShotDetector`** — monitors ball velocity, predicts goal-line intercept, flags incoming shots
- **`DivingSave`** — three-phase save: lateral crabWalk approach → directional squatBlock → hold position
- **`QuickClear`** — after a save: stand up, find ball, kick to sideline in one rapid sequence
- **`ImprovedGoaliePosition`** — velocity-aware trajectory projection replaces static linear interpolation

**Tree changes:**
- `subtree_goal_keeper_play.xml` rewritten with shot detection pipeline
- Shot detection runs at high priority — when a shot is detected, it interrupts normal goalie behavior
- Pipeline: `ShotDetector` → `DivingSave` → `QuickClear` → resume normal play

**New config params (all under `strategy.goalie`):**
- `shot.enable`, `shot.velocity_threshold`, `shot.reaction_time_window`
- `save.squat_block_msecs`, `save.block_hold_msecs`, `save.crab_speed`
- `clear.enable_quick_clear`, `clear.clear_power`
- `position.enable_trajectory_predict`

**Bug fixes carried from v1.2.4:**
- Fixed crash: removed broken `<Script code=" brain->data->kickSubType = 1; ">` node in freekick XML
- Fixed duplicate Kick sequence in `subtree_striker_freekick.xml`
- Moved kickSubType=1 logic to C++ `handleSpecialStates()`

---

## v1.2.2 — Code Cleanup & Defense Restructure (2026-05-28)

**Fixes from code review (fix.docx):**
- **Duplicates cleaned:** `brain_data.h` had 6x `kickSubType`, 2x `kickLeg`, 2x `isClearance` — now single declarations
- **Kick.msg deduplicated:** `kick_subtype` and `leg` fields were repeated — cleaned to one each
- **calcClearDir() declared** in `brain.h` — was missing, would cause linker error
- **ROS parameters declared:** 15 new `declare_parameter()` calls added so params can be read reliably
- **Freekick XML deduplicated:** removed duplicate power shot sequence in `subtree_striker_freekick.xml`

**Behavior restructure:**
- **Possession detection moved to top** of `StrikerDecide::tick()` — defense decisions now run BEFORE attack flow, preventing "try to attack while opponent has ball" scenarios
- **`isClearance` and `kickSubType` reset** at start of each tick — no leakage between frames
- **Defense before assist:** non-lead robots now check possession before blindly assisting attack
- **DANGER state implemented:** `rawState = 4` when ball moves fast (`ballVx < -0.5`) toward our goal
- **Obstacle filtering:** `getObstacles()` now excludes known markers/goalposts when calculating opponent distance
- **Real dt for ball velocity:** uses `msecsSince(prevBallTime)` instead of hardcoded 30fps
- **First-frame guard:** `hasPrevBall` flag prevents garbage velocity on initial observation
- **Steal is now Sequence:** behavior tree uses `<Sequence>` (Chase + Kick) instead of just Chase

**New/updated config defaults:**
- Tutorial defaults synced to match config.yaml
- Possession params: `possession_margin: 0.25`, `possession_hysteresis_secs: 0.3`, `attack_protection_dist: 0.5`

## v1.2.1 — Improved Possession Detection (2026-05-26)

**Fix:** Possession logic now uses 5-state machine instead of simple distance check.
Previously, the robot would panic-defend whenever an opponent was near the ball.

**New config params:**
- `possession_margin: 0.25` — distance margin (m) to determine who truly has the ball
- `possession_hysteresis_secs: 0.3` — time (seconds) state must hold before switching
- `attack_protection_dist: 0.5` — if our attacker is within this distance, keep attacking

**New behavior:**
- 5 states: OUR_POSSESSION, OPP_POSSESSION, CONTESTED, FREE_BALL, DANGER
- Ball velocity + nearest opponent distance computed every tick
- Hysteresis prevents flickering between attack/defend

## v1.2 — Striker Defense System (2026-05-26)

**New feature:** Non-goalie robots detect opponent possession and respond with steal, clearance, or defensive positioning.

**New config params:**
- `enable_striker_defense: false`, `defensive_risk_tolerance: 0.5`, `defensive_steal_range: 1.5`, `defensive_clear_power: 6.0`

**New behavior:**
- `steal` decision: chase ball and kick to sideline when close
- `defend` decision: position between opponent and goal when too far to steal
- Clearance kicks use `calcClearDir()` to aim at sideline instead of goal

## v1.1 — Quick Shot, Power Shot, Deflection Shot

- **Free-kick Power Shot:** `enable_freekick_powershot`, `freekick_powershot_power`, `freekick_powershot_min_dist`
- **Quick Shot:** `enable_quickshot`, `quickshot_max_range`
- **Deflection Shot:** `deflection_shot_weight` (0.0-1.0), `deflection_power_boost`, `enable_freekick_deflection`
- Internal: `Kick.msg kick_subtype`, `brain_data.h kickSubType`, config +7 params

## v1.0 — Original Patch

- Initial patch of BoosterRobotics/robocup_demo
- Parameter tuning: kick_range, speed limits, ball detection range
- Leg selection logic, tightened no_turn_threshold, reduced kick power
