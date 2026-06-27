#pragma once

/**
 * @file team_signals.h
 * @brief Decimal CID registry for team communication commands.
 *
 * CID format: CAPP
 *   C  = category
 *   A  = action within category
 *   PP = parameter, usually player id or a small level
 *
 * The transport still uses TeamCommunicationMsg::cmd. TeamCommunicationMsg::cmdId
 * remains the per-sender sequence number and is not the same thing as a CID.
 */
namespace TeamSignal {

constexpr int NONE = 0;

// Category 1: Lead / possession
constexpr int TAKE_LEAD = 1000;
constexpr int HOLD_LEAD = 1100;
constexpr int RELEASE_LEAD = 1200;
constexpr int REQUEST_BALL = 1300; // Implemented as an alias of PASS_TO_ME for now.

// Category 2: Pass hints
constexpr int PASS_TO_ME = 2000;
constexpr int PASS_TO_PLAYER = 2100; // + target player id
constexpr int DOING_PASS = 2200;     // + target player id
constexpr int DOING_CROSS = 2300;
constexpr int ASSIST_READY = 2400;   // TODO(v2.2): Not implemented without trained zones.
constexpr int THROUGH_BALL = 2500;   // TODO(v2.2): Not implemented yet.
constexpr int WALL_PASS_START = 2600;     // + overlapper PID: start conservative 2-on-1 wall-pass.
constexpr int WALL_PASS_READY = 2700;     // + carrier PID: overlapper reached receive window.
constexpr int WALL_PASS_RUN_READY = 2800; // + return passer PID: original carrier ran beyond defender.
constexpr int WALL_PASS_COMPLETE = 2900;  // wall-pass finished / release tactic state.

// Category 3: Defense
constexpr int DANGER = 3000;             // + level 0-9
constexpr int OPPONENT_IN_ZONE = 3100;   // TODO(v2.2): Not implemented without zones.
constexpr int COVER_PLAYER = 3200;       // TODO(v2.2): Not implemented yet.
constexpr int COVER_ZONE = 3300;         // TODO(v2.2): Not implemented without zones.
constexpr int PRESS = 3400;
constexpr int FALL_BACK = 3401;
constexpr int BLOCK_SHOT = 3500;         // TODO(v2.2): Not implemented.
constexpr int CLEAR = 3600;

// Category 4: Set pieces
constexpr int FREEKICK_SETUP = 4000;     // TODO(v2.2): Not implemented.
constexpr int FREEKICK_EXECUTE = 4100;   // TODO(v2.2): Not implemented.
constexpr int CORNER_PLAY = 4200;        // TODO(v2.2): Not implemented.
constexpr int KICKOFF_PLAY = 4300;       // TODO(v2.2): Not implemented.

// Category 5: Formation / positioning
constexpr int FORMATION = 5000;          // TODO(v2.2): Not implemented.
constexpr int MOVE_TO_ROLE_ZONE = 5100;  // TODO(v2.2): Not implemented without zones.
constexpr int SPREAD = 5200;
constexpr int COMPACT = 5201;
constexpr int PUSH_UP = 5300;            // TODO(v2.2): Not implemented.
constexpr int HOLD_POSITION = 5400;

// Category 6: Status
constexpr int BALL_LOST = 6000;
constexpr int BALL_FOUND = 6001;
constexpr int STUCK = 6100;
constexpr int UNSTUCK = 6101;
constexpr int FALLEN = 6200;
constexpr int RECOVERED = 6201;
constexpr int GOAL_SCORED = 6300;        // TODO(v2.2): Not implemented; GameController owns score.
constexpr int GOAL_CONCEDED = 6301;      // TODO(v2.2): Not implemented; GameController owns score.

// Category 7: Role management
constexpr int SWITCH_GOALIE = 7000;      // TODO(v2.2): Not implemented; old 10+PID still works.
constexpr int SWITCH_STRIKER = 7100;     // TODO(v2.2): Not implemented.
constexpr int NEED_SUBSTITUTE = 7200;    // TODO(v2.2): Not implemented.

// Category 8: Emergency
constexpr int ABORT = 8000;
constexpr int BALL_GOING_IN = 8100;
constexpr int BREAKAWAY = 8200;
constexpr int COLLISION = 8300;          // TODO(v2.2): Not implemented without direction semantics.

constexpr int category(int cid) { return cid / 1000; }
constexpr int action(int cid) { return (cid / 100) % 10; }
constexpr int param(int cid) { return cid % 100; }
constexpr bool isExtended(int cid) { return cid >= 1000 && cid <= 9999; }
constexpr int withParam(int baseCid, int value) { return baseCid + value; }

constexpr int baseCid(int cid) {
    if (cid >= PASS_TO_PLAYER && cid < PASS_TO_PLAYER + 100) return PASS_TO_PLAYER;
    if (cid >= DOING_PASS && cid < DOING_PASS + 100) return DOING_PASS;
    if (cid >= THROUGH_BALL && cid < THROUGH_BALL + 100) return THROUGH_BALL;
    if (cid >= WALL_PASS_START && cid < WALL_PASS_START + 100) return WALL_PASS_START;
    if (cid >= WALL_PASS_READY && cid < WALL_PASS_READY + 100) return WALL_PASS_READY;
    if (cid >= WALL_PASS_RUN_READY && cid < WALL_PASS_RUN_READY + 100) return WALL_PASS_RUN_READY;
    if (cid >= WALL_PASS_COMPLETE && cid < WALL_PASS_COMPLETE + 100) return WALL_PASS_COMPLETE;
    if (cid >= DANGER && cid < DANGER + 10) return DANGER;
    if (cid >= SWITCH_GOALIE && cid < SWITCH_GOALIE + 100) return SWITCH_GOALIE;
    if (cid >= SWITCH_STRIKER && cid < SWITCH_STRIKER + 100) return SWITCH_STRIKER;
    return cid;
}

constexpr bool isTargeted(int cid) {
    switch (baseCid(cid)) {
        case PASS_TO_PLAYER:
        case DOING_PASS:
        case THROUGH_BALL:
        case WALL_PASS_START:
        case WALL_PASS_READY:
        case WALL_PASS_RUN_READY:
        case WALL_PASS_COMPLETE:
        case SWITCH_GOALIE:
        case SWITCH_STRIKER:
            return true;
        default:
            return false;
    }
}

constexpr bool isImplemented(int cid) {
    switch (baseCid(cid)) {
        case NONE:
        case TAKE_LEAD:
        case HOLD_LEAD:
        case RELEASE_LEAD:
        case REQUEST_BALL:
        case PASS_TO_ME:
        case PASS_TO_PLAYER:
        case DOING_PASS:
        case DOING_CROSS:
        case WALL_PASS_START:
        case WALL_PASS_READY:
        case WALL_PASS_RUN_READY:
        case WALL_PASS_COMPLETE:
        case DANGER:
        case PRESS:
        case FALL_BACK:
        case CLEAR:
        case SPREAD:
        case COMPACT:
        case HOLD_POSITION:
        case BALL_LOST:
        case BALL_FOUND:
        case STUCK:
        case UNSTUCK:
        case FALLEN:
        case RECOVERED:
        case ABORT:
        case BALL_GOING_IN:
        case BREAKAWAY:
            return true;
        default:
            return false;
    }
}

} // namespace TeamSignal
