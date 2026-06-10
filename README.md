# booster-patch

**Unofficial patch archive for the Booster Robotics robocup_demo.**

Original source: [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo) — The official Booster T1 and K1 RoboCup demo.

This repository contains patched versions of the official robocup_demo with custom modifications for competition use. Not affiliated with Booster Robotics.

## Versions
It is generally recommended to download the latest bugfix release for each `1.x` version series, meaning the version with the highest `y` in `1.x.y`, to minimize known bugs.

| Version | Description | Download | Recommended? |
|---|---|---|:-:|
| v1.0 | Original patch by Kevin Zhou | [Patch_1.0.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.0/Patch_1.0.zip) | |
| v1.1 | Updated Quick Shot, Power Shot, Deflection Shot | [Patch_1.1.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.1/Patch_1.1.zip) | |
| v1.2.6 | Updated Striker Defense & Bugfixes | [Patch_1.2.6.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.2.4/Patch_1.2.6.zip) | ⭐ |
| v1.3.1 | Updated Goalie Algorithm & XML Bugfix | [Patch_1.3.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.3.1/Patch_1.3.1.zip) | ⭐, Untested |
| v2.0 | Update patch to the v1.6 SDK | [Patch_2.0.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v2.0/v2.0.zip) | ⭐, Untested |

## Notes

- This is a community patch, **NOT** the official release.
- For the original unmodified source, visit [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo).
- NOTE: The original source may be updated & modified at any time. The v1.x series uses the demo which can be found [here](https://github.com/dycnnnb/robot).
- The v2.x series uses the demo which can be found [here](https://github.com/dycnnnb/robot/tree/2).

## Model Engines

TensorRT model engines (.engine files) are **not included** in the source folder.
They are available in the [engines/](engines/) directory reference or can be downloaded from the [release zip](https://github.com/Unknownuserfrommars/booster-patch/releases) as part of the `Patch_1.x.y.zip`. For v2 releases, they are under the `"v2.x.y.zip"` (Or `"v2.x.zip"`)

To use: copy the .engine files from the release zip to the corresponding `Patch/src/vision/model/` before building.
