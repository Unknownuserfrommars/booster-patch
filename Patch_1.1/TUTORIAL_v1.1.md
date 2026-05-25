# Patch v1.1 — Tutorial: Using New Features

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
  quickshot_max_range: 1.2

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


### Deflection Shot (v1.1 update)

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

## Reverting

To disable any feature, set its `enable_*` param to `false` in config.yaml. No code changes needed.
