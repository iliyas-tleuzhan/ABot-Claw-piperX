import importlib.util
import pathlib


def load_launch(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def substitution_text(value):
    if isinstance(value, list):
        return "".join(substitution_text(item) for item in value)
    if isinstance(value, tuple):
        return "".join(substitution_text(item) for item in value)
    text = getattr(value, "text", None)
    if text is not None:
        return text
    variable_name = getattr(value, "variable_name", None)
    if variable_name:
        return substitution_text(tuple(variable_name))
    return str(value)


def test_wall_approach_launch_loads():
    launch_file = pathlib.Path(__file__).resolve().parents[1] / "launch" / "wall_approach.launch.py"
    description = load_launch(launch_file).generate_launch_description()
    assert description is not None


def test_touch_marker_full_stack_launch_loads():
    launch_file = pathlib.Path(__file__).resolve().parents[1] / "launch" / "touch_marker_full_stack.launch.py"
    description = load_launch(launch_file).generate_launch_description()
    entity_types = [type(entity).__name__ for entity in description.entities]
    node_executables = [
        getattr(entity, "_Node__node_executable", None)
        for entity in description.entities
    ]
    node_remappings = {
        getattr(entity, "_Node__node_executable", None): getattr(entity, "_Node__remappings", [])
        for entity in description.entities
    }
    node_parameters = {
        getattr(entity, "_Node__node_executable", None): getattr(entity, "_Node__parameters", [])
        for entity in description.entities
    }
    launch_defaults = {
        getattr(entity, "name", None): substitution_text(getattr(entity, "default_value", ""))
        for entity in description.entities
        if type(entity).__name__ == "DeclareLaunchArgument"
    }
    assert "SetEnvironmentVariable" in entity_types
    assert launch_defaults["piper_namespace"] == "front_piper"
    assert launch_defaults["use_piper_motion_stack"] == "true"
    assert launch_defaults["use_realsense"] == "false"
    assert launch_defaults["use_handeye_tf_publisher"] == "false"
    assert launch_defaults["use_front_piper_joint_state_adapter"] == "true"
    assert launch_defaults["integrated_joint_state_topic"] == "/joint_states"
    assert launch_defaults["front_piper_joint_prefix"] == "front_piper_"
    assert launch_defaults["camera_image_topic"] == "/front_camera/color/image_raw"
    assert launch_defaults["camera_info_topic"] == "/front_camera/color/camera_info"
    assert launch_defaults["point_cloud_topic"] == "/front_camera/depth/color/points"
    assert launch_defaults["camera_optical_frame"] == "front_camera_color_optical_frame"
    assert launch_defaults["joint_state_topic"] == "/front_piper/feedback/joint_states"
    assert launch_defaults["control_topic"] == "/front_piper/control/joint_states"
    assert launch_defaults["robot_description_topic"] == "/front_piper/robot_description"
    assert (
        launch_defaults["robot_description_semantic_topic"]
        == "/front_piper/robot_description_semantic"
    )
    assert (
        launch_defaults["trajectory_action"]
        == "/front_piper/arm_controller/follow_joint_trajectory"
    )
    assert "wall_approach_node" in node_executables
    assert "search_marker_node" in node_executables
    assert "front_piper_joint_state_adapter.py" in node_executables
    assert "piper_x_control_gate.py" in node_executables
    assert "piper_touch_marker_api.py" in node_executables
    assert ("joint_states", "joint_state_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["wall_approach_node"]
    ]
    assert ("robot_description", "robot_description_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["wall_approach_node"]
    ]
    assert ("robot_description_semantic", "robot_description_semantic_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["wall_approach_node"]
    ]
    assert ("joint_states", "joint_state_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["search_marker_node"]
    ]
    assert ("robot_description", "robot_description_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["search_marker_node"]
    ]
    assert ("robot_description_semantic", "robot_description_semantic_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["search_marker_node"]
    ]
    search_marker_inline_params = [
        param
        for param in node_parameters["search_marker_node"]
        if isinstance(param, dict)
    ]
    wall_approach_inline_params = [
        param
        for param in node_parameters["wall_approach_node"]
        if isinstance(param, dict)
    ]
    assert any(
        substitution_text(key) == "move_group_namespace"
        and substitution_text(value) == "piper_namespace"
        for params in wall_approach_inline_params
        for key, value in params.items()
    )
    assert any(
        substitution_text(key) == "joint_state_topic"
        and substitution_text(value) == "joint_state_topic"
        for params in search_marker_inline_params
        for key, value in params.items()
    )
    assert any(
        substitution_text(key) == "move_group_namespace"
        and substitution_text(value) == "piper_namespace"
        for params in search_marker_inline_params
        for key, value in params.items()
    )
