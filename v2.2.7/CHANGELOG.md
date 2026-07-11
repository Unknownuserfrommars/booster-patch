# Patch v2.2.7 — CHANGELOG

## v2.2.7 — Rerun Post-Match Logging On By Default (2026-07-11)

Per the team's rerun.docx usage guide. Matches are unobservable live (ethernet unplugged), so `.rrd`
file logging is now the default: `rerunLog.enable_file: true`, with `img_interval` 1 → 10 (~3fps
image logging) to protect match-day CPU/disk. Files land in `/home/booster/Workspace/rrlog`, split
every 5 minutes; open them afterwards with the Rerun Viewer (viewer version must match the robot's
rerun_sdk version). `enable_tcp` stays `false` — flip it plus `server_ip` (your PC's wired IP) for
live viewing during pre-match testing/calibration only. Config-only change, no rebuild needed.

---

## v2.2.6 — Tournament Anti-Interference Rules Compliance (2026-07-10)

Per the organizer's rules update (upd.docx, 避免外部连接干扰比赛-解决方案). Referees pull system logs;
non-compliant connections are penalized.

### Automated (this patch)
- Bundled the **official** `scripts/kill_booster_server.sh` (verbatim, do not modify) — stops the
  `boosterserver` / `server.motion` service that provides phone-App and Bluetooth connectivity
  (handles firmware 1.7 `bdb service`, 1.6 `bdb container`, and pre-1.6 `BoosterServer` process).
- `scripts/start.sh` now runs it in the background at the exact position shown in the official doc:
  `sudo -v && sudo -b bash ./scripts/kill_booster_server.sh >/dev/null 2>&1`
  (after `./scripts/stop.sh`, before `jetson_clocks`). The service auto-starts on boot, so every
  match start re-kills it. After it runs, the rear breathing light turns red — this is the expected
  Bluetooth-off indicator, not an error.

### Manual steps (cannot be automated — do these on each robot before the match)
1. Block booster-studio connections: `sudo passwd booster` (studio logins need the user password).
2. Report each robot's wireless IP to the organizers: `ifconfig`, read the `wlP1p1s0` inet address.
   Only the registered eight robot IPs are allowed on the field network; others are blacklisted.
3. Do not connect to the field network outside of matches.

---

## v2.2.5 hotfix — vision_node startup crash after calibration (2026-07-10)

- `vision_node` terminated with `YAML::TypedBadConversion<string>` at startup when the merged
  `/opt/booster/vision.yaml` lacked `camera.type` — the read was unguarded. Now falls back to
  `realsense` via `as_or` (same fix as the robot-verified K1_5v5_Demo_v1.6_fixed reference);
  `detection_model.classnames` similarly guarded with the default class list.
- Root cause of the broken system config: `start_calibration.sh` unconditionally copied
  `/tmp/vision.yaml` over `/opt/booster/vision.yaml`. When the calibration node saves to
  `/opt/booster` directly, a stale/partial leftover `/tmp/vision.yaml` clobbered the good config.
  The copy now only happens if `/tmp/vision.yaml` was freshly written by this run, and the script
  verifies `/opt/booster/vision.yaml` contains `camera.type` + `detection_model` afterwards,
  auto-repairing from the package config (with a `.broken-<timestamp>` backup) if not.
- On-robot recovery without rebuilding: restore a complete config over `/opt/booster/vision.yaml`
  (newest `~/Workspace/calibration_log/handeye/*/vision_local.yaml.calbration_res_*` keeps today's
  calibration; otherwise the package `src/vision/config/vision.yaml`).

---

## v2.2.5 — CRITICAL ABORT Fix + Race Config + Review Hardening (2026-07-10)

### CRITICAL: ABORT signal permanently disabled receiving robots (latent since v2.2)
- `handleReceivedTeamSignal`'s `ABORT` case set `control_state = 1` — the gamepad/manual branch of `game.xml`.
  With no gamepad allowed mid-match, a robot that received one ABORT stood idle for the rest of the match
  (only LT+B or a restart recovers). Removed; ABORT now stops for one tick, releases tactic/lead, and resumes
  autonomous play.
- `abortTwoToOneTactic` broadcast that `ABORT` on every wall-pass abort (setup timeout, stale comms, extra
  corridor opponent). Now sends `WALL_PASS_COMPLETE`, which only releases the partner's wall-pass state.

### Race config profile (no-warmup, no-intervention match; all reversible in config.yaml)
- `enable_auto_visual_kick: false` — whether this firmware's VisualKick physically kicks was never verified;
  not gambling without a warmup. The fixed scripted kick pipeline carries the match.
- `two_to_one.enabled: false` — never field-verified; avoids 7s two-robot choreography variance.
- `enable_stable_kick: false` — the 1s stabilize plus ~1.8s kick exceeds the 2.5s decision-commit window and
  could reintroduce mid-kick flapping; without it the kick finishes in ~1.8s, safely inside.

### Review hardening
- `GlanceAtGoal` early-exit (goal outside head range) now zeroes velocity.
- `Kick::onRunning` obstacle-avoid branch: min-speed amplification disabled (matches onStart fix).

---

## v2.2.4 — Deployment + Manual Calibration Fixes (2026-07-09)

### Deployment (merged from Codex's "fixed-for-robot" package)
- `scripts/assist.sh` and `robocup_game_assist.service`: `tree:=assist` → `tree:=chase` — `assist.xml` never
  existed, so the assist autostart crashed the brain at init.
- `robocup_game_assist.service`: `Restart=never` (invalid systemd value) → `Restart=no`; added
  `WorkingDirectory`; fixed missing trailing newline.
- `distribution/install.sh` / `uninstall.sh`: install root is now `/home/booster/Workspace/robocup_demo`
  (overridable via `ROBOCUP_WORKSPACE`); install backs up an existing install instead of `rm -rf`;
  `set -e` + quoted paths + tolerant service stop/disable ordering.

### Manual hand-eye calibration (`ros2 run vision calibration_node handeye ...`)
- `src/vision/CMakeLists.txt`: `install(DIRECTORY model ... OPTIONAL)` — source checkouts from GitHub have no
  `model/` dir (engines are stripped, git drops the empty dir), which failed the vision install step and caused
  "Package 'vision' not found" after a build.
- `calibration_node.cpp`: intrinsics topic `rgb/camera_info` → `depth/camera_info`, matching the
  robot-verified K1_5v5_Demo_v1.6_fixed reference (rgb/camera_info is not published on some firmware).
- `scripts/start_calibration.sh`: now checks that the workspace is built and that the `vision` package resolved
  after sourcing, with actionable error messages (vision only builds on the robot — CUDA/TensorRT required).

---

## v2.2.3 — Kick Pipeline Fixes + RL Kick Hand-off + GlanceAtGoal (2026-07-06)

### Kicking (P0)
- Fixed inverted margin fallback in `Brain::isAngleGood()` — the 0.5m goalpost margin was applied whenever the
  goal window was *smaller* than 120° (i.e. almost always), shrinking the shot-acceptance window to ±6-8° at range.
  Now the bigger margin only applies close to the goal.
- Relaxed `reachedKickDir`: static threshold 0.1 → 0.2 rad; sign-flip release tightened π/6 → 0.25 rad
  (faster to satisfy, bounded aim error at release).
- Added a 2.5s kick-decision commit latch in `StrikerDecide` — once in `kick`/`safe_shoot`/`cross`, the decision
  holds while the ball stays in kick range, so the robot's own motion can no longer flap the angle conditions and
  halt the stateful `Kick` node mid-execution.
- Fixed the "stabilize" phase of `Kick`: `setVelocity(-0.05, …, applyMinX=true)` was amplified to a 0.3 m/s
  backward walk for 1s, pushing the ball out of kick range and aborting the kick. Now stands still.
- `Kick` now crab-walks through the ball **along the planned `kickDir`** (aiming 0.3m beyond the ball, clamped
  to ±0.35 rad of the ball bearing) instead of walking at the ball bearing — kicks now travel where aimed.
- `GoalieDecide` writes its clear direction into `data->kickDir` so the goalie's `Kick` aims correctly.
- Kick entry now tolerates ≤400ms of ball-detection dropout (ball is often occluded at contact range).
- Adjust orbit speed `tangential_speed_near` 0.15 → 0.3; `near_ball_speed_limit` 0.4 → 0.6.

### New: GlanceAtGoal (aim verification before shooting)
- Before a `kick`/`safe_shoot`, if no opponent-half goalpost was seen and no successful re-localization happened
  within `max_aim_age_ms`, the robot pauses ~0.6s and turns its head toward the goal to acquire goalposts /
  re-localize, then shoots. Config: `strategy.glance_at_goal.{enable,msecs,max_aim_age_ms,cooldown_ms}`.
- `detectProcessGoalposts` now timestamps opponent-half goalpost observations (`lastGoalObservationTime`).

### Behavior fixes
- Removed the empty auto-visual-defend branch in `GoalieDecide` that produced an empty decision (goalie no-op
  ticks) whenever the ball was 0.5-2.0m ahead with a clear front.
- Possession detection now measures opponent-to-ball distance from vision-confirmed `Opponent` robots instead of
  raw depth-grid obstacles (teammates/referees/posts no longer hijack the kick into steal/defend).
- The steal-vs-defend risk roll is cached for 1s instead of re-rolled every 10ms tick.
- Lead election got a sticky margin (current lead keeps it unless a teammate is ≥0.5 cost cheaper).
- `Kick::onHalted`/`StandStill::onHalted` no longer do seconds-vs-milliseconds time arithmetic.
- Removed duplicated leg-selection block in `StrikerDecide`.

### RLVisionKick band split (RL/scripted hand-off) — `enable_auto_visual_kick` re-enabled
- The RL VisualKick branch now only triggers in a 1.2–4.0m band (`auto_visual_kick_enable_dist_min` raised
  0.2 → 1.2, with a code-enforced floor of `kick_range * 1.2`), so it can no longer shadow the deterministic
  `Kick` node's <0.75m window. RL owns the approach; the scripted kick owns the finish.
- Added a stall hand-off inside `RLVisionKick`: if the ball sits within `auto_visual_kick_handoff_range`
  (0.85m) essentially unmoved for `auto_visual_kick_stall_ms` (2.5s), the node exits ("track-but-never-kick"
  firmware behavior) and the scripted Kick takes over.
- Implemented the previously stubbed `isMinIntervalSatisfied()` as a real re-entry cooldown
  (`auto_visual_kick_reentry_cooldown_ms`, 4s), checked in `StrikerDecide` before re-entering the RL mode —
  no more exit/re-enter thrash.
- With these guardrails in place, `enable_auto_visual_kick` is now `true` in config.yaml.

---

# Patch v2.2.2 — CHANGELOG

## v2.2.2 — GameController Safety + Build Fixes (2026-06-27)

### Safety
- Added a final referee-state hard stop after each behavior-tree tick for `SET`, `END`, penalty, free-kick `STOP`, and free-kick `SET`.
- Added an immediate zero-velocity command when GameController transitions into `SET`.
- Made malformed GameController values fail closed: invalid primary state becomes `SET`, invalid sub-state becomes `STOP`, and invalid team/player arrays force a stop instead of leaving stale `PLAY` behavior active.

### Build / Packaging
- Renamed macro-conflicting `TwoToOneRole::NONE` and `TeamSignal::NONE` symbols to avoid `RoboCupGameControlData.h`'s global `#define NONE`.
- Included `scripts/auto_calib.sh` in the patch package.

---

## v2.2.1 — Conservative 3v3 Two-on-One Wall Pass (2026-06-26)

### Strategy
- Added a conservative 2-on-1 wall-pass FSM for 3v3:
  1. Carrier detects exactly one opponent in the forward corridor.
  2. Carrier calls one reachable striker teammate with `WALL_PASS_START + PID`.
  3. Overlapper runs to a flank target and replies `WALL_PASS_READY + carrier PID`.
  4. Carrier passes, runs beyond the defender, and sends `WALL_PASS_RUN_READY + support PID`.
  5. Supporter returns the pass, then both robots release the tactic.
- Added aborts for stale comms, lost/low-confidence ball, extra opponents entering the corridor, timeout, non-PLAY game state, ball out, and recovery/fallen state.
- Uses fixed geometry instead of trained zones/APF so the behavior is easier to test quickly.

### Config
- Added `strategy.two_to_one.*` parameters for trigger range, corridor width, flank/run offsets, ready radius, timeouts, ball confidence, and abort behavior.
- Set local default `game.number_of_players` to `3` for the current 3v3 match setup.

### Comms
- Added targeted CIDs:
  - `2600 + PID`: `WALL_PASS_START`
  - `2700 + PID`: `WALL_PASS_READY`
  - `2800 + PID`: `WALL_PASS_RUN_READY`
  - `2900`: `WALL_PASS_COMPLETE`

---

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
