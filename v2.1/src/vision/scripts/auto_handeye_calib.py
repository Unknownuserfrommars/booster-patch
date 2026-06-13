#!/usr/bin/env python3
"""
Auto Hand-Eye Calibration Node (Full-Auto)
===========================================
自动手眼标定——机器人自己转头扫网格，自动检测棋盘格、自动采集、自动计算。

两种模式:
  AUTO 模式 (默认):   程序控制机器人头扫描 pitch/yaw 网格，自动采集
  SEMI-AUTO 模式:     人用手柄转头，程序自动判断+拍照（替代按S键）

Usage:
  # 全自动（需要 LocoApiTopicReq 可写）
  python3 auto_handeye_calib.py --config src/vision/config/vision.yaml

  # 半自动
  python3 auto_handeye_calib.py --config src/vision/config/vision.yaml --mode semi

物理设定:
  - 标定板固定在机器人前方（墙上/架子上），不动
  - 机器人头（带相机）按程序控制转动
  - 每个角度检测到棋盘格 → 自动采集 → 下一角度
  - 攒够 8 帧（覆盖足够多角度）→ 自动计算外参

Head control wire format (LocoApiTopicReq / RpcReqMsg):
  uuid:   random
  header: {"api_id": <kRotateHead>}
  body:   {"pitch": X.X, "yaw": Y.Y}
"""

import argparse
import copy
import importlib.util
import json
import os
import shlex
import sys
import time
import uuid
from datetime import datetime


def bootstrap_ros_environment():
    """Re-run under ROS/Booster setup files when launched from a plain shell."""
    needs_booster_msgs = '--discover' in sys.argv or '--api-id' in sys.argv
    needs_booster_interface = '--api-id' in sys.argv
    missing_rclpy = importlib.util.find_spec('rclpy') is None
    missing_booster_msgs = (
        needs_booster_msgs and importlib.util.find_spec('booster_msgs') is None
    )
    missing_booster_interface = (
        needs_booster_interface and importlib.util.find_spec('booster_interface') is None
    )
    if not missing_rclpy and not missing_booster_msgs and not missing_booster_interface:
        return
    if os.environ.get('AUTO_HANDEYE_ROS_SETUP_ATTEMPTED') == '1':
        return

    setup_candidates = [
        '/opt/ros/humble/setup.bash',
        '/opt/booster/BoosterRos2/install/setup.bash',
        '/opt/booster/BoosterRos2Interface/install/setup.bash',
        '/home/booster/Workspace/K1_5v5_Demo_v1.6/install/setup.bash',
    ]
    source_parts = [
        f'source {shlex.quote(path)} >/dev/null 2>/dev/null'
        for path in setup_candidates
        if os.path.exists(path)
    ]
    if not source_parts:
        return

    env = os.environ.copy()
    env['AUTO_HANDEYE_ROS_SETUP_ATTEMPTED'] = '1'
    argv = ' '.join(shlex.quote(arg) for arg in [sys.executable] + sys.argv)
    cmd = '; '.join(source_parts + [f'exec {argv}'])
    os.execvpe('bash', ['bash', '-lc', cmd], env)


bootstrap_ros_environment()

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, CompressedImage
from geometry_msgs.msg import Pose as RosPose
from cv_bridge import CvBridge
import yaml

try:
    from booster_interface.srv import RpcService
except ImportError:
    RpcService = None

try:
    from booster_msgs.msg import RpcReqMsg
except ImportError:
    RpcReqMsg = None


# ─── Head sweep grid ───────────────────────────────────────────────
# Pitch: 低头看板子，范围 -25 ~ 0 度（0 = 平视）
# Yaw:   左右扫，范围 -60 ~ +60 度（0 = 正前方）
SWEEP_YAW_DEG = list(range(-60, 65, 15))   # -60, -45, -30, -15, 0, 15, 30, 45, 60
SWEEP_PITCH_DEG = [-25, -20, -15, -10, -5]  # 低头看标定板

# Settle time after head movement (seconds)
HEAD_SETTLE_S = 0.8

# Timeout waiting for board detection at a position (seconds)
DETECT_TIMEOUT_S = 3.0

LOCO_API_CHANGE_MODE = 2000
LOCO_API_ROTATE_HEAD = 2004
ROBOT_MODE_PREPARE = 1
ROBOT_MODE_WALKING = 2
DEFAULT_COLOR_TOPIC = '/boostercamera/head/rgb'
DEFAULT_CAMERA_INFO_TOPIC = '/boostercamera/head/rgb/camera_info'


def ros_pose_to_rt(pose: RosPose):
    from scipy.spatial.transform import Rotation
    qx, qy, qz, qw = pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w
    R = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
    t = np.array([[pose.position.x], [pose.position.y], [pose.position.z]])
    return R, t


def rt_to_4x4(R, t):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3:4] = t
    return T


def ensure_booster_msgs_available():
    """Make booster_msgs importable, re-execing under the Booster ROS overlay if needed."""
    try:
        from booster_msgs.msg import RpcReqMsg  # noqa: F401
        return True
    except ImportError:
        pass

    setup_candidates = [
        '/opt/booster/BoosterRos2/install/setup.bash',
        '/home/booster/Workspace/K1_5v5_Demo_v1.6/install/setup.bash',
    ]
    setup_path = next((p for p in setup_candidates if os.path.exists(p)), None)
    if setup_path and os.environ.get('AUTO_HANDEYE_BOOSTER_SETUP_ATTEMPTED') != '1':
        env = os.environ.copy()
        env['AUTO_HANDEYE_BOOSTER_SETUP_ATTEMPTED'] = '1'
        argv = ' '.join(shlex.quote(arg) for arg in [sys.executable] + sys.argv)
        cmd = f'source {shlex.quote(setup_path)} && exec {argv}'
        os.execvpe('bash', ['bash', '-lc', cmd], env)

    print('ERROR: booster_msgs is not importable, so LocoApiTopicReq cannot be decoded.')
    print('Run this first, then retry:')
    print('  source /opt/booster/BoosterRos2/install/setup.bash')
    return False


class AutoHandEyeCalib(Node):
    def __init__(self, config_path, mode='auto', api_id=None,
                 board_w=11, board_h=8, square_size=0.05,
                 image_topic=None, camera_info_topic=None,
                 compressed_topic=None):
        super().__init__('auto_handeye_calib')

        self.mode = mode  # 'auto' or 'semi'
        self.config_path = config_path
        self.board_w = board_w
        self.board_h = board_h
        self.square_size = square_size
        self.target_frames = 8
        self.head_api_id = api_id  # None = try to auto-discover

        # Load config
        self._load_config()
        if image_topic:
            self.color_topic = image_topic
        if camera_info_topic:
            self.intrin_topic = camera_info_topic
        self.compressed_topic = compressed_topic

        self.bridge = CvBridge()

        # Subscriptions
        self.color_sub = self.create_subscription(
            Image, self.color_topic, self._color_cb, qos_profile_sensor_data)
        self.compressed_sub = None
        if self.compressed_topic:
            self.compressed_sub = self.create_subscription(
                CompressedImage, self.compressed_topic, self._compressed_cb,
                qos_profile_sensor_data)
        self.pose_sub = self.create_subscription(
            RosPose, '/head_pose', self._pose_cb, 10)
        self.camera_info_sub = self.create_subscription(
            CameraInfo, self.intrin_topic, self._camera_info_cb,
            qos_profile_sensor_data)

        # Service client for head control (auto mode)
        self.loco_client = None
        self.head_pub = None
        self.mode_switched_for_auto = False
        if self.mode == 'auto' and self.head_api_id is not None:
            if RpcService is None or RpcReqMsg is None:
                self.get_logger().error('Booster ROS interfaces are not available. Falling back to SEMI-AUTO mode.')
                self.mode = 'semi'
            else:
                self.loco_client = self.create_client(RpcService, '/booster_rpc_service')
                self.head_pub = self.create_publisher(RpcReqMsg, 'LocoApiTopicReq', 10)

        # State
        self.latest_img = None
        self.latest_img_ts = None
        self.latest_pose = None
        self.latest_pose_ts = None
        self.captured_frames = []
        self.prev_board_poses = []
        self.last_capture_time = 0.0
        self.intrinsics_received = False
        self.camera_matrix = None
        self.dist_coeffs = None
        self.board_position_mask = None
        self.display_enabled = bool(os.environ.get('DISPLAY'))
        self._load_intrinsics_from_config()

        # 3D board points
        self.board_points_3d = np.array(
            [
                [j * self.square_size, i * self.square_size, 0.0]
                for i in range(self.board_h)
                for j in range(self.board_w)
            ],
            dtype=np.float32,
        )

        # Auto sweep state
        self.sweep_positions = []
        self.sweep_idx = 0
        self.sweep_phase = 'init'  # init | moving | settling | detecting | done
        self.sweep_timer_start = None
        self.sweep_position_start = None
        self.auto_calib_done = False
        self.head_cmd_sent = False

        if self.mode == 'auto':
            self._build_sweep_grid()
            self.get_logger().info(f'AUTO mode: {len(self.sweep_positions)} head positions in grid')
            self.get_logger().info(f'  Yaw:  {min(SWEEP_YAW_DEG)} to {max(SWEEP_YAW_DEG)} deg, step 15')
            self.get_logger().info(f'  Pitch: {SWEEP_PITCH_DEG} deg')
            self.get_logger().info(f'  Settle: {HEAD_SETTLE_S}s, detect timeout: {DETECT_TIMEOUT_S}s')
            self.get_logger().info(f'  Head API ID: {self.head_api_id or "auto-discover (try ros2 topic echo)"}')
        else:
            self.get_logger().info(f'SEMI-AUTO mode: move head with gamepad, auto-capture will handle S-key')

        # Display timer: 10 Hz
        self.timer = self.create_timer(0.1, self._process_tick)

        self.get_logger().info(f'Ready. Camera: {self.color_topic}')
        if self.compressed_topic:
            self.get_logger().info(f'Compressed image fallback: {self.compressed_topic}')
        self.get_logger().info(f'Board: {board_w}x{board_h}, square={square_size}m')

    def _load_config(self):
        """Read camera topics from config yaml."""
        if not self.config_path or not os.path.exists(self.config_path):
            self.get_logger().warn(f'Config not found: {self.config_path}, using defaults')
            self.base_config = {}
            self.config_intrin = None
            self.color_topic = DEFAULT_COLOR_TOPIC
            self.intrin_topic = DEFAULT_CAMERA_INFO_TOPIC
            self.camera_type = 'realsense'
            return

        with open(self.config_path, 'r') as f:
            cfg = yaml.safe_load(f)
        self.base_config = cfg if cfg is not None else {}

        camera_cfg = self.base_config.get('camera', {})
        self.camera_type = camera_cfg.get('type', 'realsense')
        self.config_intrin = camera_cfg.get('intrin')

        # v1.6+ publishes a unified camera interface regardless of physical camera.
        self.color_topic = DEFAULT_COLOR_TOPIC
        self.intrin_topic = DEFAULT_CAMERA_INFO_TOPIC

        self.get_logger().info(f'Camera type: {self.camera_type} → {self.color_topic}')

    def _build_sweep_grid(self):
        """Build ordered list of (pitch_deg, yaw_deg) positions to visit."""
        # Snake pattern: go left-to-right on one pitch row, right-to-left on next
        positions = []
        for i, pitch in enumerate(SWEEP_PITCH_DEG):
            yaw_row = SWEEP_YAW_DEG if i % 2 == 0 else list(reversed(SWEEP_YAW_DEG))
            for yaw in yaw_row:
                positions.append((pitch, yaw))
        self.sweep_positions = positions
        self.get_logger().info(f'Grid: {len(self.sweep_positions)} positions')
        self.get_logger().info(f'  Pattern: snake scan (left→right, right→left alternating)')

    def _move_head(self, pitch_deg, yaw_deg):
        """Send head rotation command via LocoApiTopicReq."""
        if self.head_pub is None:
            self.get_logger().error('Head publisher not available (semi-auto mode?)')
            return False

        if self.head_api_id is None:
            self.get_logger().error('head_api_id not set! Cannot control head.')
            self.get_logger().error('Find it on the robot: grep -r kRotateHead /opt/booster/')
            return False

        pitch_rad = np.deg2rad(float(pitch_deg))
        yaw_rad = np.deg2rad(float(yaw_deg))
        msg = RpcReqMsg()
        msg.uuid = str(uuid.uuid4())
        msg.header = json.dumps({'api_id': self.head_api_id})
        msg.body = json.dumps({'pitch': float(pitch_rad), 'yaw': float(yaw_rad)})

        self.head_pub.publish(msg)
        self.get_logger().info(
            f'  → Head: pitch={pitch_deg}° yaw={yaw_deg}° '
            f'({pitch_rad:.3f}, {yaw_rad:.3f} rad)'
        )
        return True

    def prepare_auto_control(self):
        if self.mode != 'auto' or self.loco_client is None:
            return True
        if not self._ensure_loco_service():
            return False
        if self._call_loco_api(LOCO_API_CHANGE_MODE, {'mode': ROBOT_MODE_WALKING}):
            self.mode_switched_for_auto = True
            self.get_logger().info('Robot switched to kWalking for head control.')
            time.sleep(0.5)
            return True
        self.get_logger().error('Failed to switch robot to kWalking; head control will not work.')
        return False

    def _ensure_loco_service(self):
        if self.loco_client.service_is_ready():
            return True
        self.get_logger().info('Waiting for /booster_rpc_service...')
        if self.loco_client.wait_for_service(timeout_sec=3.0):
            return True
        self.get_logger().error('/booster_rpc_service is not available.')
        return False

    def _call_loco_api(self, api_id, body):
        req = RpcService.Request()
        req.msg.api_id = int(api_id)
        req.msg.body = json.dumps(body) if isinstance(body, dict) else str(body)
        future = self.loco_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done() or future.result() is None:
            self.get_logger().error(f'Loco API {api_id} timed out.')
            return False
        resp = future.result().msg
        if resp.status != 0:
            self.get_logger().error(f'Loco API {api_id} failed: status={resp.status} body={resp.body}')
            return False
        return True

    def _restore_prepare_mode(self):
        if self.mode_switched_for_auto and self.loco_client is not None and rclpy.ok():
            self._call_loco_api(LOCO_API_CHANGE_MODE, {'mode': ROBOT_MODE_PREPARE})
            self.mode_switched_for_auto = False

    def _camera_info_cb(self, msg: CameraInfo):
        if self.intrinsics_received:
            return
        fx, fy = msg.k[0], msg.k[4]
        cx, cy = msg.k[2], msg.k[5]
        self.camera_matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)
        self.dist_coeffs = np.array(msg.d, dtype=np.float64)
        self.intrinsics_received = True
        self.get_logger().info(f'Intrinsics OK: {fx:.0f}x{fy:.0f}')

    def _color_cb(self, msg: Image):
        self.latest_img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        self.latest_img_ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def _compressed_cb(self, msg: CompressedImage):
        data = np.frombuffer(msg.data, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            return
        self.latest_img = img
        self.latest_img_ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def _load_intrinsics_from_config(self):
        if not self.config_intrin:
            return
        try:
            fx = float(self.config_intrin['fx'])
            fy = float(self.config_intrin['fy'])
            cx = float(self.config_intrin['cx'])
            cy = float(self.config_intrin['cy'])
            coeffs = self.config_intrin.get('distortion_coeffs') or []
        except (KeyError, TypeError, ValueError):
            self.get_logger().warn('Invalid camera.intrin in config; waiting for CameraInfo.')
            return
        self.camera_matrix = np.array(
            [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
            dtype=np.float64,
        )
        self.dist_coeffs = np.array(coeffs, dtype=np.float64)
        self.intrinsics_received = True
        self.get_logger().info(f'Intrinsics loaded from config: {fx:.0f}x{fy:.0f}')

    def _pose_cb(self, msg: RosPose):
        self.latest_pose = msg
        self.latest_pose_ts = self.get_clock().now().nanoseconds * 1e-9

    def _detect_board(self, img):
        """Detect chessboard. Returns (corners_subpix, score, details)."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(
            gray, (self.board_w, self.board_h),
            flags=cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
        )
        if not found:
            return None, 0, {'reason': 'not found'}

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners_subpix = cv2.cornerSubPix(gray, corners, (5, 5), (-1, -1), criteria)

        score, details = self._score_frame(img, corners_subpix.squeeze())
        return corners_subpix, score, details

    def _score_frame(self, img, corners):
        """Score 0-100. Fill ratio(40) + Skew(30) + Corner quality(20) + Diversity(10)."""
        h, w = img.shape[:2]
        score = 0
        details = {}

        valid_x1, valid_y1 = int(w * 0.15), int(h * 0.15)
        valid_x2, valid_y2 = int(w * 0.85), int(h * 0.85)
        valid_area = (valid_x2 - valid_x1) * (valid_y2 - valid_y1)

        corners_np = np.array(corners)
        board_x1, board_y1 = corners_np.min(axis=0)
        board_x2, board_y2 = corners_np.max(axis=0)

        # Overlap with valid area
        ox1, oy1 = max(valid_x1, board_x1), max(valid_y1, board_y1)
        ox2, oy2 = min(valid_x2, board_x2), min(valid_y2, board_y2)
        if ox2 <= ox1 or oy2 <= oy1:
            return 0, {'reason': 'outside valid area'}

        overlap_area = (ox2 - ox1) * (oy2 - oy1)
        board_area = (board_x2 - board_x1) * (board_y2 - board_y1)
        if board_area <= 0:
            return 0, {'reason': 'zero board area'}

        fill_ratio = min(overlap_area / valid_area, 1.0)
        containment = overlap_area / board_area

        if containment < 0.85:
            return 0, {'reason': f'clipped by edge ({containment:.0%})'}

        score += fill_ratio * 40
        details['fill_ratio'] = fill_ratio
        details['containment'] = containment

        # Skew angle via solvePnP
        if self.intrinsics_received:
            ok, rvec, tvec = cv2.solvePnP(
                self.board_points_3d, np.array(corners, dtype=np.float32),
                self.camera_matrix, self.dist_coeffs
            )
            if ok:
                R, _ = cv2.Rodrigues(rvec)
                board_normal = R[:, 2]
                angle_rad = np.arccos(np.clip(abs(np.dot(board_normal, [0, 0, 1])), -1, 1))
                angle_deg = np.degrees(angle_rad)
                details['skew_deg'] = angle_deg
                skew_score = max(0, 30 * (1 - angle_deg / 50.0))
                score += skew_score
                details['rvec'] = rvec
                details['tvec'] = tvec
            else:
                return 0, {'reason': 'solvePnP failed'}
        else:
            details['skew_deg'] = None

        details['score'] = score
        return score, details

    def _pose_diverse(self, rvec, tvec):
        """Check board pose differs from previous captures."""
        if not self.prev_board_poses:
            return True
        R_new, _ = cv2.Rodrigues(rvec)
        T_new = rt_to_4x4(R_new, tvec)
        for T_old in self.prev_board_poses:
            trans_diff = np.linalg.norm(T_new[:3, 3] - T_old[:3, 3])
            R_diff = T_new[:3, :3] @ T_old[:3, :3].T
            rot_diff_deg = np.degrees(np.arccos(np.clip((np.trace(R_diff) - 1) / 2, -1, 1)))
            if trans_diff < 0.03 and rot_diff_deg < 10.0:
                return False
        return True

    def _try_capture(self, img, corners, details):
        """Capture frame if pose synced and board detected."""
        if self.latest_pose is None:
            return False
        # Sync check
        if self.latest_img_ts and self.latest_pose_ts:
            sync_diff_ms = abs(self.latest_img_ts - self.latest_pose_ts) * 1000
            if sync_diff_ms > 1500:
                return False

        R_head, t_head = ros_pose_to_rt(self.latest_pose)
        rvec, tvec = details.get('rvec'), details.get('tvec')
        if rvec is None or tvec is None:
            return False

        n = len(self.captured_frames)
        self.captured_frames.append({
            'img': img.copy(),
            'head_R': R_head, 'head_t': t_head,
            'board_rvec': rvec, 'board_tvec': tvec,
            'corners': corners.copy(),
            'score': details.get('score', 0),
            'fill_ratio': details.get('fill_ratio', 0),
            'skew_deg': details.get('skew_deg', 0),
        })

        R_board, _ = cv2.Rodrigues(rvec)
        self.prev_board_poses.append(rt_to_4x4(R_board, tvec))

        # Overlay mask
        cn = np.int32(corners)
        hull = cv2.convexHull(cn)
        mask = np.zeros_like(img)
        cv2.fillPoly(mask, [hull], (0, 255, 0))
        cv2.putText(mask, str(n), tuple(cn[0] + [0, 10]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        if self.board_position_mask is None:
            self.board_position_mask = np.zeros_like(img)
        cv2.bitwise_or(mask, self.board_position_mask, self.board_position_mask)

        self.get_logger().info(
            f'CAPTURE #{n+1}/{self.target_frames} | '
            f'score={details.get("score",0):.0f} fill={details.get("fill_ratio",0):.0%} '
            f'skew={details.get("skew_deg",0):.0f}deg'
        )
        return True

    # ─── AUTO sweep logic ──────────────────────────────────────────

    def _auto_sweep_tick(self):
        """Advance the head sweep state machine."""
        now = time.time()

        if self.sweep_phase == 'init':
            # Start sweeping
            self.sweep_phase = 'moving'
            self.sweep_idx = 0
            self.sweep_position_start = now
            self._sweep_move_to_current()
            self.head_cmd_sent = True

        elif self.sweep_phase == 'moving':
            # Wait for head to settle
            if now - self.sweep_position_start >= HEAD_SETTLE_S:
                self.sweep_phase = 'detecting'
                self.sweep_timer_start = now
                self.get_logger().info(f'  Waiting for board at position {self.sweep_idx+1}/{len(self.sweep_positions)}...')

        elif self.sweep_phase == 'detecting':
            # Try auto-capture
            if self.latest_img is not None:
                corners, score, details = self._detect_board(self.latest_img)
                if corners is not None and score >= 40:
                    if 'rvec' in details and self._pose_diverse(details['rvec'], details['tvec']):
                        if self._try_capture(self.latest_img, corners.squeeze(), details):
                            self.get_logger().info(
                                f'  ✓ Captured at position {self.sweep_idx+1}')
                            self._sweep_next()
                            return

            # Timeout?
            if now - self.sweep_timer_start > DETECT_TIMEOUT_S:
                self.get_logger().info(
                    f'  ✗ No board at position {self.sweep_idx+1}, skipping')
                self._sweep_next()

        elif self.sweep_phase == 'done':
            if len(self.captured_frames) >= 3 and not self.auto_calib_done:
                self._run_calibration()
                self.auto_calib_done = True
            elif not self.auto_calib_done:
                self.get_logger().error(
                    f'Calibration aborted: only {len(self.captured_frames)} usable frames collected; need at least 3.'
                )
                self.auto_calib_done = True
                self._restore_prepare_mode()
                if rclpy.ok():
                    rclpy.shutdown()

    def _sweep_move_to_current(self):
        pitch, yaw = self.sweep_positions[self.sweep_idx]
        self._move_head(pitch, yaw)
        self.sweep_position_start = time.time()

    def _sweep_next(self):
        self.sweep_idx += 1
        if self.sweep_idx >= len(self.sweep_positions) or len(self.captured_frames) >= self.target_frames:
            self.get_logger().info(
                f'Sweep complete. {len(self.captured_frames)} frames collected.')
            self.sweep_phase = 'done'
        else:
            self.sweep_phase = 'moving'
            self.sweep_position_start = time.time()
            self._sweep_move_to_current()
            self.head_cmd_sent = True

    # ─── Semi-auto logic ────────────────────────────────────────────

    def _semi_auto_tick(self, display):
        """Semi-auto: human controls head, auto-capture replaces 'S' key."""
        if self.latest_img is None:
            return

        corners, score, details = self._detect_board(self.latest_img)
        h, w = self.latest_img.shape[:2]

        status = [f'{len(self.captured_frames)}/{self.target_frames} captured']
        can_capture = False

        if corners is not None:
            cv2.drawChessboardCorners(display, (self.board_w, self.board_h), corners, True)
            skew_str = f"{details.get('skew_deg', '?'):.0f}deg" if details.get('skew_deg') else '?'
            status.append(f'Board OK | score={score:.0f} fill={details.get("fill_ratio",0):.0%} skew={skew_str}')

            diversity_ok = ('rvec' in details and
                          self._pose_diverse(details['rvec'], details['tvec']))
            time_ok = (time.time() - self.last_capture_time) >= 0.8

            if score >= 50 and diversity_ok and time_ok:
                if self._try_capture(self.latest_img, corners.squeeze(), details):
                    self.last_capture_time = time.time()
            else:
                if not diversity_ok:
                    status.append('↻ Move head more (pose too similar)')
                elif score < 50:
                    status.append('↻ Adjust (low score)')
                else:
                    status.append(f'⟳ Cooldown {0.8 - (time.time() - self.last_capture_time):.1f}s')
        else:
            status.append(f'No board: {details.get("reason", "?")}')

        # Draw status
        y0 = 30
        for text in status:
            cv2.putText(display, text, (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
            y0 += 22
        cv2.putText(display, 'SEMI-AUTO | q=quit  r=reset  c=calc(force)',
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)

        # Auto-compute when enough
        if len(self.captured_frames) >= self.target_frames and not self.auto_calib_done:
            self._run_calibration()
            self.auto_calib_done = True

    # ─── Main tick ─────────────────────────────────────────────────

    def _process_tick(self):
        if self.auto_calib_done:
            return

        img = self.latest_img
        if img is None:
            return

        display = img.copy()
        h, w = img.shape[:2]

        # Board position mask overlay
        if self.board_position_mask is not None:
            cv2.addWeighted(self.board_position_mask, 0.25, display, 0.75, 0, display)

        # Valid area rectangle
        vx1, vy1 = int(w * 0.15), int(h * 0.15)
        vx2, vy2 = int(w * 0.85), int(h * 0.85)
        cv2.rectangle(display, (vx1, vy1), (vx2, vy2), (0, 255, 0), 2)

        # Mode label
        mode_label = 'FULL-AUTO' if self.mode == 'auto' else 'SEMI-AUTO'
        cv2.putText(display, mode_label, (w - 140, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        if self.mode == 'auto' and not self.auto_calib_done:
            # Sweep status
            if self.sweep_phase != 'done':
                pitch, yaw = self.sweep_positions[self.sweep_idx]
                phase_str = {'init': 'starting', 'moving': f'moving→ p{pitch} y{yaw}',
                            'detecting': f'detecting p{pitch} y{yaw}', 'done': 'done'}[self.sweep_phase]
                cv2.putText(display, f'Sweep {self.sweep_idx+1}/{len(self.sweep_positions)} {phase_str}',
                            (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
            self._auto_sweep_tick()

        elif self.mode == 'semi':
            self._semi_auto_tick(display)

        # Key check
        key = 255
        if self.display_enabled:
            cv2.imshow('Auto Hand-Eye Calibration', display)
            key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            self.get_logger().info('Quit.')
            rclpy.shutdown()
            sys.exit(0)
        elif key == ord('r'):
            self.get_logger().info('Reset.')
            self._reset()
        elif key == ord('c'):
            if len(self.captured_frames) >= 3:
                self._run_calibration()
                self.auto_calib_done = True

    # ─── Calibration ────────────────────────────────────────────────

    def _run_calibration(self):
        self.get_logger().info('=' * 60)
        self.get_logger().info(f'Computing Hand-Eye with {len(self.captured_frames)} frames...')

        R_g2b, t_g2b, R_t2c, t_t2c = [], [], [], []
        for f in self.captured_frames:
            R_board, _ = cv2.Rodrigues(f['board_rvec'])
            R_g2b.append(f['head_R'])
            t_g2b.append(f['head_t'])
            R_t2c.append(R_board)
            t_t2c.append(f['board_tvec'])

        try:
            R_c2g, t_c2g = cv2.calibrateHandEye(
                R_g2b, t_g2b, R_t2c, t_t2c,
                method=cv2.CALIB_HAND_EYE_TSAI
            )
        except Exception as e:
            self.get_logger().error(f'Calibration failed: {e}')
            return

        # Reprojection error
        total_err = 0.0
        n_pts = 0
        if self.intrinsics_received:
            for f in self.captured_frames:
                pts_proj, _ = cv2.projectPoints(
                    self.board_points_3d, f['board_rvec'], f['board_tvec'],
                    self.camera_matrix, self.dist_coeffs
                )
                cn = np.array(f['corners'], dtype=np.float32).reshape(-1, 1, 2)
                total_err += cv2.norm(cn, pts_proj, cv2.NORM_L2) / len(pts_proj)
                n_pts += 1

        mean_reproj = total_err / n_pts if n_pts > 0 else float('nan')

        # Output
        from scipy.spatial.transform import Rotation
        quat = Rotation.from_matrix(R_c2g).as_quat()
        tx, ty, tz = t_c2g.ravel()
        extrin_matrix = rt_to_4x4(R_c2g, t_c2g)

        self.get_logger().info(f'Extrinsics (R):\n{R_c2g}')
        self.get_logger().info(f'Extrinsics (t): [{tx:.4f}, {ty:.4f}, {tz:.4f}]')
        self.get_logger().info(f'Quat: [{quat[0]:.4f}, {quat[1]:.4f}, {quat[2]:.4f}, {quat[3]:.4f}]')
        self.get_logger().info(f'Mean reprojection error: {mean_reproj:.4f} px')

        # Save
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        result = copy.deepcopy(self.base_config)
        camera_cfg = result.setdefault('camera', {})
        camera_cfg['type'] = self.camera_type
        camera_cfg['extrin'] = extrin_matrix.tolist()
        camera_cfg['pitch_compensation'] = 0.0
        camera_cfg['yaw_compensation'] = 0.0
        camera_cfg['z_compensation'] = 0.0

        handeye_cfg = result.setdefault('calibration', {}).setdefault('handeye', {})
        handeye_cfg['calibration_time'] = ts
        handeye_cfg['reprojection_error'] = float(mean_reproj)
        handeye_cfg['method'] = 'OpenCV_Tsai'
        handeye_cfg['n_frames'] = len(self.captured_frames)
        handeye_cfg['mode'] = self.mode

        log_dir = os.path.expanduser('~/Workspace/calibration_log/auto_handeye')
        os.makedirs(log_dir, exist_ok=True)
        result_path = os.path.join(log_dir, f'result_{ts}.yaml')

        with open(result_path, 'w') as f:
            yaml.dump(result, f, default_flow_style=False, sort_keys=False)

        self.get_logger().info(f'Saved: {result_path}')
        self.get_logger().info('=' * 60)
        self.get_logger().info('DONE! Saved a vision.yaml-compatible result file.')
        cv2.destroyAllWindows()
        self._restore_prepare_mode()
        if rclpy.ok():
            rclpy.shutdown()

    def _reset(self):
        self.captured_frames.clear()
        self.prev_board_poses.clear()
        self.board_position_mask = None
        self.last_capture_time = 0.0
        if self.mode == 'auto':
            self.sweep_idx = 0
            self.sweep_phase = 'init'
            self.head_cmd_sent = False
            self.auto_calib_done = False


def discover_api_id():
    """Sniff /LocoApiTopicReq for kRotateHead API ID.
    User moves head with gamepad once, we print the api_id."""
    import json as _json
    if not ensure_booster_msgs_available():
        return

    from booster_msgs.msg import RpcReqMsg

    seen_ids = set()

    class Sniffer(Node):
        def __init__(self):
            super().__init__('api_id_sniffer')
            self.sub = self.create_subscription(
                RpcReqMsg, 'LocoApiTopicReq', self._cb, 10)
            self.get_logger().info('👂 Listening on /LocoApiTopicReq ...')
            self.get_logger().info('   Move the robot head with the gamepad NOW.')

        def _cb(self, msg):
            try:
                hdr = _json.loads(msg.header)
                api = hdr.get('api_id')
                if api is not None and api not in seen_ids:
                    seen_ids.add(api)
                    body_str = msg.body[:120]
                    self.get_logger().info(f'  api_id={api}  body={body_str}')
                    if 'pitch' in body_str.lower() or 'yaw' in body_str.lower():
                        self.get_logger().info(f'')
                        self.get_logger().info(f'✅ kRotateHead api_id = {api}')
                        self.get_logger().info(f'   Run: python3 auto_handeye_calib.py --config <cfg> --api-id {api}')
                        self.get_logger().info(f'')
                        rclpy.shutdown()
            except Exception:
                pass

    rclpy.init()
    node = Sniffer()
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Auto Hand-Eye Calibration')
    parser.add_argument('--config', default='', help='Path to vision.yaml')
    parser.add_argument('--mode', choices=['auto', 'semi'], default='auto',
                        help='auto=head sweep, semi=manual head+auto capture')
    parser.add_argument('--api-id', type=int, default=None,
                        help='LocoApiId::kRotateHead numeric value')
    parser.add_argument('--discover', action='store_true',
                        help='Sniff /LocoApiTopicReq to find kRotateHead api_id (move head with gamepad)')
    parser.add_argument('--board-w', type=int, default=11)
    parser.add_argument('--board-h', type=int, default=8)
    parser.add_argument('--square-size', type=float, default=0.05)
    parser.add_argument('--image-topic', default='',
                        help=f'Raw Image topic override (default: {DEFAULT_COLOR_TOPIC})')
    parser.add_argument('--camera-info-topic', default='',
                        help=f'CameraInfo topic override (default: {DEFAULT_CAMERA_INFO_TOPIC})')
    parser.add_argument('--compressed-topic', default='',
                        help='Optional CompressedImage topic fallback; disabled by default')
    args = parser.parse_args()

    if args.discover:
        ensure_booster_msgs_available()
        discover_api_id()
        return

    if args.mode == 'auto' and args.api_id is not None:
        ensure_booster_msgs_available()

    rclpy.init()
    node = AutoHandEyeCalib(
        config_path=args.config,
        mode=args.mode,
        api_id=args.api_id,
        board_w=args.board_w,
        board_h=args.board_h,
        square_size=args.square_size,
        image_topic=args.image_topic or None,
        camera_info_topic=args.camera_info_topic or None,
        compressed_topic=args.compressed_topic or None,
    )

    if args.mode == 'auto' and args.api_id is None:
        print()
        print('╔══════════════════════════════════════════════════════════════╗')
        print('║  ⚠️  --api-id not set!                                    ║')
        print('║                                                          ║')
        print('║  Step 1 - Discover the ID (on the robot):                ║')
        print('║    python3 auto_handeye_calib.py --discover              ║')
        print('║    → then move the head with gamepad once                ║')
        print('║                                                          ║')
        print('║  Step 2 - Run full-auto with the discovered ID:          ║')
        print(f'║    python3 auto_handeye_calib.py --config {args.config}')
        print('║    --api-id <NUMBER>                                     ║')
        print('║                                                          ║')
        print('║  (Falling back to SEMI-AUTO — head controlled by you)    ║')
        print('╚══════════════════════════════════════════════════════════╝')
        print()
        node.mode = 'semi'

    if node.mode == 'auto' and not node.prepare_auto_control():
        node.mode = 'semi'

    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node._restore_prepare_mode()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
