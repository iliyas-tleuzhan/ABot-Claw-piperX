import importlib.util
import pathlib


def load_launch(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def substitution_text(value):
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
    assert "SetEnvironmentVariable" in entity_types
    assert "wall_approach_node" in node_executables
    assert "search_marker_node" in node_executables
    assert "piper_touch_marker_api.py" in node_executables
    assert ("joint_states", "joint_state_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["wall_approach_node"]
    ]
    assert ("joint_states", "joint_state_topic") in [
        (substitution_text(src), substitution_text(dst))
        for src, dst in node_remappings["search_marker_node"]
    ]
