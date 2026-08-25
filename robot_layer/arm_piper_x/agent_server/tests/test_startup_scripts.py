from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
AGENT_DIR = ROOT / "robot_layer" / "arm_piper_x" / "agent_server"


def test_agent_startup_does_not_start_legacy_manipulation_listener():
    start_script = (AGENT_DIR / "start_piper_x_agent_server.sh").read_text()

    assert "start_manipulation_task_listener.sh" not in start_script
