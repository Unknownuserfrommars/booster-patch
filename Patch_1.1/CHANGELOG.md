# Patch v1.1 — CHANGELOG

## New Features

### 1. Free-kick Power Shot ⚡
**Purpose:** During free kicks (ball out of bounds), the robot can now attempt a powerful shot directly at goal when the path is clear.

**How it works:** When `enable_freekick_powershot` is ON and the robot is on the attack side during a free kick, it will set kickSubType to 1 (freekick_power). The walk engine receives `power = 9.0` for maximum range.

**Config params:**
```yaml
enable_freekick_powershot: false   # ON/OFF
freekick_powershot_power: 9.0      # Kick power (distance in meters)
freekick_powershot_min_dist: 3.0   # Minimum distance to goal
```

### 2. Quick Shot 🏃‍♂️
**Purpose:** In 3v3/5v5 scenarios, when the robot gets the ball very close to goal, it takes an immediate fast kick instead of going through the full adjust sequence — catching defenders off guard.

**How it works:** When `enable_quickshot` is ON and the robot's ball range is under `quickshot_max_range`, StrikerDecide returns "quickshot" instead of "kick". The behavior tree executes a faster kick (400ms vs 1000ms) with less stabilization (200ms vs 1000ms).

**Config params:**
```yaml
enable_quickshot: false     # ON/OFF
quickshot_max_range: 1.2    # Max distance from ball for quick shot
```

### 3. Deflection Shot 🎯
**Purpose:** When opponents are blocking the direct path to goal, the robot adds extra power to blast through or deflect off opponents into goal.

**How it works:** When `enable_deflection_shot` is ON and opponents are detected between the robot and goal, the kick power is increased by `deflection_power_boost` on top of the base power.

**Config params:**
```yaml
enable_deflection_shot: false   # ON/OFF
deflection_power_boost: 2.5     # Extra power added for deflection attempts
```


### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---

## Files Changed (9 files)

| File | Change |
|
### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---|
### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---|
| `src/brain/config/config.yaml` | +7 new params (3 features) |
| `src/brain/msg/Kick.msg` | +1 field: `kick_subtype` |
| `src/brain/include/brain_data.h` | +1 field: `kickSubType` |
| `src/brain/src/brain.cpp` | pubKickMsg: power logic + subtype published |
| `src/brain/src/brain_tree.cpp` | StrikerDecide: quickshot + deflection decisions |
| `src/brain/behavior_trees/subtrees/subtree_striker_freekick.xml` | +power shot sequence |
| `src/brain/behavior_trees/subtrees/subtree_striker_play.xml` | +quickshot action |
| `patch_info.txt` | v1.0 → v1.1 |


### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---

## Kick Subtype Values

| Value | Type | When |
|
### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---|
### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---|
### v1.1 Updates (after initial release)

**Deflection shot refined:**
- Removed `enable_deflection_shot` (on/off) - replaced with `deflection_shot_weight` (0.0~1.0)
- `0.0` = disabled (default), `0.1`-`1.0` = probability of deflection when normal shot is blocked
- Normal shot always takes priority - deflection only triggers when a straightforward shot isn't possible
- Added `enable_freekick_deflection` for free kick deflection attempts
---|
| 0 | Normal | Default — standard kick logic |
| 1 | Free-kick Power | During free kicks on attack side |
| 2 | Quick Shot | Close to goal, multi-robot game |
| 3 | Deflection | Opponents blocking path to goal |
