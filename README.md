# booster-patch

**Unofficial patch archive for the Booster Robotics robocup_demo.**

Original source: [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo) — The official Booster T1 and K1 RoboCup demo.

This repository contains patched versions of the official robocup_demo with custom modifications for competition use. Not affiliated with Booster Robotics.

## Versions
It is generally recommended to download the latest bugfix release for each `1.x` version series, meaning the version with the highest `y` in `1.x.y`, to minimize known bugs.

| Version | Description | Download | Recommended Ver. |
|---|---|---|---|
| v1.0 | Original patch by Kevin Zhou | [Patch_1.0.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.0/Patch_1.0.zip) | |
| v1.1 | Updated Quick Shot, Power Shot, Deflection Shot | [Patch_1.1.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.1/Patch_1.1.zip) | |
| v1.2.4 | Updated Striker Defense & Bugfixes | [Patch_1.2.4.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.2.4/Patch_1.2.4.zip) | ⭐ |
| v1.3 | Updated Goalie Algorithm | [Patch_1.3.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.3/Patch_1.3.zip) | ⭐ |

## Notes

- This is a community patch, **NOT** the official release.
- For the original unmodified source, visit [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo).
- NOTE: The original source may be updated & modified at any time. The v1.x series uses the demo which can be found [here](https://github.com/dycnnnb/robot).

## Model Engines

TensorRT model engines (.engine files) are **not included** in the source folder.
They are available in the [engines/](engines/) directory reference or can be downloaded from the [release zip](https://github.com/Unknownuserfrommars/booster-patch/releases) as part of the `Patch_1.x.y.zip`.

To use: copy the .engine files from the release zip to the corresponding `Patch_1.x.y/src/vision/model/` before building.
