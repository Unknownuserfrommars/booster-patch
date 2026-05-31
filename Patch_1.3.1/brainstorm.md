

## Defence System Analysis & Proposals

### Current State

**Goalie (goal_keeper):**
- Two modes: `attack` (active) and `guard` (passive)
- `GoalieDecide` decides: find ball, retreat to goal, chase ball, kick, or adjust
- `GoToGoalBlockingPosition` calculates blocking position using ball trajectory projection
- Squat block activates when ball is within 0.9m (`squat_dist`)
- Squat direction: left/right/center based on ball lateral offset
- `use_move_block: false` — disabled. `enable_auto_visual_defend: false` — disabled

**Striker defending:**
- When ball is in own half, strikers use `GoToGoalBlockingPosition` to drop back
- `ball_out` triggers: `GoBackInField` — just returns to field boundary
- `calcBlockLineY` in `Assist` node exists but is never called (dead code)
- Role switching: striker/goalie swap when cost-to-ball threshold is crossed

### Problems I See

1. **Goalie predicts ball using ratio** — `y = ballY * distToGoalline / (ballX + fieldLength/2)`. Linear projection only, no velocity or kick direction considered.

2. **Squat block is purely reactive** — only triggers at 0.9m. Too late for hard shots.

3. **`use_move_block` is disabled**, `calcBlockLineY` is dead lambda — unfinished features that would help.

4. **No opponent tracking** — defence ignores opponent positions entirely.

5. **Ball-out recovery is basic** — just `GoBackInField`, no strategic repositioning.

6. **No pass interception** — defence doesn't cut passing lanes.

7. **No formation** — 3 non-goalie robots have no defined defensive roles.

### Proposed Improvements

**A. Goalie aggressiveness (low effort, high impact)**
New param `goalie_aggressiveness: 0.5` (0.0=stay on line, 1.0=charge ball)
- 0.0: guard mode, stays on goal line
- 0.5: positions at penalty area edge
- 1.0: actively chases ball outside the box
- Reuses existing `GoToGoalBlockingPosition` with dynamic `dist_to_goalline`

**B. Enable move_block intercept (medium effort)**
Wire up the dead `calcBlockLineY` code:
- When opponent has the ball, move to block the line between opponent and own goal
- Use `calcBlockLineY` to find the intercept point on the goal line
- New param `enable_move_block_intercept: false`
- Integrate into `Assist::tick()` or create new `Intercept` node

**C. Opponent-aware positioning (medium effort)**
Extend `GoToGoalBlockingPosition` to consider opponent positions:
- Track closest opponent to ball (primary threat)
- Position goalie to cover the angle between ball and that opponent
- New param `opponent_aware_defence: false`
- Uses existing detection model (already detects `Person`, `Opponent` classes)

**D. Goalie anticipation from ball predictor (medium effort)**
Feed ball_predictor output into goalie positioning:
- If predicted trajectory hits goal -> pre-position there
- If predicted trajectory misses -> stay central (don't dive unnecessarily)
- Reuses existing `ball_predictor.step_interval` and `step_cnt` config
- New param `enable_predictive_goalie: false`

**E. Quick clear after save (low effort)**
After goalie blocks and squats up, immediately kick ball away:
- Instead of just standing up, add a `Kick` action after squat
- Kick to sideline or to best-positioned teammate
- New param `enable_quick_clear: false`
- Simple: add a `Kick` node in the behavior tree after the squat sequence

**F. Formation defence for 5v5 (high effort)**
Define defensive positions for non-goalie robots:
- CB (centre back): stays central, covers goal area
- LB/RB (left/right back): covers flanks
- CDM (defensive mid): presses ball carrier
- New param `defensive_formation: "2-1-1"` with options like "3-0-1", "1-2-1"
- Uses existing `Cooperation.ball_control_cost_threshold` for role assignment

**G. Smart ball-out repositioning (low effort)**
Instead of generic `GoBackInField`:
- If ball went out near opponent goal: keep strikers forward
- If ball went out near own goal: all robots drop back
- New param `smart_reposition: false`

### Priority

| # | Improvement | Effort | Impact |
|---|---|---|---|
| A | Goalie aggressiveness | Low | High |
| B | Move block intercept | Medium | High |
| C | Opponent-aware positioning | Medium | High |
| D | Goalie anticipation | Medium | Medium |
| E | Quick clear after save | Low | Medium |
| G | Smart ball-out repositioning | Low | Low |
| F | Formation defence | High | High |


### Non-Goalie Defense Analysis

**Short answer: there is NO defense algorithm for non-goalie positions.**

Here is everything that exists:

| Behavior | Actual Purpose | Is it defense? |
|---|---|---|
| ball_out -> GoBackInField | Return to field after ball goes out | Barely |
| decision == assist -> Assist | Position to receive a pass | No - offensive support |
| role_switch | Striker becomes goalie | No - just swaps roles |
| tmMyCostRank positioning | Ranks by distance to ball | No - offense-oriented |
| calcBlockLineY (dead code) | Was supposed to block lines | Yes - but never called |

The Assist node (closest thing to defense) positions for OFFENSE support, not defense.
When the OPPONENT has the ball, there is zero defensive behavior for non-goalies.

### How the existing system helps

tmMyCostRank already ranks robots by distance to ball. Repurpose for defense:
- Rank 0 (closest) = press the opponent ball carrier
- Rank 1 (second) = cover passing lane / intercept
- Rank 2+ (far) = drop back to defensive positions

### Proposed: enable_striker_defense

A single config param that repurposes Assist/Chase when opponent has the ball.

New config params (all default false/off):

  strategy:
    enable_striker_defense: false       # Master switch
    striker_defense_aggressiveness: 0.5  # 0.0=drop deep, 1.0=press hard
    cover_passing_lanes: false           # Rank 1 intercepts passes
    defensive_clearance: false           # Kick long after gaining possession

Defensive roles by rank:
- Rank 0: Chase opponent ball carrier, stay between them and goal
- Rank 1: Position between ball and own goal, block pass/shoot paths
- Rank 2+: Drop to penalty area edge, cover goal

Changes needed:
1. Add params to config.yaml
2. In StrikerDecide: when opponent has ball + defense enabled, return defend decision
3. Add Defend BT node or reuse Assist with defensive params
4. The existing tmMyCostRank handles rank assignment automatically

This gives 4 robots defined roles in 5v5: 1 goalie + 1 presser + 1 cover + 1 deep defender.
