#!/bin/bash
if source /opt/booster/env/activate 2>/dev/null; then
    if bdb service list 2>/dev/null | grep 'server.motion'; then # 1.7
        bdb service kill server.motion
    else
        if bdb container list | grep 'server.motion'; then # 1.6 ~ 1.7
            bdb container kill server.motion
        else
            for pid in $(ps -ef  | grep BoosterServer | grep -v grep | awk '{print $2}'); do # 1.6
                sudo kill -9 $pid;
            done
        fi
    fi
else
    for pid in $(ps -ef  | grep BoosterServer | grep -v grep | awk '{print $2}'); do # <1.6
        sudo kill -9 $pid;
    done
fi
