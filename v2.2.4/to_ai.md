# to_ai.md — Team Communication Signal Protocol: Implementation Guide

> **To:** ChatGPT Codex (Collaborator AI)  
> **From:** Claw (Project AI)  
> **Project:** Booster RoboCup — Patch 2.2  
> **Date:** 2026-06-25  
> **Status:** READY TO IMPLEMENT — All context provided below.

---

## 0. Collaboration Note

You and I are working together on the same robot soccer codebase. I've done the design and analysis; you're doing the implementation. I am not your competitor — I am your upstream. Everything in this document is meant to make your job easy. If something is unclear, flag it and I'll clarify. Do not feel you need to invent anything; the protocol is fully specified below.

---

## 1. What Is This Project?

**Booster** is a RoboCup SPL (Standard Platform League) robot soccer system. It runs on ROS 2 Humble, compiled with `colcon`. The robots are humanoid K1 bipeds. Games are 3v3 or 5v5.

**Key directories in Patch_2.2:**

```
Patch_2.2/
├── src/brain/              ← YOUR WORK IS HERE
│   ├── include/            ← Headers
│   │   ├── team_communication_msg.h   ← Message struct definition
│   │   ├── brain_communication.h      ← Communication class header
│   │   ├── brain_data.h              ← Runtime data (add fields here)
│   │   ├── brain.h                   ← Brain class (add handler declaration)
│   │   └── types.h                   ← Shared types (TMStatus struct)
│   ├── src/
│   │   ├── brain_communication.cpp   ← Communication implementation
│   │   ├── brain.cpp                 ← Main brain logic (add handler)
│   │   └── brain_tree.cpp            ← Behavior tree nodes (StrikerDecide, Assist)
│   └── behavior_trees/               ← XML behavior trees
│       └── subtrees/                 ← Sub-behavior trees
├── configs/
├── src/game_controller/
├── src/vision/
└── team-signals-proposal.md          ← The high-level proposal (read first)
```

**Build system:** ROS 2 `colcon`. `CMakeLists.txt` in each package. Build with:
```bash
cd Patch_2.2
colcon build --packages-select brain
```

**The `Brain` class** is the central decision-maker. It owns:
- `config` (BrainConfig) — YAML-configurable parameters
- `data` (BrainData) — runtime state
- `tree` (BrainTree) — BehaviorTree.CPP decision engine
- `communication` (BrainCommunication) — UDP comms to teammates

---

## 2. Current Team Communication (What Exists)

### 2.1 Message Structure

`src/brain/include/team_communication_msg.h`:

```cpp
struct TeamCommunicationMsg {
    int validation = VALIDATION_COMMUNICATION;  // 31202
    int communicationId;
    int teamId;
    int playerId;
    int playerRole;        // 1=striker, 2=goal_keeper
    bool isAlive;
    bool isLead;
    bool ballDetected;
    bool ballLocationKnown;
    double ballConfidence;
    double ballRange;
    double cost;
    Point ballPosToField;
    Pose2D robotPoseToField;
    double kickDir;
    double thetaRb;
    int cmdId;             // Incremented per-command
    int cmd;               // ⬅ THE FIELD WE'RE EXTENDING
};
```

This message is sent via UDP unicast every **100ms** to all discovered teammates (see `UNICAST_INTERVAL_MS` in `brain_communication.cpp`). Discovery happens via broadcast on port `20000 + teamId` every **1000ms**.

### 2.2 Current cmd Encoding

The `cmd` field currently encodes exactly 2 signals using positional digits:

| `cmd` Value | Meaning | Where Used |
|---|---|---|
| `0` | Nothing | Default |
| `100` | "I'm taking lead control, others assist" | `handleCooperation()` in brain.cpp |
| `10+N` | "Goalie says: player N, become the new goalie" | `handleCooperation()` in brain.cpp |

**`cmdId` semantics:** Every time a robot issues a new command, it increments `cmdId` by 1. Receivers compare incoming `cmdId` against their stored `tmCmdId` to detect new commands (don't re-process the same command).

### 2.3 How Commands Are Sent

Commands are set by writing to `brain->data->tmMyCmd` and incrementing `brain->data->tmCmdId`. The unicast thread picks these up automatically in `unicastCommunication()` (line ~158 in `brain_communication.cpp`):

```cpp
msg.cmd = brain->data->tmMyCmd;
msg.cmdId = brain->data->tmMyCmdId;
```

### 2.4 How Commands Are Received

In `spinCommunicationReceiver()` (line ~280 in `brain_communication.cpp`):

```cpp
// Check if we received a new command
if (msg.cmdId > brain->data->tmCmdId) {
    brain->data->tmCmdId = msg.cmdId;
    brain->data->tmReceivedCmd = msg.cmd;  // <-- processed in handleCooperation()
    brain->data->tmLastCmdChangeTime = brain->get_clock()->now();
}
```

Then in `handleCooperation()` (line ~658 in `brain.cpp`):

```cpp
auto cmd = data->tmReceivedCmd;
if (cmd != 0) {
    if (cmd == 100) {                        // Teammate wants lead
        data->tmImLead = false;
        tree->setEntry<bool>("is_lead", false);
    } else if (cmd > 10 && cmd < 20) {      // Goalie role switch
        int newGoalieId = cmd - 10;
        if (newGoalieId == selfId) {
            tree->setEntry<string>("player_role", "goal_keeper");
        }
    } else {
        log_(format("unknown cmd %d from teammate", cmd));  // <-- SAFE FALLBACK
    }
    data->tmReceivedCmd = 0;
}
```

**Key insight for backwards compatibility:** Unknown commands fall into the `else` branch and are safely ignored. This means old firmware robots will silently ignore our new signals. New firmware robots handle both old and new signals.

---

## 3. What We're Building

Replace the 2-signal system with a **structured 4-digit signal protocol**. Think Unix signals (`SIGUSR1`, `SIGALRM`, etc.) but for robot soccer tactics.

### 3.1 Protocol Encoding

```
0xXYZW  (hex) or X Y Z W (decimal digits)
 │││└── Parameter (0-9): player ID, zone index, priority level
 ││└─── Sub-signal (0-9): variant within category
 │└──── Category (0-9): major signal category
 └───── Zero-padding for 4-digit consistency
```

### 3.2 Full Signal Catalog

#### Category 1: Possession & Lead Control (1xxx / 0x1___)

| Hex | Decimal | Constant Name | Meaning | Sender | Receiver Behavior |
|---|---|---|---|---|---|
| `0x1100` | 4352 | `TAKE_LEAD` | I'm the ball controller now | Striker with ball | Set `is_lead=false`, enter assist |
| `0x1101` | 4353 | `HOLD_LEAD` | I still have control, stay put | Lead striker (refresh) | Same as TAKE_LEAD |
| `0x1200` | 4608 | `RELEASE_LEAD` | I lost/gave up control | Current leader | Recalculate lead (next tick) |
| `0x1300` | 4864 | `REQUEST_BALL` | I want the ball! +prio | Any non-lead striker | Leader notes it for pass decision |

`REQUEST_BALL` adds the requesting player's ID in the low nibble for priority:
- `0x1303` = player 3 requesting ball

#### Category 2: Passing & Assists (2xxx / 0x2___)

| Hex | Decimal | Constant Name | Meaning | Sender | Receiver Behavior |
|---|---|---|---|---|---|
| `0x210N` | 8448+N | `PASS_TO_ME` | I'm open, pass to me! | Open striker | If leader: consider pass to sender |
| `0x211N` | 8464+N | `PASS_TO_PLAYER` | Everyone: pass to player N | Any | Redirect decisions toward player N |
| `0x220N` | 8704+N | `DOING_PASS` | I'm kicking to player N now | Leader about to kick | Player N: prepare to receive |
| `0x230N` | 8960+N | `DOING_CROSS` | Crossing from wing, crash box | Wing player | Attackers: move toward goal |
| `0x240N` | 9216+N | `ASSIST_READY` | I'm at zone N for a pass | Support player | Leader: knows where help is |
| `0x250N` | 9472+N | `THROUGH_BALL` | Through ball to player N | Leader | Player N: run onto the ball |

#### Category 3: Defensive Coordination (3xxx / 0x3___)

| Hex | Decimal | Constant Name | Meaning | Sender | Receiver Behavior |
|---|---|---|---|---|---|
| `0x310N` | 12544+N | `DANGER` | Threat level N (0-9) | Any robot seeing danger | Scale: 0-3=aware, 4-6=defensive, 7-9=emergency retreat |
| `0x311N` | 12560+N | `OPPONENT_IN_ZONE` | Opponent in zone N | Any | Defenders: cover that zone |
| `0x320N` | 12800+N | `COVER_PLAYER` | Cover opponent player N | Any | Assigned defender: mark player N |
| `0x321N` | 12816+N | `COVER_ZONE` | Cover defensive zone N | Any | Assigned defender: move to zone N |
| `0x3300` | 13056 | `PRESS` | All strikers press! | Any (usually leader) | Aggressive chase, high speed |
| `0x3301` | 13057 | `FALL_BACK` | Everyone retreat to own half | Any (usually leader) | Return to defensive positions |
| `0x340N` | 13312+N | `BLOCK_SHOT` | Shot incoming from angle N | Goalie/defender | Move to block angle zone N |
| `0x3500` | 13568 | `CLEAR` | Just clear the ball, no fancy play | Leader under pressure | Set `isClearance=true`, use `calcClearDir()` |

#### Category 4: Set Piece Orchestration (4xxx / 0x4___)

| Hex | Decimal | Constant Name | Meaning | Sender | Receiver Behavior |
|---|---|---|---|---|---|
| `0x410N` | 16640+N | `FREEKICK_SETUP` | Free kick, type N | Designated kicker | Type: 0=direct, 1=indirect, 2=corner |
| `0x411N` | 16656+N | `FREEKICK_EXECUTE` | Execute now, target zone N | Designated kicker | Receivers: move to target zone |
| `0x421N` | 16912+N | `CORNER_PLAY` | Run corner play #N | Corner taker | Play: 0=far post, 1=near post, 2=short, 3=crowd box |
| `0x440N` | 17408+N | `KICKOFF_PLAY` | Kickoff play #N | Kickoff taker | Play: 0=forward, 1=back pass, 2=wide split |

#### Category 5: Formation & Positioning (5xxx / 0x5___)

| Hex | Decimal | Constant Name | Meaning | Sender | Receiver Behavior |
|---|---|---|---|---|---|
| `0x510N` | 20736+N | `FORMATION` | Switch to formation N | Captain/leader | Form: 0=2-3-0, 1=3-2-0, 2=1-3-1, 3=4-1-0 |
| `0x520N` | 20992+N | `MOVE_TO_ZONE` | Player N: go to your zone | Leader | Player N moves to designated zone |
| `0x5210` | 21008 | `SPREAD` | All: spread out wide | Leader | Increase spacing between robots |
| `0x5220` | 21024 | `COMPACT` | All: tighten formation | Leader | Decrease spacing |
| `0x530N` | 21248+N | `PUSH_UP` | Push line to Y=N | Leader | Defenders: advance to Y=N |
| `0x5400` | 21504 | `HOLD_POSITION` | Nobody advance | Leader | Stay at current positions |

**Field Zone Map** (for zone-based signals):

```
┌──────────────────────────────────────────┐  ← Their goal line
│  1        2        3        4        5   │
├──────────────────────────────────────────┤
│  6        7        8        9       10   │
├──────────────────────────────────────────┤  ← Halfway
│ 11       12       13       14       15   │
├──────────────────────────────────────────┤
│ 16       17       18       19       20   │  ← Our goal line
└──────────────────────────────────────────┘
```

#### Category 6: Status & Alerts (6xxx / 0x6___)

| Hex | Decimal | Constant Name | Meaning |
|---|---|---|---|
| `0x6100` | 24832 | `BALL_LOST` | I lost sight of the ball |
| `0x6110` | 24848 | `BALL_FOUND` | I reacquired the ball |
| `0x6200` | 25088 | `STUCK` | I'm stuck, help or avoid me |
| `0x6210` | 25104 | `UNSTUCK` | I'm free again |
| `0x6300` | 25344 | `FALLEN` | I fell over |
| `0x6310` | 25360 | `RECOVERED` | I got up |
| `0x6500` | 25856 | `GOAL_SCORED` | We scored! |
| `0x6510` | 25872 | `GOAL_CONCEDED` | They scored |

#### Category 7: Role Management (7xxx / 0x7___)

| Hex | Decimal | Constant Name | Meaning | Old Equivalent |
|---|---|---|---|---|
| `0x710N` | 28928+N | `SWITCH_GOALIE` | Player N → goalie | `cmd > 10 && cmd < 20` |
| `0x711N` | 28944+N | `SWITCH_STRIKER` | Player N → striker | *(new)* |
| `0x7200` | 29184 | `NEED_SUBSTITUTE` | I need a sub | *(new)* |

#### Category 8: Emergency (8xxx / 0x8___)

| Hex | Decimal | Constant Name | Meaning | Receiver Behavior |
|---|---|---|---|---|
| `0x8100` | 33024 | `ABORT` | Abort all current actions | Stop moving, return to safe state |
| `0x8200` | 33280 | `BALL_GOING_IN` | Ball heading into our goal | Goalie: emergency save mode |
| `0x8300` | 33536 | `BREAKAWAY` | Opponent breakaway | All defenders: sprint back |
| `0x8400` | 33792 | `COLLISION` | Collision imminent | Avoid indicated direction |

---

## 4. Implementation Steps (In Order)

### Step 1: Create `team_signals.h` — Signal Definitions

**File:** `src/brain/include/team_signals.h` (NEW FILE)

This is the canonical signal registry. Every constant goes here. Use hex notation for clarity.

```cpp
#pragma once

/**
 * @file team_signals.h
 * @brief Team communication signal protocol — structured 4-digit command codes.
 * 
 * Encoding: 0xXYZW → X=category, Y=sub-signal, ZW=parameter
 * Categories: 1=possession, 2=passing, 3=defense, 4=setpiece,
 *             5=formation, 6=status, 7=role, 8=emergency
 */

namespace TeamSignal {

// --- Bit masks for extracting fields ---
constexpr int CAT_MASK    = 0xF000;  // top nibble: category
constexpr int SUBCAT_MASK = 0x0F00;  // second nibble: sub-signal
constexpr int PARAM_MASK  = 0x00FF;  // low byte: parameter (allows 0-255)

inline int category(int signal)  { return (signal & CAT_MASK) >> 12; }
inline int subSignal(int signal) { return (signal & SUBCAT_MASK) >> 8; }
inline int param(int signal)     { return signal & PARAM_MASK; }

// ==================================================================
// Category 1: Possession & Lead Control (0x1___)
// ==================================================================
constexpr int TAKE_LEAD     = 0x1100;   // I'm taking ball control
constexpr int HOLD_LEAD     = 0x1101;   // I still have control (refresh)
constexpr int RELEASE_LEAD  = 0x1200;   // I lost/gave up control
constexpr int REQUEST_BALL  = 0x1300;   // I want the ball (OR with playerId)

// ==================================================================
// Category 2: Passing & Assists (0x2___)
// ==================================================================
constexpr int PASS_TO_ME     = 0x2100;  // Pass to me (OR with my playerId)
constexpr int PASS_TO_PLAYER = 0x2110;  // Pass to player N (OR with playerId)
constexpr int DOING_PASS     = 0x2200;  // I'm about to pass to player N
constexpr int DOING_CROSS    = 0x2300;  // I'm crossing from wing (OR with urgency)
constexpr int ASSIST_READY   = 0x2400;  // I'm ready at zone N for a pass
constexpr int THROUGH_BALL   = 0x2500;  // Through ball to player N

// ==================================================================
// Category 3: Defensive Coordination (0x3___)
// ==================================================================
constexpr int DANGER           = 0x3100;  // Threat level N (OR with level 0-9)
constexpr int OPPONENT_IN_ZONE = 0x3110;  // Opponent in zone N
constexpr int COVER_PLAYER     = 0x3200;  // Cover opponent player N
constexpr int COVER_ZONE       = 0x3210;  // Cover defensive zone N
constexpr int PRESS            = 0x3300;  // All strikers press!
constexpr int FALL_BACK        = 0x3301;  // Everyone retreat
constexpr int BLOCK_SHOT       = 0x3400;  // Shot incoming from angle N
constexpr int CLEAR            = 0x3500;  // Clear the ball

// ==================================================================
// Category 4: Set Piece Orchestration (0x4___)
// ==================================================================
constexpr int FREEKICK_SETUP    = 0x4100;  // Free kick, type N (0=direct,1=indirect,2=corner)
constexpr int FREEKICK_EXECUTE  = 0x4110;  // Execute now to zone N
constexpr int CORNER_PLAY       = 0x4210;  // Corner play #N (0=far,1=near,2=short,3=crowd)
constexpr int KICKOFF_PLAY      = 0x4400;  // Kickoff play #N

// ==================================================================
// Category 5: Formation & Positioning (0x5___)
// ==================================================================
constexpr int FORMATION       = 0x5100;  // Switch formation N (0=2-3-0,1=3-2-0,2=1-3-1,3=4-1-0)
constexpr int MOVE_TO_ZONE    = 0x5200;  // Player N: go to your zone
constexpr int SPREAD          = 0x5210;  // All: spread out
constexpr int COMPACT         = 0x5220;  // All: tighten
constexpr int PUSH_UP         = 0x5300;  // Push line to Y=N
constexpr int HOLD_POSITION   = 0x5400;  // Nobody advance

// ==================================================================
// Category 6: Status & Alerts (0x6___)
// ==================================================================
constexpr int BALL_LOST      = 0x6100;
constexpr int BALL_FOUND     = 0x6110;
constexpr int STUCK          = 0x6200;
constexpr int UNSTUCK        = 0x6210;
constexpr int FALLEN         = 0x6300;
constexpr int RECOVERED      = 0x6310;
constexpr int GOAL_SCORED    = 0x6500;
constexpr int GOAL_CONCEDED  = 0x6510;

// ==================================================================
// Category 7: Role Management (0x7___)
// ==================================================================
constexpr int SWITCH_GOALIE   = 0x7100;  // Player N becomes goalie (OR with playerId)
constexpr int SWITCH_STRIKER  = 0x7110;  // Player N becomes striker (OR with playerId)
constexpr int NEED_SUBSTITUTE = 0x7200;

// ==================================================================
// Category 8: Emergency (0x8___)
// ==================================================================
constexpr int ABORT          = 0x8100;
constexpr int BALL_GOING_IN  = 0x8200;
constexpr int BREAKAWAY      = 0x8300;
constexpr int COLLISION      = 0x8400;

} // namespace TeamSignal
```

**Note on hex vs decimal:** The proposal used decimal in some places, but hex is cleaner for bit manipulation. The message carries an `int` — hex or decimal doesn't matter on the wire. Use whichever reads better in the header. I recommend **hex constants** because they make the category/subcategory/param structure visually obvious: `0x3107` = category 3 (defense), sub 1 (danger), param 7 (level 7).

---

### Step 2: Add Data Fields to `brain_data.h`

**File:** `src/brain/include/brain_data.h`

**Location:** Add these fields inside the `BrainData` class, near the existing `tmStatus` and `tmMyCmd` fields (around line 129-145, near the `// 双机配合` comment block).

Add **after** the existing `tmMyCostRank` line and **before** the existing `tmImInVisualKick` line:

```cpp
    // --- NEW: Extended team communication signal data ---
    int tmDangerLevel = 0;              // 0-9, danger level from teammate signals
    string tmDefensiveMode = "";        // "press", "retreat", or "" (none)
    int tmFormation = 0;                // Active formation number (0-3)
    string tmFormationAdjust = "";      // "spread", "compact", or "" (none)
    bool tmPassRequested = false;       // A teammate is requesting a pass
    int tmPassTargetId = -1;            // Player ID being asked to receive
    bool tmExpectingPass = false;       // I should prepare to receive a pass
    int tmPassFromId = -1;              // Player ID who will pass to me
    int tmSetPieceSignal = 0;           // Last set piece orchestration signal
    bool tmBallLostBy[HL_MAX_NUM_PLAYERS] = {false};   // Which teammates lost ball
    bool tmFallenPlayers[HL_MAX_NUM_PLAYERS] = {false}; // Which teammates fell
    // --- END NEW ---
```

**How `HL_MAX_NUM_PLAYERS` works:** It's defined in `RoboCupGameControlData.h` and equals the max robots per team (likely 6 or 8). The `tmStatus` array already uses it the same way. Index by `playerId - 1`.

---

### Step 3: Add Signal Handler Declaration to `brain.h`

**File:** `src/brain/include/brain.h`

**Location:** In the public methods section, add after `handleCooperation()` declaration (around line 150-ish, look for `void handleCooperation();`).

Add:

```cpp
    // 处理扩展的队伍通讯信号 (Patch 2.2)
    void handleReceivedSignal(int signal);
```

Also add the include for the new header at the top of `brain.h`, near the other includes:

```cpp
#include "team_signals.h"   // Patch 2.2: extended team communication signals
```

---

### Step 4: Implement Signal Handler in `brain.cpp`

**File:** `src/brain/src/brain.cpp`

**Location:** Add the new function definition. A good place is right after `handleCooperation()` ends (around line 682, after `tree->setEntry<bool>("is_lead", data->tmImLead);`).

```cpp
/**
 * @brief Handle an extended team communication signal received from a teammate.
 * 
 * Called from handleCooperation() when tmReceivedCmd contains a 4-digit signal.
 * Maps signal categories to brain state changes.
 */
void Brain::handleReceivedSignal(int signal) {
    using namespace TeamSignal;
    auto log_ = [this](string msg) {
        this->log->setTimeNow();
        this->log->log("debug/handleSignal", rerun::TextLog(msg));
    };
    
    int cat = category(signal);
    int par = param(signal);
    
    log_(format("Received signal 0x%04X (cat=%d, sub=%d, param=%d)", 
                signal, cat, subSignal(signal), par));
    
    switch (cat) {
        
        // ---------------------------------------------------------------
        case 0: // No-op
            break;
        
        // ---------------------------------------------------------------
        case 1: { // Possession & Lead Control
            if (signal == TAKE_LEAD || signal == HOLD_LEAD) {
                data->tmImLead = false;
                tree->setEntry<bool>("is_lead", false);
                log_("Teammate took lead, I'm now assisting");
            } else if (signal == RELEASE_LEAD) {
                // Next tick's handleCooperation will recalculate
                log_("Teammate released lead, will recalculate");
            } else if ((signal & 0xFF00) == 0x1300) {
                // REQUEST_BALL — store for leader's pass decision
                data->tmPassRequested = true; 
                data->tmPassTargetId = 0; // requesting player IS the target
                log_(format("Player %d requests ball", par));
            }
            break;
        }
        
        // ---------------------------------------------------------------
        case 2: { // Passing & Assists
            if ((signal & 0xFF00) == 0x2100) {
                // PASS_TO_ME
                data->tmPassRequested = true;
                data->tmPassTargetId = par;
                log_(format("Player %d is open for a pass", par));
            } else if ((signal & 0xFF00) == 0x2110) {
                // PASS_TO_PLAYER
                data->tmPassTargetId = par;
                log_(format("Directed pass to player %d", par));
            } else if ((signal & 0xFF00) == 0x2200) {
                // DOING_PASS — I'm the target, prepare to receive
                data->tmExpectingPass = true;
                data->tmPassFromId = par;
                log_(format("Teammate passing to me (from player %d)", par));
            } else if ((signal & 0xFF00) == 0x2300) {
                // DOING_CROSS — crash the box
                log_(format("Cross incoming! urgency=%d", par));
                // This gets handled in StrikerDecide/Assist behavior
            } else if ((signal & 0xFF00) == 0x2400) {
                // ASSIST_READY at zone
                log_(format("Teammate ready for pass at zone %d", par));
            }
            break;
        }
        
        // ---------------------------------------------------------------
        case 3: { // Defensive Coordination
            if ((signal & 0xFF00) == 0x3100) {
                // DANGER level
                data->tmDangerLevel = par;
                log_(format("Danger level set to %d", par));
                if (par >= 7) {
                    // High danger: fall back, abandon attack
                    data->tmImLead = false;
                    tree->setEntry<bool>("is_lead", false);
                    data->tmDefensiveMode = "retreat";
                    log_("High danger — retreating");
                }
            } else if (signal == PRESS) {
                data->tmDefensiveMode = "press";
                log_("Defensive mode: press");
            } else if (signal == FALL_BACK) {
                data->tmDefensiveMode = "retreat";
                log_("Defensive mode: retreat");
            } else if (signal == CLEAR) {
                data->isClearance = true;
                data->kickSubType = 4;
                log_("Clearance signal received");
            } else if ((signal & 0xFF00) == 0x3400) {
                // BLOCK_SHOT from angle zone
                log_(format("Block shot from angle zone %d", par));
            }
            break;
        }
        
        // ---------------------------------------------------------------
        case 4: // Set Piece Orchestration
            data->tmSetPieceSignal = signal;
            log_(format("Set piece signal received: 0x%04X", signal));
            break;
        
        // ---------------------------------------------------------------
        case 5: // Formation & Positioning
            if ((signal & 0xFF00) == 0x5100) {
                data->tmFormation = par;
                log_(format("Switching to formation %d", par));
            } else if (signal == SPREAD) {
                data->tmFormationAdjust = "spread";
            } else if (signal == COMPACT) {
                data->tmFormationAdjust = "compact";
            }
            break;
        
        // ---------------------------------------------------------------
        case 6: // Status & Alerts
            if (signal == BALL_LOST) {
                if (par > 0 && par <= HL_MAX_NUM_PLAYERS) {
                    data->tmBallLostBy[par - 1] = true;
                }
            } else if (signal == FALLEN) {
                if (par > 0 && par <= HL_MAX_NUM_PLAYERS) {
                    data->tmFallenPlayers[par - 1] = true;
                }
            } else if (signal == RECOVERED) {
                if (par > 0 && par <= HL_MAX_NUM_PLAYERS) {
                    data->tmFallenPlayers[par - 1] = false;
                }
            } else if (signal == GOAL_SCORED) {
                log_("WE SCORED!");
                // Could trigger celebration behavior
            } else if (signal == GOAL_CONCEDED) {
                log_("They scored. Reset.");
                data->tmDefensiveMode = "retreat";
            }
            break;
        
        // ---------------------------------------------------------------
        case 7: { // Role Management
            if ((signal & 0xFF00) == 0x7100) {
                // SWITCH_GOALIE — player N becomes goalie
                int newGoalieId = par;
                if (newGoalieId == config->playerId) {
                    tree->setEntry<string>("player_role", "goal_keeper");
                    speak("i become goalie", true);
                    log_("I am now the goalie");
                } else {
                    log_(format("Player %d is now the goalie", newGoalieId));
                }
            } else if ((signal & 0xFF00) == 0x7110) {
                // SWITCH_STRIKER
                if (par == config->playerId) {
                    tree->setEntry<string>("player_role", "striker");
                    log_("I am now a striker");
                }
            }
            break;
        }
        
        // ---------------------------------------------------------------
        case 8: { // Emergency
            if (signal == ABORT) {
                log_("EMERGENCY ABORT received");
                data->tmImLead = false;
                tree->setEntry<bool>("is_lead", false);
                // Stop all movement
                client->setVelocity(0, 0, 0);
            } else if (signal == BALL_GOING_IN) {
                data->tmDangerLevel = 9;
                log_("BALL GOING INTO OUR GOAL!");
            } else if (signal == BREAKAWAY) {
                data->tmDangerLevel = 8;
                data->tmDefensiveMode = "retreat";
                log_("Opponent breakaway — retreat!");
            }
            break;
        }
        
        // ---------------------------------------------------------------
        default:
            log_(format("Unhandled signal category %d (signal=0x%04X)", cat, signal));
            break;
    }
}
```

---

### Step 5: Wire Into `handleCooperation()` — Replace Old cmd Handling

**File:** `src/brain/src/brain.cpp`

**Location:** Replace the existing command handling block (approximately lines 658-680) inside `handleCooperation()`.

**BEFORE (remove this):**
```cpp
    auto cmd = data->tmReceivedCmd;
    if (cmd != 0) {
        log_(format("received cmd %d from teammate", cmd));
        if (cmd == 100) { // 队友要控球
            data->tmImLead = false;
            tree->setEntry<bool>("is_lead", false);
            log_("teammate wants to take lead, i'll assist");
        } else if (cmd > 10 && cmd < 20) { 
            log_("goalie wants to attack");
            int newGoalieId = cmd - 10;
            if (newGoalieId == selfId) { 
                log_("i become goalie");
                tree->setEntry<string>("player_role", "goal_keeper");
                speak("i become goalie", true);
            } else { 
                log_(format("teammate %d becomes goalie", newGoalieId));
            }
        } else {
            log_(format("unknown cmd %d from teammate", cmd));
        }
        data->tmReceivedCmd = 0; 
    }
```

**AFTER (replace with this):**
```cpp
    // Process received team communication signals
    auto cmd = data->tmReceivedCmd;
    if (cmd != 0) {
        log_(format("received cmd %d from teammate", cmd));
        
        // Check if this is an extended signal (4-digit, >= 0x1000)
        if (cmd >= 0x1000) {
            handleReceivedSignal(cmd);
        }
        // Backwards compatibility: handle old 2-signal format
        else if (cmd == 100) {
            // Equivalent to TeamSignal::TAKE_LEAD
            data->tmImLead = false;
            tree->setEntry<bool>("is_lead", false);
            log_("teammate wants to take lead, i'll assist");
        } else if (cmd > 10 && cmd < 20) {
            // Equivalent to TeamSignal::SWITCH_GOALIE
            int newGoalieId = cmd - 10;
            if (newGoalieId == selfId) {
                log_("i become goalie");
                tree->setEntry<string>("player_role", "goal_keeper");
                speak("i become goalie", true);
            } else {
                log_(format("teammate %d becomes goalie", newGoalieId));
            }
        } else {
            log_(format("unknown cmd %d from teammate", cmd));
        }
        
        data->tmReceivedCmd = 0;
    }
```

**Why >= 0x1000?** The old commands were 0, 100, or 10-19 (all < 4096). Our new signals are all >= 0x1000 (4096). This cleanly separates old from new on the wire without a separate flag. No ambiguity.

---

### Step 6: Add Sender Logic — When to Send Which Signal

This is the most context-dependent step. The signals need to be sent from the right places in the decision pipeline.

#### 6a. In `StrikerDecide::tick()` — defensive transitions

**File:** `src/brain/src/brain_tree.cpp`

**Location:** Inside `StrikerDecide::tick()`, wherever `newDecision` is being set. Look for the defense-related code around lines 960-1060.

**When the robot enters defense mode**, add signal sending:

```cpp
    // Insert this where "defend" decision is made (look for newDecision = "defend")
    if (newDecision == "defend") {
        // Broadcast danger level to teammates
        int dangerLevel = (brain->data->ballState == 4) ? 7 : 
                          (brain->data->ballState == 1) ? 5 : 3;
        if (brain->data->tmMyCmd != TeamSignal::DANGER + dangerLevel) {
            brain->data->tmMyCmd = TeamSignal::DANGER | dangerLevel;
            brain->data->tmCmdId++;
            brain->data->tmMyCmdId = brain->data->tmCmdId;
            brain->data->tmLastCmdChangeTime = brain->get_clock()->now();
        }
    }
```

**When entering steal/clear mode**, send CLEAR signal:

```cpp
    // Near where steal decision and isClearance are set
    if (newDecision == "steal" && brain->data->isClearance) {
        brain->data->tmMyCmd = TeamSignal::CLEAR;
        brain->data->tmCmdId++;
        brain->data->tmMyCmdId = brain->data->tmCmdId;
        brain->data->tmLastCmdChangeTime = brain->get_clock()->now();
    }
```

**When taking lead**, send TAKE_LEAD:

```cpp
    // Near where tmImLead is set to true
    if (brain->data->tmImLead && brain->data->tmMyCmd != TeamSignal::TAKE_LEAD) {
        brain->data->tmMyCmd = TeamSignal::TAKE_LEAD;
        brain->data->tmCmdId++;
        brain->data->tmMyCmdId = brain->data->tmCmdId;
        brain->data->tmLastCmdChangeTime = brain->get_clock()->now();
    }
```

#### 6b. In `handleCooperation()` — role/lead transitions

**File:** `src/brain/src/brain.cpp`

Same places where `tmMyCmd` is currently set to `100` or `10+N`. Replace with new signal constants:

**Old (around line 646):**
```cpp
data->tmMyCmd = 10 + minIndex + 1;
```

**New:**
```cpp
data->tmMyCmd = TeamSignal::SWITCH_GOALIE | (minIndex + 1);
```

#### 6c. Sending cooldown helper (optional but recommended)

Add a helper to prevent signal spam (signals are re-sent every 100ms otherwise):

```cpp
// In brain.h, add:
bool shouldSendSignal(int newSignal);

// In brain.cpp, add:
bool Brain::shouldSendSignal(int newSignal) {
    const int SIGNAL_COOLDOWN_MS = 2000;
    
    // Always allow sending if signal changed
    if (newSignal != data->tmMyCmd) return true;
    
    // Don't re-send the same signal within cooldown
    if (msecsSince(data->tmLastCmdChangeTime) < SIGNAL_COOLDOWN_MS) return false;
    
    return true;
}
```

Then wrap signal sends:
```cpp
if (shouldSendSignal(TeamSignal::DANGER | 5)) {
    data->tmMyCmd = TeamSignal::DANGER | 5;
    data->tmCmdId++;
    data->tmMyCmdId = data->tmCmdId;
    data->tmLastCmdChangeTime = get_clock()->now();
}
```

---

### Step 7: Update CMakeLists.txt (if needed)

**File:** `src/brain/CMakeLists.txt`

The new `team_signals.h` is header-only, so no `.cpp` to add. But you may need to ensure the include path is correct. The brain's `CMakeLists.txt` likely already has:

```cmake
include_directories(include)
```

If it doesn't, add it. This is usually already present since it needs to find `brain_data.h` etc. No changes expected.

---

### Step 8: Config Toggle (Optional but Recommended)

**File:** `src/brain/config/config.yaml`

Add a toggle so extended signals can be disabled without reverting code:

```yaml
strategy:
  team_communication:
    enable_extended_signals: false   # Set to true once all robots on Patch 2.2+
```

**In `brain.cpp` `Brain::Brain()` constructor**, declare the parameter (add near other `declare_parameter` calls):

```cpp
declare_parameter<bool>("strategy.team_communication.enable_extended_signals", false);
```

**In the signal sending code**, gate it:

```cpp
bool extendedSignals;
get_parameter("strategy.team_communication.enable_extended_signals", extendedSignals);
if (extendedSignals && shouldSendSignal(TeamSignal::DANGER | 5)) {
    // ... send signal
}
```

**In the receiving code**, gate it:

```cpp
bool extendedSignals;
get_parameter("strategy.team_communication.enable_extended_signals", extendedSignals);
if (extendedSignals && cmd >= 0x1000) {
    handleReceivedSignal(cmd);
}
```

---

## 5. Implementation Checklist

- [ ] **Step 1:** Create `src/brain/include/team_signals.h` with all signal constants
- [ ] **Step 2:** Add new data fields to `src/brain/include/brain_data.h`
- [ ] **Step 3:** Add `#include "team_signals.h"` and `handleReceivedSignal()` declaration to `src/brain/include/brain.h`
- [ ] **Step 4:** Implement `Brain::handleReceivedSignal()` in `src/brain/src/brain.cpp`
- [ ] **Step 5:** Replace old `cmd` handling block in `handleCooperation()` with new dispatch
- [ ] **Step 6a:** Add signal-sending in `StrikerDecide::tick()` for defense/danger/lead signals
- [ ] **Step 6b:** Update signal-sending in `handleCooperation()` role transitions
- [ ] **Step 6c:** (Optional) Add `shouldSendSignal()` cooldown helper
- [ ] **Step 7:** Verify CMakeLists.txt include paths
- [ ] **Step 8:** (Optional) Add `enable_extended_signals` config toggle
- [ ] **Build test:** `colcon build --packages-select brain`
- [ ] **Verify:** No compilation errors, all signal constants resolve

---

## 6. Testing Guidance

### Unit-level checks (no robot needed):

1. **Parse test:** Add a temporary debug log that prints every received signal's category/sub/param. Verify the extraction works.

2. **Backwards compat:** Send `cmd == 100` from an old robot (or simulate it). The new code should still enter the `else if (cmd == 100)` branch, not the `cmd >= 0x1000` branch.

3. **Unknown signal resilience:** Send a garbage hex value like `0x9999`. It should hit the `default:` case in `handleReceivedSignal` and log "Unhandled signal category 9" — no crash, no undefined behavior.

### Integration checks (need 2+ robots):

4. **TAKE_LEAD propagation:** Robot A takes lead → Robot B receives signal → Robot B's `is_lead` blackboard entry becomes `false` → Robot B enters `Assist` behavior.

5. **DANGER cascade:** Robot A sees opponent near ball → sends `DANGER|5` → Robot B receives → B's `tmDangerLevel` is 5 → B adjusts behavior (defensive positioning instead of attacking).

6. **Role switch:** Goalie sends `SWITCH_GOALIE|3` → Player 3 receives → Player 3's `player_role` becomes `"goal_keeper"`.

---

## 7. Common Pitfalls

### ⚠️ `cmdId` race conditions
The `cmdId` is a team-global counter. Every robot increments it for every command. This means if Robot A sends `cmdId=5` and Robot B simultaneously sends `cmdId=5`, receivers will see "same cmdId, not new" for the second one. **This is fine** — commands are idempotent and re-sent every 100ms anyway. Just don't rely on cmdId being perfectly unique.

### ⚠️ The `tmReceivedCmd` consumption pattern
`tmReceivedCmd` is set in the receiver thread (`spinCommunicationReceiver`) and consumed in the main thread (`handleCooperation`). After consumption, it's reset to 0. This means **only one command per tick** is processed. If multiple teammates send commands in the same 100ms window, only the most recent one is processed. This is acceptable for now. A command queue could be added later if needed.

### ⚠️ Network congestion at 100ms intervals
`UNICAST_INTERVAL_MS = 100` means every robot sends a full `TeamCommunicationMsg` (including the full ball/robot pose) to every other robot 10 times per second. With 5 robots, that's 40 UDP packets/sec. This is tiny. The `cmd` field is just 4 bytes of that payload. No performance concern.

### ⚠️ Field zone encoding limitation
The zone map uses zones 1-20, but the parameter nibble in our hex encoding only allows 0-255 (we use the low byte, not just a nibble). So zone values fit easily. Just make sure any helper that packs zone+player uses different fields.

### ⚠️ `HL_MAX_NUM_PLAYERS` array size
Ensure `HL_MAX_NUM_PLAYERS` is at least as large as the highest player ID on your team. If it's 6, player IDs 1-6 work. Player ID 7 will write out of bounds on `tmBallLostBy[7-1]`. Add a bounds check: `if (par > 0 && par <= HL_MAX_NUM_PLAYERS)`.

---

## 8. What NOT to Touch

- ❌ **Do NOT modify `team_communication_msg.h`** — the message struct stays the same. We're only changing the *meaning* of the `cmd` field, not its type.
- ❌ **Do NOT modify `brain_communication.cpp`** — the send/receive/unicast infrastructure stays the same. It already publishes `cmd` and `cmdId` transparently.
- ❌ **Do NOT modify behavior tree XML files** unless you're adding specific signal-reactive behavior (beyond scope of this patch).
- ❌ **Do NOT remove old cmd handling** — keep the `cmd == 100` and `cmd > 10 && cmd < 20` branches for backwards compatibility.

---

## 9. Questions? 

If anything is unclear, check:
- `team-signals-proposal.md` (same directory) — the higher-level design rationale
- Existing `brain_communication.cpp` lines 158-170 — how `cmd` is sent
- Existing `brain_communication.cpp` lines 280-290 — how `cmd` is received
- Existing `brain.cpp` lines 451-682 — `handleCooperation()` full context
- Existing `brain_tree.cpp` - `StrikerDecide::tick()` — where decisions are made

Good luck! We're building something cool here. 🦀⚽
