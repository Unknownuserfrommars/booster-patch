# booster-patch

**Unofficial patch archive for the Booster Robotics robocup_demo.**

Original source: [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo) — The official Booster T1 and K1 RoboCup demo.

This repository contains patched versions of the official robocup_demo with custom modifications for competition use. Not affiliated with Booster Robotics.

## Versions
It is generally recommended to download the latest bugfix release for each `1.x` version series, meaning the version with the highest `y` in `1.x.y`, to minimize known bugs.

| Version | Description | Download | Recommended? |
|---|---|---|:-:|
| v1.0 | Original patch by Kevin Zhou | [Patch_1.0.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.0/Patch_1.0.zip) | No[1][3] |
| v1.1 | Updated Quick Shot, Power Shot, Deflection Shot | [Patch_1.1.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.1/Patch_1.1.zip) | No[1][3] |
| v1.2.6 | Updated Striker Defense & Bugfixes | [Patch_1.2.6.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.2.4/Patch_1.2.6.zip) | ⭐ [3] |
| v1.3.1 | Updated Goalie Algorithm & XML Bugfix | [Patch_1.3.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v1.3.1/Patch_1.3.1.zip) | No[2][3] |
| v2.0 | Update patch to the v1.6 SDK | [Patch_2.0.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v2.0/v2.0.zip) | No[1] |
| v2.1 | Experimental auto-calibration and fix compatibility issues of vision node | [Patch_2.1.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v2.1/v2.1.zip) | No[1] |
| v2.2.2 | Team signal communication system + 3v3 tactics design + Bugfix | [v2.2.2.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v2.2.2/v2.2.2.zip) | No[1] |
| v2.2.3 | Kick pipeline fixes (hesitation + direction) + RL VisualKick band-split hand-off + GlanceAtGoal pre-shot aim check | [v2.2.3.zip](https://github.com/Unknownuserfrommars/booster-patch/releases/download/v2.2.3/v2.2.3.zip) | ⭐ |

[1]: Outdated Version. May contain bugs or have less features.
[2]: Very less test data provided. Can be unstable.
[3]: This uses an outdated SDK version by BoosterRobotics.

## Notes

- This is a community patch, **NOT** the official release.
- For the original unmodified source, visit [BoosterRobotics/robocup_demo](https://github.com/BoosterRobotics/robocup_demo).
- NOTE: The original source may be updated & modified at any time. The v1.x series uses the demo which can be found [here](https://github.com/dycnnnb/robot).
- The v2.x series uses the demo which can be found [here](https://github.com/dycnnnb/robot/tree/2).

## Model Engines

TensorRT model engines (.engine files) are **not included** in the source folder.
They are available in the [engines/](engines/) directory reference or can be downloaded from the [release zip](https://github.com/Unknownuserfrommars/booster-patch/releases) as part of the `Patch_1.x.y.zip`. For v2 releases, they are under the `v2.x.zip` asset, such as `v2.2.2.zip`.

To use: copy the .engine files from the release zip to the corresponding `Patch/src/vision/model/` before building.
