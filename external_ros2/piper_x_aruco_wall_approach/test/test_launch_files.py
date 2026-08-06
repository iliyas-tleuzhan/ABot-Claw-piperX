import importlib.util
import pathlib


def load_launch(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert "SetEnvironmentVariable" in entity_types
    assert "wall_approach_node" in node_executables
    assert "piper_touch_marker_api.py" in node_executables
