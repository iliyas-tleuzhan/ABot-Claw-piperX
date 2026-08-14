import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PARSER = ROOT / "openclaw_layer/skills/abotclaw-piper-x-manipulation/scripts/piper_x_marker_task.py"


class PiperXMarkerParserTest(unittest.TestCase):
    def parse(self, text):
        output = subprocess.check_output(
            [sys.executable, str(PARSER), text, "--plan-only"],
            text=True,
        )
        return json.loads(output)

    def test_touch_marker_routes_to_piper_x_runner(self):
        parsed = self.parse("touch the aruco marker")
        self.assertEqual(parsed["action"], "touch")
        self.assertEqual(parsed["selected_robot"], "PiPER-X")
        self.assertIn("robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py", parsed["command_text"])
        self.assertIn("touch", parsed["command_text"])
        self.assertIn("--plan-only", parsed["command_text"])

    def test_open_door_routes_to_touch_marker(self):
        for phrase in (
            "open the door",
            "open door",
            "activate the door button",
            "trigger the door sensor",
            "wave at the door sensor",
        ):
            with self.subTest(phrase=phrase):
                parsed = self.parse(phrase)
                self.assertEqual(parsed["action"], "touch")
                self.assertIn("touch", parsed["command_text"])
                self.assertIn("--plan-only", parsed["command_text"])

    def test_search_marker_routes_to_search(self):
        for phrase in (
            "search for the marker",
            "look for the marker",
            "search",
            "find aruco marker",
            "locate the tag",
        ):
            with self.subTest(phrase=phrase):
                parsed = self.parse(phrase)
                self.assertEqual(parsed["action"], "search")
                self.assertIn(" search ", parsed["command_text"])
                self.assertIn("--plan-only", parsed["command_text"])
                self.assertEqual(parsed["completion_type"], "marker_search_saved_found_pose")

    def test_move_to_found_marker_pose_routes_to_saved_pose(self):
        for phrase in (
            "move to the found marker pose",
            "go to saved marker position",
            "return to detected aruco pose",
        ):
            with self.subTest(phrase=phrase):
                parsed = self.parse(phrase)
                self.assertEqual(parsed["action"], "found-marker")
                self.assertIn("found-marker", parsed["command_text"])
                self.assertIn("--plan-only", parsed["command_text"])

    def test_approach_marker_routes_to_approach(self):
        parsed = self.parse("approach the marker")
        self.assertEqual(parsed["action"], "approach")
        self.assertIn("approach", parsed["command_text"])

    def test_home_routes_to_home_endpoint(self):
        parsed = self.parse("go to home pose")
        self.assertEqual(parsed["action"], "home")
        self.assertIn(" home ", parsed["command_text"])

    def test_nav_pose_routes_to_nav_pose_endpoint(self):
        parsed = self.parse("rear arm go nav pose")
        self.assertEqual(parsed["action"], "nav-pose")
        self.assertEqual(parsed["arm"], "rear")
        self.assertIn("nav-pose", parsed["command_text"])
        self.assertIn("--arm rear", parsed["command_text"])

    def test_front_arm_is_default(self):
        parsed = self.parse("front arm search for the marker")
        self.assertEqual(parsed["action"], "search")
        self.assertEqual(parsed["arm"], "front")
        self.assertIn("--arm front", parsed["command_text"])

    def test_save_home_routes_to_non_motion_snapshot(self):
        parsed = self.parse("save current pose as home")
        self.assertEqual(parsed["action"], "save-home")
        self.assertIn("save-home", parsed["command_text"])

    def test_previous_routes_to_previous_endpoint(self):
        parsed = self.parse("go back to previous pose")
        self.assertEqual(parsed["action"], "previous")
        self.assertIn("previous", parsed["command_text"])
        self.assertIn("--plan-only", parsed["command_text"])

    def test_save_previous_routes_to_non_motion_snapshot(self):
        parsed = self.parse("save current pose as previous pose")
        self.assertEqual(parsed["action"], "save-previous")
        self.assertIn("save-previous", parsed["command_text"])

    def test_open_gripper_routes_to_gripper_tool(self):
        parsed = self.parse("open the gripper")
        self.assertEqual(parsed["action"], "open-gripper")
        self.assertIn("open-gripper", parsed["command_text"])
        self.assertIn("--plan-only", parsed["command_text"])

    def test_close_gripper_routes_to_gripper_tool(self):
        parsed = self.parse("close the claw")
        self.assertEqual(parsed["action"], "close-gripper")
        self.assertIn("close-gripper", parsed["command_text"])
        self.assertEqual(parsed["completion_type"], "gripper_width_command")


if __name__ == "__main__":
    unittest.main()
