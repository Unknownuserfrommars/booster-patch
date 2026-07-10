# 🦀 Team Communication Signal Protocol — Patch 2.2 Proposal

> **Author:** Claw  
> **Date:** 2026-06-25  
> **Target:** Replace the primitive 2-signal `cmd` system with a structured protocol for 3v3/5v5 coordination.

---

## The Problem

Right now, the `cmd` field in `TeamCommunicationMsg` encodes exactly **2 signals**:

| `cmd` Value | Meaning |
|---|---|
| `0` | Nothing |
| `100` | "I want ball control, others assist" |
| `10+N` | "Goalie wants player N to replace me as goalie" |

That's it. For a 5v5 robot soccer team, that's like a basketball team that can only say "pass" and "switch." No formation calls, no danger alerts, no passing coordination, no set piece orchestration.

The existing positional-encoding trick (hundreds digit = meaning L1, tens digit = meaning L2, units digit = parameter) is clever but maxes out at 3 layers and ~10 values each. We need a system that scales.

---

## Design Philosophy

**Like C++ errno codes, but for team tactics.** Three design principles:

1. **Categorical hierarchy** — Signal digits encode category → subcategory → detail, so robots can react at any level of specificity they understand
2. **Backwards compatible** — `0 = nothing`, `1xx = I'm taking lead` keeps existing behavior
3. **Stateless + idempotent** — Every signal is a complete instruction; no "state machine across messages" needed. A receiving robot who just woke up can read it and act.

---

## The Protocol: 4-Digit Signal Codes

```
X Y Z W
│ │ │ └─ Parameter (0-9): player ID, zone index, urgency level
│ │ └─── Sub-signal (0-9): variant within the category
│ └───── Category (0-9): major signal category
└─────── Reserved for team/role flags (0-9)
```

### Signal Categories

| X (Hundreds) | Category | Like C++ Signal… |
|---|---|---|
| `0xxx` | **No-op / Clear** | `0` — success, nothing to report |
| `1xxx` | **Possession & Lead** | `SIGUSR1` — "I'm doing this now" |
| `2xxx` | **Passing & Assists** | `SIGIO` — data transfer inbound |
| `3xxx` | **Defensive Coordination** | `SIGALRM` — threat detected |
| `4xxx` | **Set Piece Orchestration** | `SIGTRAP` — planned sequence |
| `5xxx` | **Formation & Positioning** | `SIGWINCH` — reshape the field layout |
| `6xxx` | **Status & Alerts** | `SIGCHLD` — state change report |
| `7xxx` | **Role Management** | `SIGUSR2` — role change request |
| `8xxx` | **Urgent / Emergency** | `SIGABRT` — abort current action |
| `9xxx` | **Debug / Custom** | `SIGSTKFLT` — developer-only |

---

## Full Signal Catalog

### 0xxx — No-op / Standby

| Code | Signal | Meaning |
|---|---|---|
| `0000` | `SIG_NONE` | Nothing. Default state. |
| `0001` | `SIG_ACK` | Acknowledged previous command (opt-in) |
| `0002` | `SIG_STANDBY` | I'm alive but not participating (penalty box, sub) |

### 1xxx — Possession & Lead Control

| Code | Signal | Meaning | Old Equivalent |
|---|---|---|---|
| `1100` | `SIG_TAKE_LEAD` | I'm taking ball control, everyone else assist | `cmd == 100` |
| `1101` | `SIG_HOLD_LEAD` | I still have control, stay in position |
| `1200` | `SIG_RELEASE_LEAD` | I lost the ball / gave up — someone else take it |
| `130N` | `SIG_REQUEST_BALL` | I want the ball! Priority N (0=low, 9=high) |

**New behavior:** `SIG_REQUEST_BALL` lets a striker *ask* for the ball without superseding the current leader. The leader can factor this into pass decisions.

### 2xxx — Passing & Assists

| Code | Signal | Meaning |
|---|---|---|
| `210N` | `SIG_PASS_TO_ME` | Pass to player N (me). I'm open. |
| `211N` | `SIG_PASS_TO_PLAYER` | Everyone: pass to player N |
| `220N` | `SIG_DOING_PASS` | I'm about to kick toward player N — heads up |
| `230N` | `SIG_DOING_CROSS` | I'm crossing from the wing — crash the box! Priority N |
| `240N` | `SIG_ASSIST_READY` | I'm positioned for a pass at zone N |
| `250N` | `SIG_THROUGH_BALL` | I'm sending a through ball — run onto it, player N |

**Game-changer:** Currently, passing is entirely implicit (robot just kicks toward goal). These signals make passing a deliberate team action. `SIG_DOING_PASS` tells the receiver to stop chasing and position for reception.

### 3xxx — Defensive Coordination

| Code | Signal | Meaning |
|---|---|---|
| `310N` | `SIG_DANGER` | Threat level N (0=low, 9=ball flying at our goal) |
| `311N` | `SIG_OPPONENT_IN_ZONE` | Opponent detected in zone N, need coverage |
| `320N` | `SIG_COVER_PLAYER` | Player N: cover opponent number N |
| `321N` | `SIG_COVER_ZONE` | Player N: cover defensive zone N |
| `3300` | `SIG_PRESS` | All strikers: press the ball carrier! |
| `3301` | `SIG_FALL_BACK` | All: retreat to own half |
| `340N` | `SIG_BLOCK_SHOT` | Shot incoming from angle zone N — block |
| `3500` | `SIG_CLEAR` | Clear the ball — no fancy play, just get it out |

### 4xxx — Set Piece Orchestration

| Code | Signal | Meaning |
|---|---|---|
| `410N` | `SIG_FREEKICK_SETUP` | Free kick starting. Type N: 0=direct, 1=indirect, 2=corner |
| `411N` | `SIG_FREEKICK_EXECUTE` | Execute free kick now. Target zone N. |
| `420N` | `SIG_CORNER_SETUP` | Corner kick. Player N takes it. |
| `421N` | `SIG_CORNER_PLAY_N` | Run corner play #N (0=far post, 1=near post, 2=short, 3=crowd) |
| `4300` | `SIG_PENALTY_SETUP` | Penalty kick. Designated taker, others stay back. |
| `440N` | `SIG_KICKOFF_PLAY` | Run kickoff play #N (0=forward, 1=back pass, 2=wide split) |
| `450N` | `SIG_GOAL_KICK` | Goal kick setup. Distribute to zone N. |

**New behavior:** The `realGameSubState` field already distinguishes corner/goal/penalty kicks, but there's no in-team coordination. These signals let the designated kicker orchestrate everyone else's positioning.

### 5xxx — Formation & Positioning

| Code | Signal | Meaning |
|---|---|---|
| `510N` | `SIG_FORMATION` | Switch to formation N (0=2-3-0, 1=3-2-0, 2=1-3-1, 3=4-1-0) |
| `520N` | `SIG_MOVE_TO_ZONE` | Player N: move to zone N on the field |
| `5210` | `SIG_SPREAD` | All: spread out, create space |
| `5220` | `SIG_COMPACT` | All: tighten formation |
| `530N` | `SIG_PUSH_UP` | Push defensive line to Y=N (field coordinate) |
| `5400` | `SIG_HOLD_POSITION` | Nobody advance beyond current positions |

**Field zones** for zone-based signals:
```
┌─────────────────────────────────────────┐
│  1       2       3       4       5      │  ← Their half
├─────────────────────────────────────────┤
│  6       7       8       9      10      │
├──────────────── ────────────────────────┤  ← Halfway line
│ 11      12      13      14      15      │
├─────────────────────────────────────────┤
│ 16      17      18      19      20      │  ← Our half
└─────────────────────────────────────────┘
```

### 6xxx — Status & Alerts

| Code | Signal | Meaning |
|---|---|---|
| `6100` | `SIG_BALL_LOST` | I've lost sight of the ball |
| `6110` | `SIG_BALL_FOUND` | I've reacquired the ball |
| `6200` | `SIG_STUCK` | I'm stuck / can't move. Help or avoid me. |
| `6210` | `SIG_UNSTUCK` | I'm free again |
| `6300` | `SIG_FALLEN` | I've fallen over |
| `6310` | `SIG_RECOVERED` | I've gotten up |
| `6400` | `SIG_LOW_BATTERY` | Battery below threshold — consider subbing |
| `6500` | `SIG_GOAL_SCORED` | We scored! (Can trigger celebration) |
| `6510` | `SIG_GOAL_CONCEDED` | They scored. Reset formation. |

### 7xxx — Role Management

| Code | Signal | Meaning | Old Equivalent |
|---|---|---|---|
| `710N` | `SIG_SWITCH_GOALIE` | Player N switch to goalie | `cmd > 10 && cmd < 20` |
| `711N` | `SIG_SWITCH_STRIKER` | Player N switch to striker |
| `712N` | `SIG_SWITCH_ROLE` | Player N switch to role N (N from role enum) |
| `7200` | `SIG_NEED_SUBSTITUTE` | I need to be subbed out |
| `7300` | `SIG_ROLE_CONFIRM` | Role switch confirmed |

**New behavior:** The current system only allows goalie→striker switching. This extends to full role management including midfield/defense roles from the ROADMAP v2.0 plan.

### 8xxx — Urgent / Emergency

| Code | Signal | Meaning |
|---|---|---|
| `8100` | `SIG_ABORT` | Abort current play immediately |
| `8200` | `SIG_BALL_GOING_IN` | Ball is heading into OUR goal — GOALIE ALERT |
| `8300` | `SIG_OPPONENT_BREAKAWAY` | Opponent has breakaway — all defenders retreat |
| `8400` | `SIG_COLLISION_IMMINENT` | About to hit a teammate — avoid |
| `8500` | `SIG_OUT_OF_BOUNDS` | Ball going out — prepare for throw-in |

### 9xxx — Debug / Developer

| Code | Signal | Meaning |
|---|---|---|
| `9100` | `SIG_TEST` | Test signal — ignore |
| `9200` | `SIG_LOG_MARK` | Insert a marker in the telemetry log |
| `9300` | `SIG_ENTER_MANUAL` | Enter manual/debug mode |
| `9400` | `SIG_EXIT_MANUAL` | Exit manual/debug mode |

---

## Implementation Plan

### Phase 1: Signal Definitions (header-only, ~50 lines)

```cpp
// team_signals.h — new file

namespace TeamSignal {
    // Category masks
    constexpr int CAT_MASK       = 0xF000;
    constexpr int SUBCAT_MASK    = 0x0F00;
    constexpr int PARAM_MASK     = 0x000F;
    
    // Category extractors
    inline int category(int signal)   { return (signal & CAT_MASK) >> 12; }
    inline int subSignal(int signal)  { return (signal & SUBCAT_MASK) >> 8; }
    inline int param(int signal)      { return signal & PARAM_MASK; }
    inline int makeSignal(int cat, int sub, int p) { return (cat << 12) | (sub << 8) | p; }

    // Category 1: Possession
    constexpr int TAKE_LEAD     = 0x1100;
    constexpr int HOLD_LEAD     = 0x1101;
    constexpr int RELEASE_LEAD  = 0x1200;
    inline int REQUEST_BALL(int prio) { return 0x1300 | (prio & 0xF); }

    // Category 2: Passing
    inline int PASS_TO_ME(int myId)       { return 0x2100 | (myId & 0xF); }
    inline int PASS_TO_PLAYER(int id)      { return 0x2110 | (id & 0xF); }
    inline int DOING_PASS(int targetId)    { return 0x2200 | (targetId & 0xF); }
    inline int DOING_CROSS(int prio)       { return 0x2300 | (prio & 0xF); }
    inline int ASSIST_READY(int zone)      { return 0x2400 | (zone & 0xF); }
    inline int THROUGH_BALL(int runnerId)  { return 0x2500 | (runnerId & 0xF); }

    // Category 3: Defense
    inline int DANGER(int level)           { return 0x3100 | (level & 0xF); }
    inline int OPPONENT_IN_ZONE(int zone)  { return 0x3110 | (zone & 0xF); }
    inline int COVER_PLAYER(int id)        { return 0x3200 | (id & 0xF); }
    inline int COVER_ZONE(int zone)        { return 0x3210 | (zone & 0xF); }
    constexpr int PRESS           = 0x3300;
    constexpr int FALL_BACK       = 0x3301;
    inline int BLOCK_SHOT(int zone)        { return 0x3400 | (zone & 0xF); }
    constexpr int CLEAR           = 0x3500;

    // Category 4: Set Pieces
    inline int FREEKICK_SETUP(int type)     { return 0x4100 | (type & 0xF); }
    inline int FREEKICK_EXECUTE(int zone)   { return 0x4110 | (zone & 0xF); }
    inline int CORNER_PLAY(int playN)       { return 0x4210 | (playN & 0xF); }
    inline int KICKOFF_PLAY(int playN)      { return 0x4400 | (playN & 0xF); }
    inline int GOAL_KICK_ZONE(int zone)     { return 0x4500 | (zone & 0xF); }

    // Category 5: Formation
    inline int FORMATION(int formN)         { return 0x5100 | (formN & 0xF); }
    inline int MOVE_TO_ZONE(int playerId, int zone) 
        { return 0x5200 | (playerId & 0xF); } // zone in extra field
    constexpr int SPREAD          = 0x5210;
    constexpr int COMPACT         = 0x5220;
    constexpr int HOLD_POSITION   = 0x5400;

    // Category 6: Status
    constexpr int BALL_LOST       = 0x6100;
    constexpr int BALL_FOUND      = 0x6110;
    constexpr int STUCK           = 0x6200;
    constexpr int FALLEN          = 0x6300;
    constexpr int RECOVERED       = 0x6310;
    constexpr int GOAL_SCORED     = 0x6500;
    constexpr int GOAL_CONCEDED   = 0x6510;

    // Category 7: Role Mgmt
    inline int SWITCH_GOALIE(int newId)    { return 0x7100 | (newId & 0xF); }
    inline int SWITCH_STRIKER(int newId)   { return 0x7110 | (newId & 0xF); }
    inline int NEED_SUBSTITUTE()           { return 0x7200; }

    // Category 8: Emergency
    constexpr int ABORT           = 0x8100;
    constexpr int BALL_GOING_IN   = 0x8200;
    constexpr int BREAKAWAY       = 0x8300;
    constexpr int COLLISION       = 0x8400;
}
```

### Phase 2: Receiver — Signal Handler (~80 lines in brain.cpp)

Replace the current `cmd` handling block (lines 658-680 in brain.cpp):

```cpp
void Brain::handleReceivedSignal(int signal) {
    using namespace TeamSignal;
    int cat = category(signal);
    
    switch (cat) {
        case 0: break; // No-op
        
        case 1: // Possession
            if (signal == TAKE_LEAD || signal == HOLD_LEAD) {
                data->tmImLead = false;
                tree->setEntry<bool>("is_lead", false);
            } else if (signal == RELEASE_LEAD) {
                // Re-evaluate lead (next tick will recalculate)
                data->tmImLead = true; // tentative
            } else if ((signal & 0xFF00) == 0x1300) {
                // REQUEST_BALL — log it, let leader decide
                int requesterId = param(signal);
                log_(format("player %d requests ball (prio %d)", requesterId, requesterId));
            }
            break;
            
        case 2: // Passing
            if ((signal & 0xFF00) == 0x2100 || (signal & 0xFF00) == 0x2110) {
                // Someone wants a pass — if I'm lead, consider it
                data->tmPassRequested = true;
                data->tmPassTargetId = param(signal);
            } else if ((signal & 0xFF00) == 0x2200) {
                // Teammate is passing to me — prepare to receive
                data->tmExpectingPass = true;
                data->tmPassFromId = param(signal);
            }
            break;
            
        case 3: // Defense
            if ((signal & 0xFF00) == 0x3100) {
                data->tmDangerLevel = param(signal);
                if (data->tmDangerLevel >= 7) {
                    tree->setEntry<bool>("is_lead", false); // fall back
                }
            } else if (signal == PRESS) {
                data->tmDefensiveMode = "press";
            } else if (signal == FALL_BACK) {
                data->tmDefensiveMode = "retreat";
            } else if (signal == CLEAR) {
                data->isClearance = true;
                data->kickSubType = 4;
            }
            break;
            
        case 4: // Set Pieces
            data->tmSetPieceSignal = signal;
            // StrikerDecide reads this to choose set piece behavior
            break;
            
        case 5: // Formation
            if ((signal & 0xFF00) == 0x5100) {
                data->tmFormation = param(signal);
            } else if (signal == SPREAD || signal == COMPACT) {
                data->tmFormationAdjust = (signal == SPREAD) ? "spread" : "compact";
            }
            break;
            
        case 6: // Status
            if (signal == BALL_LOST) {
                data->tmBallLostBy[param(signal)] = true;
            } else if (signal == FALLEN) {
                data->tmFallenPlayers[param(signal)] = true;
            }
            break;
            
        case 7: // Role Mgmt
            if ((signal & 0xFF00) == 0x7100) {
                int newGoalieId = param(signal);
                if (newGoalieId == config->playerId) {
                    tree->setEntry<string>("player_role", "goal_keeper");
                    speak("i become goalie", true);
                }
            }
            break;
            
        case 8: // Emergency
            if (signal == ABORT) {
                // Cancel current action, return to safe state
                data->tmImLead = false;
                brain->client->setVelocity(0, 0, 0);
            } else if (signal == BALL_GOING_IN) {
                data->tmDangerLevel = 9;
            }
            break;
    }
}
```

### Phase 3: New brain_data fields (~15 lines)

```cpp
// brain_data.h additions
int tmDangerLevel = 0;
string tmDefensiveMode = "";
int tmFormation = 0;
string tmFormationAdjust = "";
bool tmPassRequested = false;
int tmPassTargetId = -1;
bool tmExpectingPass = false;
int tmPassFromId = -1;
int tmSetPieceSignal = 0;
bool tmBallLostBy[HL_MAX_NUM_PLAYERS] = {false};
bool tmFallenPlayers[HL_MAX_NUM_PLAYERS] = {false};
```

### Phase 4: Sender — Decision node signals (~30 lines in StrikerDecide)

Add signal-sending at key decision points in `StrikerDecide::tick()`:

```cpp
// When entering defense mode:
if (newDecision == "defend") {
    brain->data->tmMyCmd = TeamSignal::DANGER(5);
    brain->data->tmCmdId++;
}

// When about to pass to a teammate:
if (calcPassTargetId >= 0) {
    brain->data->tmMyCmd = TeamSignal::DOING_PASS(calcPassTargetId);
    brain->data->tmCmdId++;
}

// When free kick is starting:
if (gc_game_sub_state == "FREE_KICK") {
    brain->data->tmMyCmd = TeamSignal::FREEKICK_SETUP(0);
    brain->data->tmCmdId++;
}
```

### Phase 5: Behavior Tree integration

The `is_lead` blackboard entry and the `Assist` node already handle the lead/assist split. We extend this:

- **Assist node** reads `tmDefensiveMode`, `tmFormation`, `tmPassRequested` to position differently
- **New behavior tree nodes:** `HandleTeamSignal` (checks `tmReceivedCmd` and sets appropriate blackboard entries)
- **StrikerDecide** reads `tmExpectingPass`, `tmDangerLevel`, `tmSetPieceSignal` to override decisions

---

## Backwards Compatibility

The old signal values are preserved:
- `cmd == 0` → nothing (same)
- `cmd == 100` → mapped to `SIG_TAKE_LEAD (0x1100)` in the sender
- `cmd > 10 && cmd < 20` → mapped to `SIG_SWITCH_GOALIE(N)` in the sender

A robot running old firmware will see `cmd > 999` and fall into the `unknown cmd` branch (line 676), which is safe — it just logs and ignores. This means **mixed-firmware teams work during transition.**

### Migration path:
1. Deploy new firmware to 1 robot → it sends new 4-digit signals, old robots ignore them
2. Old robots still send `100` and `10+N` → new firmware handler maps them via the old branches
3. Once all robots are on new firmware → enable new signal handling via config flag `enable_extended_signals: true`

---

## Config Toggle

```yaml
# config.yaml
strategy:
  team_communication:
    enable_extended_signals: false   # flip to true once all robots updated
    signal_cooldown_ms: 2000         # min time between sending same signal
    danger_threshold_auto_retreat: 7 # DANGER level that triggers auto-retreat
```

---

## Why This Matters for 5v5

With 5 robots, the current binary lead/assist system breaks down. You need:
- **2 defenders** who need to know whether to press or fall back
- **1 midfielder** who needs to know when to crash the box vs hold position
- **2 strikers** who need to coordinate passing vs shooting
- **1 goalie** who needs to know shot direction and when to attack

This protocol gives every robot context about what the *team* is doing, not just what it sees itself.

---

## Effort Estimate

| Phase | Lines | Difficulty |
|---|---|---|
| 1. Signal definitions | ~50 | Trivial |
| 2. Receiver handler | ~80 | Easy |
| 3. Data fields | ~15 | Trivial |
| 4. Sender integration | ~30 | Medium (needs decision context) |
| 5. BT integration | ~50 | Medium |
| **Total** | **~225** | **2-3 evenings** |

The heavy lifting is Phase 4+5 — deciding *when* to send which signals. The protocol itself is skeleton code.

---

## Brainstorm Extras (Not in v2.2, Food for Thought)

### Idea: Signal Priority Queue
Instead of a single `cmd`, send a priority queue of 3 signals. The highest-priority active signal wins. E.g., `{SIG_DANGER(9), SIG_PASS_TO_ME(3), SIG_SPREAD}` — other robots see the danger first, then the pass request if danger clears.

### Idea: Echo/Relay for Mesh
If robot A sees something robot B can't (ball, opponent), A broadcasts it. B's vision might be blocked. The `ballLocationKnown` relay already does this for the ball — extend it to opponents.

### Idea: Time-to-Live (TTL) on Signals
Some signals expire (e.g., "I'm about to pass" is meaningless after 3 seconds). Add a TTL field or use `cmdId` increments to detect stale signals.

### Idea: Formation Auto-Selection
Instead of explicit `SIG_FORMATION` commands, let the lead robot auto-select formation based on game state and broadcast it. `winning + <2min → 4-1-0`, `losing + <2min → 1-3-1`.

---

*End proposal. No code has been modified — Patch_2.2 is a clean copy of v2.1 with only this doc added.*
