# Patch v1.2.2 — CHANGELOG

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
