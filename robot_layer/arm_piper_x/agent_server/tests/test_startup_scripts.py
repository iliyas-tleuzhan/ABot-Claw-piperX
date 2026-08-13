from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
AGENT_DIR = ROOT / "robot_layer" / "arm_piper_x" / "agent_server"


def test_agent_startup_starts_manipulation_task_listener():
    start_script = (AGENT_DIR / "start_piper_x_agent_server.sh").read_text()
    listener_script = (AGENT_DIR / "start_manipulation_task_listener.sh").read_text()

    assert "start_manipulation_task_listener.sh" in start_script
    assert "/manipulation_task/start" in listener_script
    assert "/manipulation_task/start_bool" in listener_script
    assert "std_msgs/msg/String" in listener_script
    assert "std_msgs/msg/Bool" in listener_script
    assert "manipulation_task_start.log" in listener_script
    assert "manipulation_task_start_bool.log" in listener_script
