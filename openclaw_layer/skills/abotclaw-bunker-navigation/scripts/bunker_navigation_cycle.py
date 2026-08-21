#!/usr/bin/env python3
"""Named-goal Bunker navigation and door-arrival manipulation coordinator."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger


SUCCESS = {"succeeded", "done", "finished", "success", "manipulation_succeeded"}
FAILURE = {"failed", "failure", "aborted", "canceled", "cancelled", "rejected"}


def decode(data: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except json.JSONDecodeError:
        return {"text": data, "status": data.strip().lower()}
    return value if isinstance(value, dict) else {"value": value}


def status_of(event: dict[str, Any]) -> str:
    for key in ("status", "state", "result", "event"):
        value = event.get(key)
        if isinstance(value, str):
            return value.strip().lower()
    return ""


def emit(success: bool, state: str, message: str, finished: bool = True, **details: Any) -> None:
    print(json.dumps({
        "success": success,
        "finished": finished,
        "state": state,
        "message": message,
        **details,
    }, sort_keys=True))


class NavigationNode(Node):
    def __init__(self) -> None:
        super().__init__("abotclaw_bunker_navigation_cycle")
        self.goal_pub = self.create_publisher(
            String, "/landmark_navigator/go_marker", 10
        )
        self.home_client = self.create_client(
            Trigger, "/landmark_navigator/go_home"
        )
        self.door_arrival: dict[str, Any] | None = None
        self.generic_arrival: dict[str, Any] | None = None
        self.manipulation: dict[str, Any] | None = None
        self.create_subscription(
            String, "/door_navigation/arrived", self._door_callback, 10
        )
        self.create_subscription(
            String, "/landmark_navigator/arrived", self._arrival_callback, 10
        )
        for topic in (
            "/manipulation_task/progress",
            "/navigation_manipulation/progress",
        ):
            self.create_subscription(String, topic, self._progress_callback, 10)

    def _door_callback(self, message: String) -> None:
        if message.data.strip() == "arrived_at_door":
            self.door_arrival = {
                "landmark": "door",
                "status": "succeeded",
                "legacy": True,
            }

    def _arrival_callback(self, message: String) -> None:
        event = decode(message.data)
        if event.get("landmark") in {"door", "home"}:
            self.generic_arrival = event

    def _progress_callback(self, message: String) -> None:
        event = decode(message.data)
        status = status_of(event)
        if status:
            self.manipulation = {**event, "status": status}

    def publish_landmark(self, landmark: str, wait_timeout_s: float = 8.0) -> bool:
        deadline = time.monotonic() + wait_timeout_s
        while self.goal_pub.get_subscription_count() < 1 and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        if self.goal_pub.get_subscription_count() < 1:
            return False
        message = String()
        message.data = landmark
        self.goal_pub.publish(message)
        rclpy.spin_once(self, timeout_sec=0.2)
        return True

    def call_home_service(self, timeout_s: float) -> tuple[bool, str]:
        if not self.home_client.wait_for_service(timeout_sec=timeout_s):
            return False, "landmark_navigator/go_home service unavailable"
        future = self.home_client.call_async(Trigger.Request())
        deadline = time.monotonic() + timeout_s
        while not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not future.done() or future.result() is None:
            return False, "landmark_navigator/go_home service timed out"
        response = future.result()
        return bool(response.success), response.message

    def health(self, discovery_timeout_s: float = 8.0) -> dict[str, Any]:
        # DDS discovery can expose the topic subscriber before it exposes all
        # Nav2 node names. Keep spinning until the graph settles or the timeout
        # expires instead of treating a transient graph as a failure.
        deadline = time.monotonic() + max(0.5, discovery_timeout_s)
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            topics = {name for name, _types in self.get_topic_names_and_types()}
            nodes = {name for name, _namespace in self.get_node_names_and_namespaces()}
            if (
                "/landmark_navigator/go_marker" in topics
                and {"bt_navigator", "controller_server", "planner_server"}.issubset(nodes)
                and "/navigate_to_pose/_action/status" in topics
            ):
                break
        topics = {name for name, _types in self.get_topic_names_and_types()}
        services = {name for name, _types in self.get_service_names_and_types()}
        nodes = {name for name, _namespace in self.get_node_names_and_namespaces()}
        go_marker_subscriber_visible = bool(
            self.get_subscriptions_info_by_topic("/landmark_navigator/go_marker")
        )
        required_topics = {"/landmark_navigator/go_marker"}
        progress_topics = {
            "/manipulation_task/progress",
            "/navigation_manipulation/progress",
        }
        navigation_action_status = "/navigate_to_pose/_action/status" in topics
        result = {
            "ros_ok": True,
            "required_topics_visible": sorted(required_topics & topics),
            "missing_topic_names": sorted(required_topics - topics),
            "go_marker_subscriber_visible": go_marker_subscriber_visible,
            "navigation_action_status_visible": navigation_action_status,
            "door_arrival_visible": "/door_navigation/arrived" in topics,
            "progress_topics_visible": sorted(progress_topics & topics),
            "progress_topic_missing": not bool(progress_topics & topics),
            "go_home_service_visible": "/landmark_navigator/go_home" in services,
            "generic_arrival_visible": "/landmark_navigator/arrived" in topics,
            "landmark_navigator_node_visible": "landmark_navigator" in nodes,
            "nav2_nodes_visible": sorted(
                name for name in (
                    "bt_navigator",
                    "controller_server",
                    "planner_server",
                    "lifecycle_manager_navigation",
                ) if name in nodes
            ),
        }
        # A named landmark command only needs a live landmark navigator
        # subscriber. Nav2/action checks are reported separately for cycle.
        result["command_ready"] = (
            not result["missing_topic_names"]
            and result["go_marker_subscriber_visible"]
        )
        result["nav2_stack_ready"] = (
            result["command_ready"]
            and {"bt_navigator", "controller_server", "planner_server"}.issubset(
                result["nav2_nodes_visible"]
            )
            and result["navigation_action_status_visible"]
        )
        result["ready_for_navigation"] = result["command_ready"]
        result["ready_for_cycle"] = (
            result["nav2_stack_ready"]
            and (result["generic_arrival_visible"] or result["door_arrival_visible"])
            and not result["progress_topic_missing"]
        )
        return result

    def wait_for_door(self, timeout_s: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            if self.door_arrival:
                return self.door_arrival
            event = self.generic_arrival
            if event and event.get("landmark") == "door":
                status = status_of(event)
                if status == "succeeded" or status in FAILURE:
                    return event
        return None

    def wait_for_manipulation(self, timeout_s: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            if self.manipulation and self.manipulation["status"] in SUCCESS | FAILURE:
                return self.manipulation
        return None

    def wait_for_home(self, timeout_s: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            event = self.generic_arrival
            if event and event.get("landmark") == "home":
                return event
        return None


def run(args: argparse.Namespace) -> int:
    rclpy.init()
    node = NavigationNode()
    try:
        if args.command == "health":
            result = node.health(args.discovery_timeout_s)
            print(json.dumps(result, sort_keys=True))
            return 0 if result["ready_for_navigation"] else 2

        if args.command == "go-marker":
            if args.landmark not in {"home", "door"}:
                emit(False, "FAILED", "unknown landmark", landmark=args.landmark)
                return 2
            if not node.publish_landmark(args.landmark):
                emit(False, "FAILED", "landmark navigator subscriber was not discovered", landmark=args.landmark)
                return 2
            emit(True, "NAVIGATION_STARTED", "landmark goal published; waiting for arrival event", finished=False, landmark=args.landmark)
            return 0

        if args.command == "go-home":
            success, message = node.call_home_service(args.timeout_s)
            emit(success, "GOAL_SENT" if success else "FAILED", message)
            return 0 if success else 2

        health = node.health()
        if not health["ready_for_cycle"]:
            emit(False, "FAILED", "cycle prerequisites are not ready", health=health)
            return 2

        if not node.publish_landmark("door"):
            emit(False, "FAILED", "landmark navigator subscriber was not discovered")
            return 2
        door = node.wait_for_door(args.timeout_s)
        if not door:
            emit(False, "FAILED", "door arrival was not confirmed")
            return 3
        if status_of(door) in FAILURE or door.get("_failure"):
            emit(False, "FAILED", "navigation to door failed", arrival=door)
            return 3

        node.manipulation = None
        manipulation = node.wait_for_manipulation(args.timeout_s)
        if not manipulation:
            emit(False, "FAILED", "manipulation completion was not reported", arrival=door)
            return 4
        if manipulation["status"] in FAILURE:
            emit(False, "FAILED", "manipulation failed", progress=manipulation)
            return 4

        node.generic_arrival = None
        if not node.publish_landmark("home"):
            emit(False, "FAILED", "landmark navigator subscriber was not discovered")
            return 2
        home = node.wait_for_home(args.timeout_s)
        if not home:
            emit(
                False,
                "HOME_ARRIVAL_UNCONFIRMED",
                "home goal sent but generic home arrival was not confirmed",
            )
            return 5
        if status_of(home) in FAILURE:
            emit(False, "FAILED", "navigation to home failed", arrival=home)
            return 3
        emit(
            True,
            "IDLE_AT_HOME",
            "navigation/manipulation cycle completed",
            door_arrival=door,
            manipulation=manipulation,
            home_arrival=home,
        )
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("health", "go-marker", "go-home", "cycle"))
    parser.add_argument("landmark", nargs="?")
    parser.add_argument("--timeout-s", type=float, default=300.0)
    parser.add_argument("--discovery-timeout-s", type=float, default=8.0)
    args = parser.parse_args()
    if args.command == "go-marker" and not args.landmark:
        parser.error("go-marker requires home or door")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
