#!/usr/bin/env python3

import argparse
import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState, PointCloud2
from geometry_msgs.msg import PoseStamped
from trajectory_msgs.msg import JointTrajectoryPoint
import uvicorn

from piper_x_aruco_wall_approach.srv import RunMarkerTask


def execution_allowed_from_env() -> bool:
    return os.environ.get("PIPER_TOUCH_ALLOW_EXECUTION", "").strip().lower() in {"1", "true"}


def token_from_env() -> Optional[str]:
    token = os.environ.get("PIPER_TOUCH_API_TOKEN", "").strip()
    return token or None


class MarkerTaskRequest(BaseModel):
    execute: bool = False
    pre_clearance_m: float = Field(default=0.05)
    final_clearance_m: float = Field(default=0.005)
    retract_after: bool = True
    retract_distance_m: float = Field(default=0.05)
    final_velocity_scaling: float = Field(default=0.05)
    return_home_after: bool = False
    home_duration_s: float = Field(default=6.0)


class HomeRequest(BaseModel):
    execute: bool = False
    duration_s: float = Field(default=6.0)


class SaveHomeRequest(BaseModel):
    pose_name: str = Field(default="home")


@dataclass
class HealthSnapshot:
    ros_ok: bool
    marker_pose_available: bool
    point_cloud_available: bool
    moveit_available: bool
    marker_task_service_available: bool
    home_action_available: bool
    joint_state_available: bool
    configured_marker_id: int
    configured_marker_size_m: float
    execution_allowed: bool
    marker_pose_age_s: Optional[float] = None
    point_cloud_age_s: Optional[float] = None
    marker_pose_header_age_s: Optional[float] = None
    point_cloud_header_age_s: Optional[float] = None
    joint_state_age_s: Optional[float] = None
    joint_state_header_age_s: Optional[float] = None
    marker_timeout_s: Optional[float] = None
    point_cloud_timeout_s: Optional[float] = None
    joint_state_timeout_s: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        status_value = "ready" if (
            self.ros_ok
            and self.marker_pose_available
            and self.point_cloud_available
            and self.moveit_available
            and self.marker_task_service_available
            and self.home_action_available
            and self.joint_state_available
        ) else "not_ready"
        return {
            "status": status_value,
            "ros_ok": self.ros_ok,
            "marker_pose_available": self.marker_pose_available,
            "point_cloud_available": self.point_cloud_available,
            "moveit_available": self.moveit_available,
            "marker_task_service_available": self.marker_task_service_available,
            "home_action_available": self.home_action_available,
            "joint_state_available": self.joint_state_available,
            "configured_marker_id": self.configured_marker_id,
            "configured_marker_size_m": self.configured_marker_size_m,
            "execution_allowed": self.execution_allowed,
            "marker_pose_age_s": self.marker_pose_age_s,
            "point_cloud_age_s": self.point_cloud_age_s,
            "marker_pose_header_age_s": self.marker_pose_header_age_s,
            "point_cloud_header_age_s": self.point_cloud_header_age_s,
            "joint_state_age_s": self.joint_state_age_s,
            "joint_state_header_age_s": self.joint_state_header_age_s,
            "marker_timeout_s": self.marker_timeout_s,
            "point_cloud_timeout_s": self.point_cloud_timeout_s,
            "joint_state_timeout_s": self.joint_state_timeout_s,
        }


class RosMarkerTaskAdapter:
    def health(self) -> HealthSnapshot:
        raise NotImplementedError

    def run_task(self, mode: str, request: MarkerTaskRequest) -> Dict[str, Any]:
        raise NotImplementedError

    def go_home(self, request: HomeRequest) -> Dict[str, Any]:
        raise NotImplementedError

    def save_home(self, request: SaveHomeRequest) -> Dict[str, Any]:
        raise NotImplementedError


class MarkerTaskBridge(Node, RosMarkerTaskAdapter):
    def __init__(
        self,
        marker_pose_topic: str,
        point_cloud_topic: str,
        marker_id: int,
        marker_size_m: float,
        marker_timeout_s: float,
        point_cloud_timeout_s: float,
        home_pose_file: str,
        joint_state_topic: str,
        joint_state_timeout_s: float,
    ):
        super().__init__("piper_touch_marker_api_bridge")
        self.marker_pose_topic = marker_pose_topic
        self.point_cloud_topic = point_cloud_topic
        self.marker_id = marker_id
        self.marker_size_m = marker_size_m
        self.marker_timeout_s = marker_timeout_s
        self.point_cloud_timeout_s = point_cloud_timeout_s
        self.joint_state_topic = joint_state_topic
        self.joint_state_timeout_s = joint_state_timeout_s
        self.home_pose_file = str(Path(home_pose_file).expanduser())
        self.home_joint_names, self.home_positions = self._load_home_pose(self.home_pose_file)
        self._marker_received_monotonic_s: Optional[float] = None
        self._cloud_received_monotonic_s: Optional[float] = None
        self._joint_state_received_monotonic_s: Optional[float] = None
        self._marker_header_stamp_s: Optional[float] = None
        self._cloud_header_stamp_s: Optional[float] = None
        self._joint_state_header_stamp_s: Optional[float] = None
        self._latest_joint_state: Optional[JointState] = None
        self._lock = threading.Lock()
        self._client = self.create_client(RunMarkerTask, "/run_marker_task")
        self._home_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory",
        )
        self.create_subscription(PoseStamped, marker_pose_topic, self._marker_callback, 10)
        self.create_subscription(PointCloud2, point_cloud_topic, self._cloud_callback, 10)
        self.create_subscription(JointState, joint_state_topic, self._joint_state_callback, 10)

    @staticmethod
    def _default_home_pose_file() -> str:
        return str(
            Path(get_package_share_directory("piper_x_aruco_wall_approach"))
            / "config"
            / "piper_x_home_pose.yaml"
        )

    @staticmethod
    def _load_home_pose(path: str):
        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        joint_state = data.get("joint_state", {})
        names = list(joint_state.get("names", []))
        positions = list(joint_state.get("positions_rad", []))
        if len(names) != len(positions):
            raise ValueError(f"home pose has mismatched names/positions: {path}")
        selected = [
            (name, float(position))
            for name, position in zip(names, positions)
            if str(name).startswith("joint")
        ]
        if [name for name, _ in selected] != ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]:
            raise ValueError(f"home pose must contain joint1..joint6 in order: {path}")
        return [name for name, _ in selected], [position for _, position in selected]

    @staticmethod
    def _stamp_to_seconds(msg: Any) -> Optional[float]:
        stamp = getattr(getattr(msg, "header", None), "stamp", None)
        if stamp is None:
            return None
        return float(stamp.sec) + float(stamp.nanosec) * 1e-9

    def _marker_callback(self, msg: PoseStamped) -> None:
        with self._lock:
            self._marker_received_monotonic_s = time.monotonic()
            self._marker_header_stamp_s = self._stamp_to_seconds(msg)

    def _cloud_callback(self, msg: PointCloud2) -> None:
        with self._lock:
            self._cloud_received_monotonic_s = time.monotonic()
            self._cloud_header_stamp_s = self._stamp_to_seconds(msg)

    def _joint_state_callback(self, msg: JointState) -> None:
        with self._lock:
            self._latest_joint_state = msg
            self._joint_state_received_monotonic_s = time.monotonic()
            self._joint_state_header_stamp_s = self._stamp_to_seconds(msg)

    def health(self) -> HealthSnapshot:
        now_monotonic_s = time.monotonic()
        now_wall_s = time.time()
        with self._lock:
            marker_received_monotonic_s = self._marker_received_monotonic_s
            cloud_received_monotonic_s = self._cloud_received_monotonic_s
            joint_state_received_monotonic_s = self._joint_state_received_monotonic_s
            marker_header_stamp_s = self._marker_header_stamp_s
            cloud_header_stamp_s = self._cloud_header_stamp_s
            joint_state_header_stamp_s = self._joint_state_header_stamp_s
        marker_age_s = (
            now_monotonic_s - marker_received_monotonic_s
            if marker_received_monotonic_s is not None
            else None
        )
        cloud_age_s = (
            now_monotonic_s - cloud_received_monotonic_s
            if cloud_received_monotonic_s is not None
            else None
        )
        joint_state_age_s = (
            now_monotonic_s - joint_state_received_monotonic_s
            if joint_state_received_monotonic_s is not None
            else None
        )
        marker_header_age_s = (
            now_wall_s - marker_header_stamp_s
            if marker_header_stamp_s is not None
            else None
        )
        cloud_header_age_s = (
            now_wall_s - cloud_header_stamp_s
            if cloud_header_stamp_s is not None
            else None
        )
        joint_state_header_age_s = (
            now_wall_s - joint_state_header_stamp_s
            if joint_state_header_stamp_s is not None
            else None
        )
        marker_fresh = marker_age_s is not None and marker_age_s <= self.marker_timeout_s
        cloud_fresh = cloud_age_s is not None and cloud_age_s <= self.point_cloud_timeout_s
        joint_state_fresh = (
            joint_state_age_s is not None
            and joint_state_age_s <= self.joint_state_timeout_s
        )
        names_and_types = dict(self.get_service_names_and_types())
        moveit_available = (
            "/move_action/_action/send_goal" in names_and_types
            or "/plan_kinematic_path" in names_and_types
        )
        home_action_available = "/arm_controller/follow_joint_trajectory/_action/send_goal" in names_and_types
        return HealthSnapshot(
            ros_ok=rclpy.ok(),
            marker_pose_available=marker_fresh,
            point_cloud_available=cloud_fresh,
            moveit_available=moveit_available,
            marker_task_service_available=self._client.service_is_ready(),
            home_action_available=home_action_available,
            joint_state_available=joint_state_fresh,
            configured_marker_id=self.marker_id,
            configured_marker_size_m=self.marker_size_m,
            execution_allowed=execution_allowed_from_env(),
            marker_pose_age_s=marker_age_s,
            point_cloud_age_s=cloud_age_s,
            marker_pose_header_age_s=marker_header_age_s,
            point_cloud_header_age_s=cloud_header_age_s,
            joint_state_age_s=joint_state_age_s,
            joint_state_header_age_s=joint_state_header_age_s,
            marker_timeout_s=self.marker_timeout_s,
            point_cloud_timeout_s=self.point_cloud_timeout_s,
            joint_state_timeout_s=self.joint_state_timeout_s,
        )

    def run_task(self, mode: str, request: MarkerTaskRequest) -> Dict[str, Any]:
        if not self._client.wait_for_service(timeout_sec=1.0):
            raise RuntimeError("ROS service /run_marker_task is not available")

        service_request = RunMarkerTask.Request()
        service_request.mode = mode
        service_request.execute = request.execute
        service_request.pre_clearance_m = request.pre_clearance_m
        service_request.final_clearance_m = request.final_clearance_m
        service_request.retract_distance_m = request.retract_distance_m
        service_request.final_velocity_scaling = request.final_velocity_scaling
        service_request.retract_after = request.retract_after

        future = self._client.call_async(service_request)
        deadline = time.monotonic() + 120.0
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not future.done():
            raise TimeoutError("timed out waiting for /run_marker_task response")
        response = future.result()
        if response is None:
            raise RuntimeError("ROS service /run_marker_task returned no response")
        return {
            "success": bool(response.success),
            "stage": str(response.stage),
            "message": str(response.message),
            "contact_confirmed": bool(response.contact_confirmed),
            "completion_type": str(response.completion_type),
        }

    def go_home(self, request: HomeRequest) -> Dict[str, Any]:
        if not self._home_client.wait_for_server(timeout_sec=1.0):
            raise RuntimeError("action /arm_controller/follow_joint_trajectory is not available")
        if not request.execute:
            return {
                "success": True,
                "stage": "complete",
                "message": "home pose command is ready (execute=false)",
                "contact_confirmed": False,
                "completion_type": "saved_home_pose",
            }

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(self.home_joint_names)
        point = JointTrajectoryPoint()
        point.positions = list(self.home_positions)
        point.velocities = [0.0] * len(self.home_positions)
        duration = float(request.duration_s)
        point.time_from_start = Duration(
            sec=int(duration),
            nanosec=int((duration - int(duration)) * 1_000_000_000),
        )
        goal.trajectory.points = [point]
        goal.goal_time_tolerance = Duration(sec=2, nanosec=0)

        send_future = self._home_client.send_goal_async(goal)
        deadline = time.monotonic() + 10.0
        while rclpy.ok() and not send_future.done() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not send_future.done():
            raise TimeoutError("timed out sending home trajectory goal")
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError("home trajectory goal was rejected")

        result_future = goal_handle.get_result_async()
        deadline = time.monotonic() + max(20.0, request.duration_s + 10.0)
        while rclpy.ok() and not result_future.done() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not result_future.done():
            raise TimeoutError("timed out waiting for home trajectory result")
        result = result_future.result()
        if result is None:
            raise RuntimeError("home trajectory returned no result")
        error_code = int(result.result.error_code)
        if error_code != 0:
            return {
                "success": False,
                "stage": "home_execution",
                "message": f"home trajectory failed with error_code={error_code}",
                "contact_confirmed": False,
                "completion_type": "saved_home_pose",
            }
        return {
            "success": True,
            "stage": "complete",
            "message": "home trajectory completed",
            "contact_confirmed": False,
            "completion_type": "saved_home_pose",
        }

    def save_home(self, request: SaveHomeRequest) -> Dict[str, Any]:
        if request.pose_name != "home":
            raise ValueError("only pose_name='home' is supported")
        now_monotonic_s = time.monotonic()
        with self._lock:
            joint_state = self._latest_joint_state
            received_monotonic_s = self._joint_state_received_monotonic_s
        if joint_state is None or received_monotonic_s is None:
            raise RuntimeError(f"no joint state has been received on {self.joint_state_topic}")
        age_s = now_monotonic_s - received_monotonic_s
        if age_s > self.joint_state_timeout_s:
            raise RuntimeError(
                f"latest joint state is stale: age_s={age_s:.3f}, timeout_s={self.joint_state_timeout_s:.3f}"
            )

        joint_positions = dict(zip(joint_state.name, joint_state.position))
        joint_names = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
        missing = [name for name in joint_names if name not in joint_positions]
        if missing:
            raise RuntimeError(f"joint state missing required joints: {missing}")
        positions = [float(joint_positions[name]) for name in joint_names]
        names = list(joint_names)
        saved_positions = list(positions)
        if "gripper" in joint_positions:
            names.append("gripper")
            saved_positions.append(float(joint_positions["gripper"]))

        stamp_s = self._stamp_to_seconds(joint_state)
        stamp_sec = int(stamp_s) if stamp_s is not None else 0
        stamp_nanosec = int((stamp_s - stamp_sec) * 1_000_000_000) if stamp_s is not None else 0
        path = Path(self.home_pose_file).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "pose_name": "home",
            "updated_by": "piper_touch_marker_api_save_home",
            "captured_at_wall_time_s": time.time(),
            "captured_at_ros_time": {
                "sec": stamp_sec,
                "nanosec": stamp_nanosec,
            },
            "source_topic": self.joint_state_topic,
            "source_type": "sensor_msgs/msg/JointState",
            "arm": {
                "arm_type": "piper_x",
                "effector_type": "agx_gripper",
                "can_port": "can0",
            },
            "moveit": {
                "planning_group": "arm",
                "tip_link": "tcp_link",
                "tcp_offset": [0.0, 0.0, 0.1425, 0.0, 0.0, 0.0],
            },
            "joint_state": {
                "names": names,
                "positions_rad": saved_positions,
            },
        }
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data, file, sort_keys=False)
        os.replace(tmp_path, path)

        self.home_joint_names = joint_names
        self.home_positions = positions
        return {
            "success": True,
            "stage": "complete",
            "message": f"saved current pose as home: {path}",
            "contact_confirmed": False,
            "completion_type": "saved_home_pose_update",
            "home_pose_file": str(path),
            "joint_names": joint_names,
            "positions_rad": positions,
        }


class FakeUnavailableAdapter(RosMarkerTaskAdapter):
    def health(self) -> HealthSnapshot:
        return HealthSnapshot(False, False, False, False, False, False, False, 6, 0.10, execution_allowed_from_env())

    def run_task(self, mode: str, request: MarkerTaskRequest) -> Dict[str, Any]:
        raise RuntimeError("ROS adapter not initialized")

    def go_home(self, request: HomeRequest) -> Dict[str, Any]:
        raise RuntimeError("ROS adapter not initialized")

    def save_home(self, request: SaveHomeRequest) -> Dict[str, Any]:
        raise RuntimeError("ROS adapter not initialized")


def create_app(adapter: RosMarkerTaskAdapter, api_token: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="PiPER-X Touch Marker API", version="0.1.0")
    command_lock = threading.Lock()

    def validate_request(mode: str, request: MarkerTaskRequest) -> None:
        if mode not in {"approach", "touch"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported mode: {mode}")
        if not math.isfinite(request.pre_clearance_m) or request.pre_clearance_m < 0.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pre_clearance_m must be finite and non-negative",
            )
        if mode == "touch":
            if not math.isfinite(request.final_clearance_m) or request.final_clearance_m < 0.003:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="final_clearance_m must be finite and at least 0.003 m",
                )
            if request.final_clearance_m > request.pre_clearance_m:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="final_clearance_m must be less than or equal to pre_clearance_m",
                )
            if request.pre_clearance_m - request.final_clearance_m > 0.06:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="final travel exceeds maximum of 0.06 m",
                )
            if not math.isfinite(request.retract_distance_m) or request.retract_distance_m < 0.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="retract_distance_m must be finite and non-negative",
                )
            if (
                not math.isfinite(request.final_velocity_scaling)
                or request.final_velocity_scaling <= 0.0
                or request.final_velocity_scaling > 0.25
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="final_velocity_scaling must be in (0.0, 0.25]",
                )
        if request.return_home_after:
            validate_home_request(HomeRequest(execute=request.execute, duration_s=request.home_duration_s))

    def validate_home_request(request: HomeRequest) -> None:
        if not math.isfinite(request.duration_s) or request.duration_s <= 0.0 or request.duration_s > 30.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duration_s must be finite and in (0.0, 30.0]",
            )

    def require_auth(request: Request, authorization: Optional[str] = Header(default=None)) -> None:
        if api_token is None:
            if request.client and request.client.host in {"127.0.0.1", "::1", "localhost", "testclient"}:
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="remote access requires PIPER_TOUCH_API_TOKEN",
            )
        expected = f"Bearer {api_token}"
        if authorization != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")

    @app.get("/health")
    def health(_: None = Depends(require_auth)) -> Dict[str, Any]:
        return adapter.health().as_dict()

    def run_endpoint(mode: str, request: MarkerTaskRequest) -> Dict[str, Any]:
        validate_request(mode, request)
        health_snapshot = adapter.health()
        if request.execute and not health_snapshot.execution_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="physical execution is disabled; set PIPER_TOUCH_ALLOW_EXECUTION=1",
            )
        if not health_snapshot.marker_task_service_available:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="marker task service unavailable")
        if not health_snapshot.marker_pose_available:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ArUco marker pose unavailable")
        if not health_snapshot.point_cloud_available:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RealSense point cloud unavailable")
        if not health_snapshot.moveit_available:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MoveIt is unavailable")
        if request.execute and request.return_home_after and not health_snapshot.home_action_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="home trajectory action unavailable",
            )
        if not command_lock.acquire(blocking=False):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="another PiPER marker task is active")
        try:
            result = adapter.run_task(mode, request)
            if result.get("success", False) and request.execute and request.return_home_after:
                home_result = adapter.go_home(HomeRequest(execute=True, duration_s=request.home_duration_s))
                result["return_home_after"] = home_result
                if not home_result.get("success", False):
                    result = {
                        "success": False,
                        "stage": "home_after_marker",
                        "message": home_result.get("message", "home after marker failed"),
                        "contact_confirmed": False,
                        "completion_type": result.get("completion_type", "geometric_surface_approach"),
                        "marker_task": result,
                        "return_home_after": home_result,
                    }
        except TimeoutError as exc:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        finally:
            command_lock.release()
        if not result.get("success", False):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result)
        return result

    def run_save_home_endpoint(request: SaveHomeRequest) -> Dict[str, Any]:
        if request.pose_name != "home":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only pose_name='home' is supported")
        health_snapshot = adapter.health()
        if not health_snapshot.joint_state_available:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="fresh joint state unavailable")
        if not command_lock.acquire(blocking=False):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="another PiPER marker task is active")
        try:
            result = adapter.save_home(request)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        finally:
            command_lock.release()
        if not result.get("success", False):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result)
        return result

    def run_home_endpoint(request: HomeRequest) -> Dict[str, Any]:
        validate_home_request(request)
        health_snapshot = adapter.health()
        if request.execute and not health_snapshot.execution_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="physical execution is disabled; set PIPER_TOUCH_ALLOW_EXECUTION=1",
            )
        if not health_snapshot.home_action_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="home trajectory action unavailable",
            )
        if not command_lock.acquire(blocking=False):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="another PiPER marker task is active")
        try:
            result = adapter.go_home(request)
        except TimeoutError as exc:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        finally:
            command_lock.release()
        if not result.get("success", False):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result)
        return result

    @app.post("/tools/piper/approach-marker")
    def approach_marker(
        request: MarkerTaskRequest,
        _: None = Depends(require_auth),
    ) -> Dict[str, Any]:
        return run_endpoint("approach", request)

    @app.post("/tools/piper/touch-marker")
    def touch_marker(
        request: MarkerTaskRequest,
        _: None = Depends(require_auth),
    ) -> Dict[str, Any]:
        return run_endpoint("touch", request)

    @app.post("/tools/piper/go-home")
    def go_home(
        request: HomeRequest,
        _: None = Depends(require_auth),
    ) -> Dict[str, Any]:
        return run_home_endpoint(request)

    @app.post("/tools/piper/save-home")
    def save_home(
        request: SaveHomeRequest,
        _: None = Depends(require_auth),
    ) -> Dict[str, Any]:
        return run_save_home_endpoint(request)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTP bridge for PiPER-X ArUco marker approach.")
    parser.add_argument("--host", default=os.environ.get("PIPER_TOUCH_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PIPER_TOUCH_API_PORT", "8892")))
    parser.add_argument("--marker-pose-topic", default="/aruco_single/pose")
    parser.add_argument("--point-cloud-topic", default="/camera/camera/depth/color/points")
    parser.add_argument("--marker-id", type=int, default=6)
    parser.add_argument("--marker-size-m", type=float, default=0.10)
    parser.add_argument("--marker-timeout-s", type=float, default=1.0)
    parser.add_argument("--point-cloud-timeout-s", type=float, default=2.0)
    parser.add_argument("--home-pose-file", default=MarkerTaskBridge._default_home_pose_file())
    parser.add_argument("--joint-state-topic", default="/feedback/joint_states")
    parser.add_argument("--joint-state-timeout-s", type=float, default=1.0)
    args, _ros_args = parser.parse_known_args()

    rclpy.init()
    adapter = MarkerTaskBridge(
        marker_pose_topic=args.marker_pose_topic,
        point_cloud_topic=args.point_cloud_topic,
        marker_id=args.marker_id,
        marker_size_m=args.marker_size_m,
        marker_timeout_s=args.marker_timeout_s,
        point_cloud_timeout_s=args.point_cloud_timeout_s,
        home_pose_file=args.home_pose_file,
        joint_state_topic=args.joint_state_topic,
        joint_state_timeout_s=args.joint_state_timeout_s,
    )
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(adapter)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    app = create_app(adapter, api_token=token_from_env())
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    finally:
        executor.shutdown()
        adapter.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
