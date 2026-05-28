# booster-patch

**Unofficial patch archive for the Booster Robotics robocup_demo.**

Original source: [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo) — The official Booster T1 and K1 RoboCup demo.

This repository contains patched versions of the official robocup_demo with custom modifications for competition use. Not affiliated with Booster Robotics.

## Versions

| Version | Description | Download |
|---|---|---|
| v1.0 | Original patch by Kevin Zhou | [Patch_1.0.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.0/Patch_1.0.zip) |
| v1.1 | Updated Patch | [Patch_1.1.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.1/Patch_1.1.zip) |
| v1.2.4 | Updated Striker Defense & Bugfixes | [Patch_1.2.4.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.2.4/Patch_1.2.4.zip) |

## Notes

- This is a community patch, not the official release.
- For the original unmodified source, visit [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo).

## Model Engines

Starting from v1.1, TensorRT model engines (.engine files) are **not included** in the source folder.
They are available in the [engines/](engines/) directory reference or can be downloaded from the [v1.1 release](https://github.com/Unknownuserfrommars/booster-patch/releases/tag/v1.1) as part of Patch_1.1.zip.

To use: copy the .engine files from the release zip to Patch_1.1/src/vision/model/ before building.
