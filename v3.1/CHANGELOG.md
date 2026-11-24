# Patch v3.1 — CHANGELOG

## v3.1 — Goalie/striker coordination + ryc's near-post goalie (2026-11-24)

Built on v3.0 (demo 1.7). Ported from tactics developed with ryc in the Booster Studio 3v3
simulator. **Not yet tested on a real robot** and not compiled on a dev PC (no ROS 2) — build on
the robot. Both changes can be turned off in `config.yaml` without rebuilding the C++.

### 1. Striker and goalie both charge the ball in our penalty area
- Seen in simulation: when the ball came near our goal the goalie came out to clear it and the
  defender came back for it at the same time; they collided and left an open goal.
- Cause in the demo: `StrikerDecide`'s near-ball visual kick deliberately ignores lead / cost rank
  ("近球是本机的即时优先级"), and it never checked whether a teammate was already kicking.
  The goalie (`Analyze2`) does check `teammateInVisualKick`, so the exclusion only worked one way.
- Fix (`StrikerDecide`): when the ball is in our penalty area and the goalie (from team comm) is
  already in a visual kick, **or** is the lead robot and at least `margin_m` closer to the ball,
  the striker yields: new decision `cover`.
  - Only "lead" or only "closer" is not enough: the goalie can be lead/closer but not kick (its
    clearance angle not ready), and then nobody would play the ball.
  - If team comm is down (goalie `isAlive == false`) the striker behaves exactly as in v3.0.
- New node `CoverFarPost` (`subtree_striker_play.xml`): the striker walks (with obstacle
  avoidance, so around the goalie) to just inside the **far post**, facing the ball — off the
  goalie's path, and where a tap-in into an empty net would go after a goalie rush.
- Config: `strategy.goalie_priority.{enable, margin_m, cover_depth, cover_post_inset}`.

### 2. Goalie depth for near-post shots (ryc)
- ryc: for a shot aimed near a post, what matters is not the goalie's orientation or lateral
  position but **how far it stands from the goal line**. Level with the posts, a deflection
  bounces out across the goal mouth instead of into our own goal.
- The demo's `Intercept2` always holds `dist_to_goalline` = 1.0 m.
- Fix (`Intercept2`): if the predicted crossing point is within `post_zone` of a post, the goalie
  drops back to `dist_to_goalline` = 0.1 m and re-projects the ball path onto that line.
- Config: `strategy.goalie_post_level.{enable, dist_to_goalline, post_zone}`.

### What to check on Saturday
1. `colcon build` succeeds (`./scripts/build.sh`).
2. Striker log (`debug/striker_decide`): look for `goalie owns ball in our box` when the goalie
   clears; striker decision shows `cover` and it walks to the far post.
3. Goalie: roll the ball toward a post — it should step back toward the goal line.
4. If either misbehaves: set its `enable: false` in `config.yaml`, rebuild, retest.

### Not ported from the simulator (on purpose)
- Set-piece receiving-spot scoring and the one-touch pass: relies on exact positions of every
  robot; ryc agreed it would not work with real vision.
- Goalie rush (push the ball away when the opponent is closer): needs reliable opponent
  positions; the real robot only sees opponents inside its camera view.
- Kick power→distance calibration: the real kick is Booster's RL visual kick, not a power value.
- Opponent restarts and own-half clearing: the demo already handles these
  (`GoToFreekickPosition` defense side, `CalcKickDir` "block").

---

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
