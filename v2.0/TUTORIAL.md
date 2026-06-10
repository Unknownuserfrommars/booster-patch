# Patch v1.3 — Tutorial

## v1.3 Goalie Overhaul: Shot Detection & Diving Saves

### What's New

The goalie now has a **three-stage save pipeline**:
1. **ShotDetector** — continuously monitors ball velocity. When a shot is detected heading toward goal, it flags `shot_detected=true` on the blackboard.
2. **DivingSave** — interrupts whatever the goalie was doing and executes a three-phase save:
   - **Approach**: crabWalk laterally toward the predicted intercept point
   - **Block**: directional squatBlock (left/right/center) to cover the shot
   - **Hold**: maintain block position until threat passes
3. **QuickClear** — after a save, stands up, finds the ball, and kicks it to the sideline.
4. **ImprovedGoaliePosition** — uses ball velocity for trajectory prediction (replaces old static linear projection).

### New Config Parameters

```yaml
strategy:
  goalie:
    shot:
      enable: true                    # Master switch for shot detection
      velocity_threshold: 0.3         # m/s toward own goal to trigger
      reaction_time_window: 1.5      # seconds ahead to predict
    save:
      squat_block_msecs: 500.0       # Time for squat block execution
      block_hold_msecs: 1500.0       # Max hold duration after block
      crab_speed: 1.0                # Lateral dive speed (m/s)
    clear:
      enable_quick_clear: true       # Kick ball after save
      clear_power: 6.0               # Clearance kick power
    position:
      enable_trajectory_predict: true  # Use velocity for positioning
```

### How It Works

The shot detection runs at **high priority** in the behavior tree:

```
GoalKeeperPlay tick:
  ├── Locate + SelfLocate (always)
  ├── ShotDetector (runs every tick, monitors ball)
  │
  ├── [IF shot_detected=true]  ← HIGH PRIORITY, interrupts everything
  │   ├── DivingSave  (approach → block → hold)
  │   └── QuickClear  (stand → find ball → kick)
  │
  └── [IF shot_detected=false] ← Normal goalie play
      ├── GoalieDecide → {find, retreat, chase, adjust, kick}
      ├── ImprovedGoaliePosition (trajectory-aware)
      ├── Chase / Adjust / Kick (as usual)
```

### Testing the Goalie

**Test 1: Basic shot detection**
```
1. Enable the goalie (player_role: goal_keeper)
2. Roll/kick a ball toward the goal at moderate speed
3. Watch the console for "SHOT DETECTED!" message
4. The goalie should crabWalk toward intercept + squat block
5. After the save, goalie should stand and clear the ball
```

**Test 2: Fast shot reaction**
```
1. Kick ball hard toward corner of the goal
2. ShotDetector should predict intercept point before ball arrives
3. Goalie should lateral crabWalk to intercept point
4. Goalie should execute directional squat block
5. Check: does the block happen BEFORE the ball arrives?
   - If too slow: decrease velocity_threshold (triggers earlier)
   - If too jerky: increase reaction_time_window
```

**Test 3: Center shot**
```
1. Kick ball directly at the goalie (center of goal)
2. Shot direction should be "center"
3. Goalie should squat block without lateral movement
4. Goalie should hold until ball is past, then quick clear
```

### Tuning Tips

| Symptom | Parameter to adjust | Direction |
|---|---|---|
| Goalie doesn't react to shots | `shot.velocity_threshold` | Lower (e.g., 0.2) |
| Goalie dives for everything (false positives) | `shot.velocity_threshold` | Raise (e.g., 0.5) |
| Goalie arrives too late to save | `save.crab_speed` | Raise (e.g., 1.5) |
| Goalie overshoots intercept point | `save.crab_speed` | Lower (e.g., 0.6) |
| Squat block doesn't last long enough | `save.block_hold_msecs` | Raise (e.g., 2500) |
| Clearance kick is too weak | `clear.clear_power` | Raise (e.g., 8.0) |
| Goalie stands in wrong place during normal play | `position.enable_trajectory_predict` | Try false to use old linear projection |

### Disabling the New Goalie

To revert to the old goalie behavior:
1. Set `strategy.goalie.shot.enable: false`
2. Replace `subtree_goal_keeper_play.xml` with the v1.2.4 version
3. Rebuild

---

# Patch v1.2.2 — Tutorial: Using New Features

## Enabling Features

Edit `src/brain/config/config.yaml` and set any of these to `true`:

```yaml
strategy:
  # --- Free-kick power shot ---
  enable_freekick_powershot: true
  freekick_powershot_power: 9.0
  freekick_powershot_min_dist: 3.0

  # --- Quick shot ---
  enable_quickshot: true
  quickshot_max_range: 3.0

  # --- Deflection shot ---
  enable_deflection_shot: true
  deflection_power_boost: 2.5
```

## How Each Feature Works

### Free-kick Power Shot
1. Ball goes out of bounds → GameController signals free kick
2. Robot positions itself at the free kick spot
3. If on attack side → StrikerFreekick tree runs the power shot sequence
4. Robot calculates kick direction, sets `kickSubType = 1`
5. Walk engine receives `power = 9.0` — long-range blast to goal

### Quick Shot
1. Robot chases and captures the ball
2. StrikerDecide checks: is `ballRange < quickshot_max_range` (1.2m)?
3. If yes, and `enable_quickshot = true` → returns `"quickshot"` decision
4. Behavior tree runs the quickshot Kick node:
   - `min_msec_kick = 400` (vs 1000 for normal kick)
   - `msecs_stablize = 200` (vs 1000 for normal kick)
5. Robot kicks immediately without the full adjust sequence

### Deflection Shot
1. Robot has ball, heading toward goal
2. StrikerDecide checks: is opponent within 1.5m in the kick direction?
3. Also checks: is `threatLevel < threatThreshold` (safe to attempt)?
4. If both true → sets `kickSubType = 3`
5. pubKickMsg adds `deflection_power_boost` (2.5) to base power
   - Close range: 4.0 + 2.5 = 6.5 power
   - Long range: 1.5 + 2.5 = 4.0 power

## Testing

### Free-kick Power Shot
```
1. Place ball near sideline (simulating out-of-bounds)
2. Start GameController with free kick for your team
3. Robot should power-shot toward goal
4. Check: does the ball reach the goal area?
   - If too weak: increase freekick_powershot_power
   - If overshooting: decrease it
```

### Quick Shot
```
1. Set enable_quickshot: true, number_of_players: 5
2. Place ball 0.5m from goal, directly in front
3. Robot should take a fast shot (noticeably faster than normal)
4. Check: is it too fast (inaccurate) or too slow (defender catches up)?
   - Adjust quickshot_max_range up/down
   - Adjust min_msec_kick in subtree_striker_play.xml
```

### Deflection Shot
```
1. Place an opponent robot 1m in front of the ball, between robot and goal
2. Enable enable_deflection_shot: true
3. Robot should add extra power and shoot through/around
4. Check: does the ball reach goal? Does it deflect off opponent?
   - If too weak: increase deflection_power_boost
   - If opponent detection range is wrong: adjust distToObstacle threshold in brain_tree.cpp
```

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| Power shot fires but ball doesn't reach goal | `freekick_powershot_power` too low | Increase to 10.0 or 11.0 |
| Robot never triggers quick shot | `quickshot_max_range` too small or feature disabled | Check config values |
| Deflection shot makes robot miss wildly | `deflection_power_boost` too high | Reduce to 1.5 or 1.0 |
| Robot chooses deflection when path is clear | Opponent detection threshold too wide | Increase distToObstacle check in brain_tree.cpp |
| Free kick power shot never fires | Not on attack side, or ball not known | Check gc_is_sub_state_kickoff_side flag |


### Deflection Shot (v1.2 update)

**Config params:**
```yaml
deflection_shot_weight: 0.0       # 0.0 = disabled. 0.1-1.0 = probability when normal shot blocked
deflection_power_boost: 2.5       # Extra power for deflection attempts
enable_freekick_deflection: false  # Also attempt deflection during free kicks
```

**How it works:**
1. Robot checks if a normal/straightforward shot is possible first
2. If normal shot IS possible -> always takes the normal shot (deflection never overrides)
3. If normal shot is NOT possible (angle blocked, opponents in the way) AND obstacles detected:
   - Rolls a random number against `deflection_shot_weight`
   - Weight = 0.3 means 30% chance to attempt deflection, 70% chance to keep adjusting
   - Weight = 1.0 means always try deflection when normal shot can't work
4. This makes deflection a fallback strategy, not a primary choice

**Testing:**
```
1. Place an opponent robot blocking the direct path to goal
2. Position your robot in a corner area where a straight shot is difficult
3. Set deflection_shot_weight to 0.3, 0.7, or 1.0
4. Observe: robot should attempt deflection when adjust keeps failing
5. Higher weight = more aggressive deflection attempts
```


### Striker Defense (v1.2)

**Config params:**
```yaml
enable_striker_defense: true        # Master switch for non-goalie defense (Kevin: enabled)
defensive_risk_tolerance: 0.5       # 0.0 = safe clear, 1.0 = always steal
defensive_steal_range: 1.5          # Max distance to attempt steal (m)
defensive_clear_power: 6.0          # Kick power for clearance
```

**How it works:**
1. Opponent possession detected when ball is in our half and we are not the lead attacker
2. Three levels based on distance to ball:
   - Near (ballRange < defensive_steal_range): Chase and steal -> kick to sideline
   - Mid (ballRange < 2x steal_range): Roll dice against risk_tolerance -> steal or defend
   - Far (ballRange >= 2x steal_range): Position defensively between ball and goal
3. Clearance kicks use calcClearDir() which aims at sideline, not goal
4. All original offensive behaviors remain unchanged

**Testing:**
```
1. Set enable_striker_defense: true
2. Place ball in your half, opponent robot near ball, your robot 1-2m away
3. Your robot should chase ball, steal it, and kick to sideline
4. Increase defensive_risk_tolerance to 1.0 for aggressive steals
5. Decrease to 0.0 for safe clearances only
```

### Possession Detection (v1.2.1)

**New params:**
```yaml
possession_margin: 0.25            # Distance margin (m) for determining possession
possession_hysteresis_secs: 0.3    # Time (s) state must hold before switching
attack_protection_dist: 0.5        # If our attacker is within this dist, keep attacking
```

**5-state machine:**
- OUR_POSSESSION: attacker is close + ball moving toward their goal
- OPP_POSSESSION: opponent clearly closer + ball moving toward our goal (held for 0.3s)
- CONTESTED: both teams near ball, no clear owner
- FREE_BALL: no one near ball
- DANGER: ball moving fast toward our goal with no defender
## Reverting

To disable any feature, set its `enable_*` param to `false` in config.yaml. No code changes needed.



