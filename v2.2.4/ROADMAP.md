# Booster RoboCup Patch — Roadmap

## Completed

| Version | Date | What |
|---|---|---|
| v1.0 | 2026-05-25 | Initial patch — parameter tuning, leg selection, kick power adjustment |
| v1.1 | 2026-05-25 | Free-kick power shot, quick shot, deflection shot |
| v1.2 | 2026-05-26 | Striker defense system (steal/clear/defend) |
| v1.2.1 | 2026-05-26 | 5-state possession detection, ball velocity, hysteresis |
| v1.2.2 | 2026-05-28 | Code cleanup, defense restructure, 15 bug fixes from review |
| v1.2.4 | 2026-05-28 | Fixed SIGABRT crash (broken Script node in freekick XML), duplicate Kick fix |
| v1.3 | 2026-05-28 | **Goalie overhaul:** ShotDetector, DivingSave, QuickClear, ImprovedGoaliePosition |

## v1.3.1 — Visual Kick/Defend Revival

**Status:** ⏳ Waiting for v1.3 hardware testing

Booster stripped the goalie's visual defend code before open-sourcing but left the RL model (api 2038) in the public SDK. We revive it.

| Item | Effort | Description |
|---|---|---|
| Goalie visual defend | ~30 lines | Fix `GoalieDecide::tick()` dead branch, add `RLVisionKick` to goalie tree |
| Striker visual zone expand | ~10 lines | Make visual kick zone configurable |
| Scripted kick → RL fallback | ~5 lines XML | Chain `RLVisionKick` after normal `Kick` as fallback |

**Details:** `visual-kick-brainstorm.md` in workspace.

---

## v1.4 — Set Piece Strategies

**Status:** 🔮 Planned

Currently all set pieces map to generic `FREE_KICK`. `realGameSubState` already tracks the actual type.

| Set Piece | Attack | Defend |
|---|---|---|
| Corner kick | 2 in box, 1 short, 1 back | Man-mark posts, clear sideline |
| Goal kick | Spread formation, target receiver | Push up, press |
| Penalty kick | Aim corners | Dive one side |
| Throw-in | Short pass, resume | Mark receivers |

**Details:** `goalie-brainstorm-v1.3.md` section 2.

---

## v1.5 — Deliberate Passing

**Status:** 🔮 Planned

Multi-robot coordination: deliberately pass to teammates instead of always kicking toward goal.

| Item | Description |
|---|---|
| Pass decision | New BT decision `"pass"` when teammate has better angle |
| Pass target | Use `calcKickDir` variant targeting best teammate |
| Receiver awareness | Teammate knows pass is coming via comms message flag |
| Dribbling | Controlled ball movement using `crabWalk` at low speed |

---

## v1.6 — Game State Awareness

**Status:** 🔮 Planned

Play the score and clock.

| Item | Description |
|---|---|
| Desperation attack | Losing late → all-out, goalie pushes up, max power |
| Control mode | Winning comfortably → possession priority, pass back |
| Time wasting | Leading near end → hold corners, pass to goalie |
| Kickoff set plays | Scripted plays: "Wide Split", "Rush" |

---

## Future Ideas (Unscheduled)

### Position-Based Role System (v2.0 candidate)

Currently only 2 roles: `striker` and `goal_keeper`. Real 5v5 football has distinct positions with different responsibilities.

```yaml
game:
  player_role: "CB"  # instead of "striker"/"goal_keeper"
  # Available roles: CB, LB, RB, CDM, CAM, ST, LW, RW, GK
```

**Role definitions:**

| Role | Primary Job | Attack Zone | Defend Zone | Shoot? | Pass First? |
|---|---|---|---|---|---|
| **GK** | Save shots, clear ball | Never leaves box | Goal area | No | Always clear |
| **CB** | Last line, block shots | Own half only | Penalty area | Rarely | Yes → ST/CAM |
| **LB/RB** | Cover flanks, support | Wing, own half | Flank defense | From wing only | Yes → CAM/ST |
| **CDM** | Press ball, intercept | Midfield | Up to own box | From distance | Yes → ST/CAM/LW/RW |
| **CAM** | Create chances, through balls | Opponent half | Press high | Often | Yes if blocked |
| **ST** | Score goals | Anywhere forward | Press CB | Always | Only if impossible to shoot |
| **LW/RW** | Wide play, cross | Wings, deep | Track back | Cut inside | Cross to ST |

**Role-specific params:**

```yaml
strategy:
  roles:
    CB:
      aggressiveness: 0.3          # 0.0=stay back, 1.0=press hard
      shoot_willingness: 0.1       # 0.0=never shoot, 1.0=always
      pass_priority: 0.9           # likelihood to pass before shooting
      max_forward_position: -3.0   # don't cross this field X coordinate
      chase_range: 2.0             # max distance to chase ball
      
    ST:
      aggressiveness: 0.9
      shoot_willingness: 0.9
      pass_priority: 0.2
      max_forward_position: 7.0
      chase_range: 5.0
      
    CAM:
      aggressiveness: 0.7
      shoot_willingness: 0.5
      pass_priority: 0.7           # looks to pass first, shoots if open
      max_forward_position: 5.0
      chase_range: 4.0
```

**Implementation approach:**
- Replace binary `striker`/`goal_keeper` checks with a `PlayerRole` struct
- Each role has a `RoleProfile` with default params (overridable in config)
- `StrikerDecide` becomes `PlayerDecide` — reads profile to weight decisions
- Existing striker logic maps to ST/CAM, goalie logic maps to GK
- New roles get behavior by composing existing nodes with different params
- Pass-priority roles (CB, LB, RB, CDM) trigger `"pass"` decision before `"kick"`

**Effort:** ~400 lines across config, brain_data, brain_tree, behavior XML. This is a v2.0-level change because it touches the fundamental decision architecture.

---

| Idea | Category | Effort |
|---|---|---|
| Opponent behavior tracking | Vision | High — track individual opponents over time |
| Localization confidence model | Stability | Medium — fallback when localization degrades |
| Dead code cleanup | Maintenance | Low — delete 10 stub nodes |
| Formation defense for 5v5 | Tactics | High — CB/LB/RB/CDM roles |
| Predictive squat (goalie) | Goalkeeping | Medium — pre-squat based on ball predictor |
| Goalie quick clear after save | Goalkeeping | ✅ Done in v1.3 |
| Ball prediction → goalie feed | Goalkeeping | ✅ Done in v1.3 (ImprovedGoaliePosition) |
| Opponent-aware angle coverage | Goalkeeping | Medium — cover shot angles, not ball position |
| Score/time awareness | Strategy | Medium — adjust play style dynamically |
| RL-assisted kick selection | Kicking | Blocked — needs firmware changes |
| Side-of-field visual kick | Kicking | Medium — wing zone trigger |

---

## Testing Notes

- All v1.3 goalie features need hardware validation (ShotDetector, DivingSave, QuickClear)
- Multi-robot coordination (cooperation, role switching) only testable with 2+ K1 robots
- Visual kick/defend (api 2038) likely works but was never tested on goalie
- Set piece strategies need GameController in PLAY+FREE_KICK state
