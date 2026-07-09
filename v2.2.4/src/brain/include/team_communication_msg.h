#pragma once

#include "types.h"

#define VALIDATION_COMMUNICATION 31202
#define VALIDATION_DISCOVERY 41203
struct TeamCommunicationMsg
{
    int validation = VALIDATION_COMMUNICATION; // validate msg, to determine if it's sent by us.
    int communicationId;
    int teamId;
    int playerId;
    int playerRole; // 1: striker, 2: goal_keeper, 3: unknown
    bool isAlive; // 是否在场上, 且没有在罚时中
    bool isLead; // 是否在控球状态
    bool ballDetected;
    bool ballLocationKnown;
    double ballConfidence;
    double ballRange;
    double cost; // 计算从当前状态到能踢到球的成本
    Point ballPosToField;
    Pose2D robotPoseToField;
    double kickDir;
    double thetaRb;
    int cmdId; // 每个 player 自己的指令序号, 发布新 cmd/CID 时 +1.
    int cmd; // legacy: 100 / 10+PID; v2.2 decimal CID commands are defined in team_signals.h.
};

struct TeamDiscoveryMsg
{
    int validation = VALIDATION_DISCOVERY; // validate msg, to determine if it's sent by us.
    int communicationId;
    int teamId;
    int playerId;
};
