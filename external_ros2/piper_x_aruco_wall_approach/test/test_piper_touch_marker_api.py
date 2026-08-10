import importlib.util
import os
import pathlib
import sys
import threading
import time

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "piper_touch_marker_api.py"
SPEC = importlib.util.spec_from_file_location("piper_touch_marker_api", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = api
SPEC.loader.exec_module(api)


class FakeAdapter(api.RosMarkerTaskAdapter):
    def __init__(self, health=None, result=None, search_result=None, delay_s=0.0, exc=None):
        self._health = health or api.HealthSnapshot(True, True, True, True, True, True, True, 6, 0.03, False)
        self._result = result or {
            "success": True,
            "stage": "complete",
            "message": "ok",
            "contact_confirmed": False,
            "completion_type": "single_moveit_marker_touch",
        }
        self._search_result = search_result or {
            "success": True,
            "marker_found": True,
            "marker_id": 6,
            "found_at_pose": "reactive_up",
            "steps_used": 1,
            "poses_checked": 1,
            "stage": "complete",
            "message": "marker acquired",
        }
        self.delay_s = delay_s
        self.exc = exc
        self.calls = []

    def health(self):
        return self._health

    def run_task(self, mode, request):
        self.calls.append((mode, request))
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.exc:
            raise self.exc
        return dict(self._result)

    def search_marker(self, request):
        self.calls.append(("search", request))
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.exc:
            raise self.exc
        result = dict(self._search_result)
        if result.get("marker_found", False):
            self._health.marker_pose_available = True
        return result

    def go_home(self, request):
        self.calls.append(("home", request))
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.exc:
            raise self.exc
        return {
            "success": True,
            "stage": "complete",
            "message": "home trajectory completed",
            "contact_confirmed": False,
            "completion_type": "saved_home_pose",
        }

    def go_previous(self, request):
        self.calls.append(("previous", request))
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.exc:
            raise self.exc
        return {
            "success": True,
            "stage": "complete",
            "message": "previous trajectory completed",
            "contact_confirmed": False,
            "completion_type": "saved_previous_pose",
        }

    def save_home(self, request):
        self.calls.append(("save-home", request))
        return {
            "success": True,
            "stage": "complete",
            "message": "saved current pose as home",
            "contact_confirmed": False,
            "completion_type": "saved_home_pose_update",
            "home_pose_file": "/tmp/piper_x_home_pose.yaml",
            "joint_names": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
            "positions_rad": [0.0, 0.1, -0.2, 0.3, 0.4, 0.5],
        }

    def save_previous(self):
        self.calls.append(("save-previous", None))
        return {
            "success": True,
            "stage": "complete",
            "message": "saved current pose as previous",
            "contact_confirmed": False,
            "completion_type": "saved_previous_pose_update",
            "previous_pose_file": "/tmp/piper_x_previous_pose.yaml",
            "joint_names": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
            "positions_rad": [0.0, 0.1, -0.2, 0.3, 0.4, 0.5],
        }


def client(adapter, token=None):
    return TestClient(api.create_app(adapter, api_token=token))


def test_health_endpoint_reports_state(monkeypatch):
    monkeypatch.delenv("PIPER_TOUCH_ALLOW_EXECUTION", raising=False)
    adapter = FakeAdapter(
        health=api.HealthSnapshot(
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            6,
            0.03,
            False,
            marker_pose_age_s=0.2,
            point_cloud_age_s=0.1,
            marker_timeout_s=1.0,
            point_cloud_timeout_s=2.0,
        )
    )
    response = client(adapter).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["configured_marker_id"] == 6
    assert body["configured_marker_size_m"] == 0.03
    assert body["execution_allowed"] is False
    assert body["marker_pose_available"] is True
    assert body["marker_pose_age_s"] == 0.2
    assert body["marker_timeout_s"] == 1.0


def test_health_endpoint_reports_stale_marker_ready_for_search():
    adapter = FakeAdapter(
        health=api.HealthSnapshot(
            True,
            False,
            True,
            True,
            True,
            True,
            True,
            6,
            0.10,
            True,
            marker_pose_age_s=5.0,
            point_cloud_age_s=0.1,
            marker_timeout_s=1.0,
            point_cloud_timeout_s=2.0,
        )
    )
    response = client(adapter).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["system_ready"] is True
    assert body["ready_for_search"] is True
    assert body["ready_for_approach"] is False
    assert body["marker_visible"] is False
    assert body["marker_pose_available"] is False
    assert body["marker_pose_age_s"] == 5.0


def test_execution_gate_blocks_execute(monkeypatch):
    monkeypatch.delenv("PIPER_TOUCH_ALLOW_EXECUTION", raising=False)
    response = client(FakeAdapter()).post(
        "/tools/piper/touch-marker",
        json={"execute": True},
    )
    assert response.status_code == 403
    assert "physical execution is disabled" in response.json()["detail"]


def test_execution_gate_allows_execute(monkeypatch):
    monkeypatch.setenv("PIPER_TOUCH_ALLOW_EXECUTION", "true")
    adapter = FakeAdapter(
        health=api.HealthSnapshot(True, True, True, True, True, True, True, 6, 0.10, True)
    )
    response = client(adapter).post("/tools/piper/touch-marker", json={"execute": True})
    assert response.status_code == 200
    assert response.json()["contact_confirmed"] is False
    assert [call[0] for call in adapter.calls] == ["save-previous", "touch"]


def test_bearer_token_required():
    response = client(FakeAdapter(), token="secret").get("/health")
    assert response.status_code == 401
    response = client(FakeAdapter(), token="secret").get(
        "/health",
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "health,expected_detail",
    [
        (api.HealthSnapshot(True, True, False, True, True, True, True, 6, 0.10, False), "RealSense point cloud unavailable"),
        (api.HealthSnapshot(True, True, True, False, True, True, True, 6, 0.10, False), "MoveIt is unavailable"),
        (api.HealthSnapshot(True, True, True, True, False, True, True, 6, 0.10, False), "marker task service unavailable"),
    ],
)
def test_readiness_failures_are_reported(health, expected_detail):
    response = client(FakeAdapter(health=health)).post("/tools/piper/approach-marker", json={})
    assert response.status_code == 503
    assert response.json()["detail"] == expected_detail


def test_search_marker_endpoint_proxies_search():
    adapter = FakeAdapter()
    response = client(adapter).post("/tools/piper/search-marker", json={"execute": False})
    assert response.status_code == 200
    assert response.json()["marker_found"] is True
    assert [call[0] for call in adapter.calls] == ["search"]


def test_search_step_endpoint_proxies_one_step():
    adapter = FakeAdapter(
        search_result={
            "success": True,
            "marker_found": False,
            "marker_id": 6,
            "found_at_pose": "",
            "steps_used": 1,
            "poses_checked": 1,
            "stage": "step_complete",
            "message": "reactive search step completed; marker_not_found",
        }
    )
    response = client(adapter).post(
        "/tools/piper/search-step",
        json={"execute": False, "direction": "up", "max_steps": 100},
    )
    assert response.status_code == 200
    assert response.json()["marker_found"] is False
    assert response.json()["steps_used"] == 1
    assert adapter.calls[0][0] == "search"
    assert adapter.calls[0][1].direction == "up"
    assert adapter.calls[0][1].max_steps == 1


def test_search_step_endpoint_rejects_auto_direction():
    response = client(FakeAdapter()).post(
        "/tools/piper/search-step",
        json={"execute": False, "direction": "auto"},
    )
    assert response.status_code == 400


def test_marker_absence_triggers_search_before_approach():
    adapter = FakeAdapter(
        health=api.HealthSnapshot(True, False, True, True, True, True, True, 6, 0.03, False)
    )
    response = client(adapter).post("/tools/piper/approach-marker", json={})
    assert response.status_code == 200
    assert response.json()["search_result"]["found_at_pose"] == "reactive_up"
    assert [call[0] for call in adapter.calls] == ["search", "approach"]


def test_marker_absence_returns_marker_not_found_when_search_fails():
    adapter = FakeAdapter(
        health=api.HealthSnapshot(True, False, True, True, True, True, True, 6, 0.03, False),
        search_result={
            "success": False,
            "marker_found": False,
            "marker_id": 6,
            "found_at_pose": "",
            "poses_checked": 9,
            "stage": "search_complete",
            "message": "marker_not_found",
        },
    )
    response = client(adapter).post("/tools/piper/approach-marker", json={})
    assert response.status_code == 422
    assert response.json()["detail"]["stage"] == "marker_not_found"
    assert response.json()["detail"]["search"]["poses_checked"] == 9


def test_successful_mocked_approach_and_touch():
    adapter = FakeAdapter()
    app_client = client(adapter)
    assert app_client.post("/tools/piper/approach-marker", json={}).status_code == 200
    assert app_client.post("/tools/piper/touch-marker", json={}).status_code == 200
    assert [call[0] for call in adapter.calls] == ["approach", "touch"]


def test_successful_mocked_home():
    adapter = FakeAdapter()
    response = client(adapter).post("/tools/piper/go-home", json={"execute": False})
    assert response.status_code == 200
    assert response.json()["completion_type"] == "saved_home_pose"
    assert adapter.calls[0][0] == "home"


def test_successful_mocked_previous():
    adapter = FakeAdapter()
    response = client(adapter).post("/tools/piper/go-previous", json={"execute": False})
    assert response.status_code == 200
    assert response.json()["completion_type"] == "saved_previous_pose"
    assert adapter.calls[0][0] == "previous"


def test_successful_mocked_save_home():
    adapter = FakeAdapter()
    response = client(adapter).post("/tools/piper/save-home", json={"pose_name": "home"})
    assert response.status_code == 200
    assert response.json()["completion_type"] == "saved_home_pose_update"
    assert adapter.calls[0][0] == "save-home"


def test_successful_mocked_save_previous():
    adapter = FakeAdapter()
    response = client(adapter).post("/tools/piper/save-previous", json={})
    assert response.status_code == 200
    assert response.json()["completion_type"] == "saved_previous_pose_update"
    assert adapter.calls[0][0] == "save-previous"


def test_save_home_requires_fresh_joint_state():
    response = client(
        FakeAdapter(health=api.HealthSnapshot(True, True, True, True, True, True, False, 6, 0.10, False))
    ).post("/tools/piper/save-home", json={"pose_name": "home"})
    assert response.status_code == 503
    assert response.json()["detail"] == "fresh joint state unavailable"


def test_save_previous_requires_fresh_joint_state():
    response = client(
        FakeAdapter(health=api.HealthSnapshot(True, True, True, True, True, True, False, 6, 0.10, False))
    ).post("/tools/piper/save-previous", json={})
    assert response.status_code == 503
    assert response.json()["detail"] == "fresh joint state unavailable"


def test_marker_task_can_return_home_after_execution(monkeypatch):
    monkeypatch.setenv("PIPER_TOUCH_ALLOW_EXECUTION", "true")
    adapter = FakeAdapter(
        health=api.HealthSnapshot(True, True, True, True, True, True, True, 6, 0.10, True)
    )
    response = client(adapter).post(
        "/tools/piper/touch-marker",
        json={"execute": True, "return_home_after": True, "home_duration_s": 5.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["return_home_after"]["completion_type"] == "saved_home_pose"
    assert body["previous_pose_saved_before_motion"]["completion_type"] == "saved_previous_pose_update"
    assert [call[0] for call in adapter.calls] == ["save-previous", "touch", "home"]


def test_execute_marker_task_saves_previous_before_motion(monkeypatch):
    monkeypatch.setenv("PIPER_TOUCH_ALLOW_EXECUTION", "true")
    adapter = FakeAdapter(
        health=api.HealthSnapshot(True, True, True, True, True, True, True, 6, 0.10, True)
    )
    response = client(adapter).post("/tools/piper/approach-marker", json={"execute": True})
    assert response.status_code == 200
    assert response.json()["previous_pose_saved_before_motion"]["completion_type"] == "saved_previous_pose_update"
    assert [call[0] for call in adapter.calls] == ["save-previous", "approach"]


def test_execute_home_saves_previous_before_motion(monkeypatch):
    monkeypatch.setenv("PIPER_TOUCH_ALLOW_EXECUTION", "true")
    adapter = FakeAdapter(
        health=api.HealthSnapshot(True, True, True, True, True, True, True, 6, 0.10, True)
    )
    response = client(adapter).post("/tools/piper/go-home", json={"execute": True})
    assert response.status_code == 200
    assert response.json()["previous_pose_saved_before_motion"]["completion_type"] == "saved_previous_pose_update"
    assert [call[0] for call in adapter.calls] == ["save-previous", "home"]


def test_home_execution_gate_blocks_execute(monkeypatch):
    monkeypatch.delenv("PIPER_TOUCH_ALLOW_EXECUTION", raising=False)
    response = client(FakeAdapter()).post(
        "/tools/piper/go-home",
        json={"execute": True},
    )
    assert response.status_code == 403
    assert "physical execution is disabled" in response.json()["detail"]


def test_previous_execution_gate_blocks_execute(monkeypatch):
    monkeypatch.delenv("PIPER_TOUCH_ALLOW_EXECUTION", raising=False)
    response = client(FakeAdapter()).post(
        "/tools/piper/go-previous",
        json={"execute": True},
    )
    assert response.status_code == 403
    assert "physical execution is disabled" in response.json()["detail"]


def test_home_action_unavailable_is_reported():
    response = client(
        FakeAdapter(health=api.HealthSnapshot(True, True, True, True, True, False, True, 6, 0.10, False))
    ).post("/tools/piper/go-home", json={})
    assert response.status_code == 503
    assert response.json()["detail"] == "home trajectory action unavailable"


def test_previous_action_unavailable_is_reported():
    response = client(
        FakeAdapter(health=api.HealthSnapshot(True, True, True, True, True, False, True, 6, 0.10, False))
    ).post("/tools/piper/go-previous", json={})
    assert response.status_code == 503
    assert response.json()["detail"] == "trajectory action unavailable"


def test_ros_task_failure_returns_stage():
    adapter = FakeAdapter(result={
        "success": False,
        "stage": "plane_fit",
        "message": "RANSAC failed",
        "contact_confirmed": False,
        "completion_type": "geometric_surface_approach",
    })
    response = client(adapter).post("/tools/piper/touch-marker", json={})
    assert response.status_code == 422
    assert response.json()["detail"]["stage"] == "plane_fit"


def test_service_exception_returns_bad_gateway():
    response = client(FakeAdapter(exc=RuntimeError("planning failure"))).post(
        "/tools/piper/touch-marker",
        json={},
    )
    assert response.status_code == 502
    assert "planning failure" in response.json()["detail"]


def test_invalid_touch_clearance_rejected():
    response = client(FakeAdapter()).post(
        "/tools/piper/touch-marker",
        json={"final_clearance_m": 0.001},
    )
    assert response.status_code == 400
    assert "at least 0.003" in response.json()["detail"]


def test_touch_does_not_use_pre_touch_travel_validation():
    response = client(FakeAdapter()).post(
        "/tools/piper/touch-marker",
        json={"pre_clearance_m": 0.10, "final_clearance_m": 0.005},
    )
    assert response.status_code == 200


def test_concurrent_request_returns_409():
    adapter = FakeAdapter(delay_s=0.25)
    app_client = client(adapter)
    statuses = []

    def call():
        statuses.append(app_client.post("/tools/piper/touch-marker", json={}).status_code)

    first = threading.Thread(target=call)
    first.start()
    time.sleep(0.05)
    second = app_client.post("/tools/piper/touch-marker", json={})
    first.join()
    assert second.status_code == 409
    assert 200 in statuses


def test_contact_is_never_force_confirmed():
    response = client(FakeAdapter()).post("/tools/piper/touch-marker", json={})
    body = response.json()
    assert body["contact_confirmed"] is False
    assert body["completion_type"] == "single_moveit_marker_touch"
