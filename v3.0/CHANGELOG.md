# Patch v3.0 — CHANGELOG

## v3.0 — Rebase on demo 1.7 + striker spin/speed fixes

Base: official Booster `K1_5v5_demo_1.7` (requires robot firmware 1.7+). The previous commit on
this branch is the unmodified demo, so `git diff` against it shows exactly what v3.0 changes.
The v2.x patches (CID team signals, goalie overhaul, wall-pass, etc.) were built on demo 1.6 and
are **not** ported yet.

Ideas borrowed (logic only, no code) from B-Human's 2026 code release: keep a remembered ball
instead of searching immediately (`BallLostProvider`), and lock a kick decision once committed.

### 1. Approaches the ball too fast
- Cause: `limit_near_ball_speed: false`, so Chase ran at up to 1.6 m/s until 1 m from the ball.
- Fix (`config.yaml`): `limit_near_ball_speed: true`, `near_ball_speed_limit` 0.6 → **0.5**,
  `near_ball_range` 2.0 (unchanged).

### 2. Ball drops out at close range
- Cause: vision already filters balls below 0.4 and sends `confidence × 100`; brain then dropped
  everything under 60, which is where a ball half-hidden by the feet scores.
- Fix: `strategy.ball_confidence_threshold` 60 → **45**.
- Fix: `CamTrackBall` vertical dead zone 3/10 → **2/10** of the image height, so the head pitches
  down before the ball leaves the bottom of the frame.

### 3. Spins on the spot when the ball is lost at the feet
- Cause: `RobotFindBall` always spins at `vyaw_limit` (0.8 rad/s), even when the ball was last
  seen right in front, just below the camera.
- Fix: if the remembered ball is within 0.6 m and within 1.0 rad of straight ahead, back up for
  1.2 s first (≈0.35 m), then spin if it is still not found.

### 4. Kick decision flips back to adjust
- Fix (`StrikerDecide`): once the decision is kick / power_kick / cross / safe_shoot, keep it while
  direction error < 0.45 rad and ball yaw < 0.4 rad (entry thresholds unchanged), and accept a ball
  seen within the last 700 ms instead of requiring a detection on this exact tick.
- Fix (`Kick`): the "ball lost" abort timeout was hard-coded 1000 ms; now
  `strategy.kick_abort_ball_lost_msecs`, default **2000**.

### Not changed (known, for later)
- Minimum speeds 0.3/0.3/0.3 are hard-coded in `robot_client.cpp` (Booster TODO).
- `strategy.ball_confidence_decay_rate` is declared but never read.
- `safe_shoot` has no node in `subtree_striker_play.xml` (unreachable today: threatLevel is 0–2,
  threshold −2.0).
- Near the ball, `enable_auto_visual_kick: true` hands control to Booster's RL kick; these fixes do
  not affect behaviour inside that mode.

> Not compiled on a dev PC (no ROS 2). Build on the robot: `./scripts/build.sh` then
> `source install/setup.bash`. Config/XML edits only take effect after a rebuild.
