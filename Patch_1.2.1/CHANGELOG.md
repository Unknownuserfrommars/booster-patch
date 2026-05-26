# Patch v1.2.1 — CHANGELOG


## v1.2.1 - Improved Possession Detection (2026-05-26)

**Fix:** Possession logic now uses 5-state machine instead of simple distance check.
Previously, the robot would panic-defend whenever an opponent was near the ball,
even during our own attack.

**New config params:**
- `possession_margin: 0.25` - distance margin (m) to determine who truly has the ball
- `possession_hysteresis_secs: 0.3` - time (seconds) state must hold before switching
- `attack_protection_dist: 0.5` - if our attacker is within this distance, keep attacking

**New behavior:**
- 5 states: OUR_POSSESSION, OPP_POSSESSION, CONTESTED, FREE_BALL, DANGER
- Ball velocity direction: ball moving toward their goal = our attack, toward our goal = danger
- Nearest opponent distance calculated from obstacle detection
- Hysteresis prevents flickering between attack/defend every frame
- Attack protection: lead attacker keeps attacking even if opponent is nearby
## v1.2 — Striker Defense System (2026-05-26)

**New feature:** Non-goalie robots can now detect opponent possession and respond with steal, clearance, or defensive positioning.

**New config params:**
- `enable_striker_defense: false` — master switch
- `defensive_risk_tolerance: 0.5` — 0.0=safe clear, 1.0=always steal
- `defensive_steal_range: 1.5` — max distance to attempt steal (m)
- `defensive_clear_power: 6.0` — kick power for clearance

**New behavior:**
- `steal` decision: chase ball and kick to sideline when close
- `defend` decision: position between opponent and goal when too far to steal
- Clearance kicks use `calcClearDir()` to aim at sideline instead of goal

**Internal changes:**
- `brain_data.h`: added `isOpponentPossession`, `isClearance` fields
- `brain.cpp`: added `calcClearDir()` function, clearance power logic in pubKickMsg
- `brain_tree.cpp`: opponent possession detection in StrikerDecide
- `subtree_striker_play.xml`: steal/defend actions added

## v1.1 — Quick Shot, Power Shot, Deflection Shot

**Free-kick Power Shot:** During free kicks, power shot toward goal (kickSubType=1, power=9.0)
- `enable_freekick_powershot`, `freekick_powershot_power`, `freekick_powershot_min_dist`

**Quick Shot:** Fast kick (400ms) when very close to goal in multi-robot games (kickSubType=2)
- `enable_quickshot`, `quickshot_max_range`

**Deflection Shot:** Weighted random deflection attempt when normal shot is blocked (kickSubType=3)
- `deflection_shot_weight` (0.0-1.0), `deflection_power_boost`, `enable_freekick_deflection`

**Internal changes:**
- `Kick.msg`: added `kick_subtype` field
- `brain_data.h`: added `kickSubType` field
- `brain.cpp`: kick type power logic in pubKickMsg
- `brain_tree.cpp`: quickshot + deflection decisions in StrikerDecide
- `subtree_striker_freekick.xml`: power shot sequence
- `subtree_striker_play.xml`: quickshot action
- `config.yaml`: +7 params

## v1.0 — Original Patch

- Initial patch of BoosterRobotics/robocup_demo
- Parameter tuning: kick_range, speed limits, ball detection range
- Leg selection logic in StrikerDecide
- Tightened no_turn_threshold to 0.026 rad (1.5 deg)
- Reduced kick power for controlled shots

