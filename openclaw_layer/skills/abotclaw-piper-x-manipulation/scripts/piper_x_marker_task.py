#!/usr/bin/env python3
"""Parse OpenClaw text into a bounded PiPER-X Agent Server command."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REPO_ROOT = os.environ.get(
    "ABOTCLAW_REPO_ROOT",
    str(Path(__file__).resolve().parents[4]),
)


@dataclass
class PiperXMarkerTask:
    action: str
    arm: str = "front"
    selected_robot: str = "PiPER-X"

    def runner_args(self, execute: bool = True) -> list[str]:
        base = ["python3", "robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py"]
        arm_args = ["--arm", self.arm]
        if self.action == "approach":
            return base + ["approach", *arm_args, "--execute" if execute else "--plan-only"]
        if self.action == "touch":
            args = base + [
                "touch",
                *arm_args,
                "--retract",
                "--return-home-after",
                "--execute" if execute else "--plan-only",
            ]
            return args
        if self.action == "search":
            return base + ["search", *arm_args, "--execute" if execute else "--plan-only"]
        if self.action == "home":
            return base + ["home", *arm_args, "--execute" if execute else "--plan-only"]
        if self.action == "save-home":
            return base + ["save-home"]
        if self.action == "previous":
            return base + ["previous", *arm_args, "--execute" if execute else "--plan-only"]
        if self.action == "found-marker":
            return base + ["found-marker", *arm_args, "--execute" if execute else "--plan-only"]
        if self.action == "nav-pose":
            return base + ["nav-pose", *arm_args, "--execute" if execute else "--plan-only"]
        if self.action == "save-previous":
            return base + ["save-previous"]
        if self.action == "open-gripper":
            return base + ["open-gripper", "--execute" if execute else "--plan-only"]
        if self.action == "close-gripper":
            return base + ["close-gripper", "--execute" if execute else "--plan-only"]
        return base + ["health"]

    def shell_command(self, execute: bool = True, repo_root: str = DEFAULT_REPO_ROOT) -> str:
        runner = " ".join(shlex.quote(part) for part in self.runner_args(execute))
        return "cd " + shlex.quote(repo_root) + " && " + runner

    def to_dict(self, execute: bool = True, repo_root: str = DEFAULT_REPO_ROOT) -> dict:
        return {
            "action": self.action,
            "arm": self.arm,
            "selected_robot": self.selected_robot,
            "command_text": self.shell_command(execute=execute, repo_root=repo_root),
            "contact_confirmed": False,
            "completion_type": (
                "gripper_width_command"
                if self.action in {"open-gripper", "close-gripper"}
                else (
                    "saved_pose_command"
                    if self.action in {"home", "previous", "found-marker", "nav-pose", "save-home", "save-previous"}
                    else (
                        "marker_search_saved_found_pose"
                        if self.action == "search"
                        else "geometric_surface_approach"
                    )
                )
            ),
        }


def parse_task(message: str) -> PiperXMarkerTask:
    text = re.sub(r"[^a-z0-9\s-]", " ", message.lower())
    text = re.sub(r"\s+", " ", text).strip()
    arm = "rear" if re.search(r"\b(rear|back)\b.*\b(arm|piper)\b|\b(arm|piper)\b.*\b(rear|back)\b", text) else "front"

    if re.search(r"\b(save|remember|update|set)\b.*\b(previous|last)\b.*\b(pose|position)\b", text):
        return PiperXMarkerTask("save-previous", arm=arm)
    if re.search(r"\b(save|remember|update|set)\b.*\b(home|home pose)\b", text):
        return PiperXMarkerTask("save-home", arm=arm)
    if re.search(r"\b(go|return|move)\b.*\b(nav|navigation)\b.*\b(pose|position)\b", text):
        return PiperXMarkerTask("nav-pose", arm=arm)
    if re.search(r"\b(go|return|move)\b.*\bhome\b", text):
        return PiperXMarkerTask("home", arm=arm)
    if re.search(r"\b(go|return|move)\b.*\b(previous|last)\b.*\b(pose|position|place|spot)\b", text):
        return PiperXMarkerTask("previous", arm=arm)
    if re.search(r"\b(go|return|move)\b.*\bback\b", text):
        return PiperXMarkerTask("previous", arm=arm)
    if re.search(r"\b(go|return|move)\b.*\b(found|detected|saved)\b.*\b(marker|aruco)\b.*\b(pose|position|place|spot)\b", text):
        return PiperXMarkerTask("found-marker", arm=arm)
    if re.search(r"\b(go|return|move)\b.*\b(marker|aruco)\b.*\b(found|detected|saved)\b.*\b(pose|position|place|spot)\b", text):
        return PiperXMarkerTask("found-marker", arm=arm)
    if re.search(r"\b(open|release)\b.*\b(gripper|claw|hand)\b", text):
        return PiperXMarkerTask("open-gripper")
    if re.search(r"\b(close|shut)\b.*\b(gripper|claw|hand)\b", text):
        return PiperXMarkerTask("close-gripper")
    if re.search(r"\b(search|find|look|locate|scan)\b.*\b(marker|aruco|tag)\b", text):
        return PiperXMarkerTask("search", arm=arm)
    if re.fullmatch(r"(search|find|look|locate|scan)( for it)?", text):
        return PiperXMarkerTask("search", arm=arm)
    if re.search(r"\b(open|unlock|activate|trigger|press|wave)\b.*\b(door|doorway|entrance|button|sensor)\b", text):
        return PiperXMarkerTask("touch", arm=arm)
    if re.search(r"\b(touch|press|tap|contact)\b", text):
        return PiperXMarkerTask("touch", arm=arm)
    if re.search(r"\b(approach|point|move)\b.*\b(marker|aruco|marked)\b", text):
        return PiperXMarkerTask("approach", arm=arm)
    raise ValueError("No PiPER-X marker/home action found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT)
    args = parser.parse_args()
    task = parse_task(args.message)
    print(
        json.dumps(
            task.to_dict(execute=not args.plan_only, repo_root=args.repo_root),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
