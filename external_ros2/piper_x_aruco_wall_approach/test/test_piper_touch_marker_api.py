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
    def __init__(self, health=None, result=None, delay_s=0.0, exc=None):
        self._health = health or api.HealthSnapshot(True, True, True, True, True, True, True, 6, 0.10, False)
        self._result = result or {
            "success": True,
            "stage": "complete",
            "message": "ok",
            "contact_confirmed": False,
            "completion_type": "geometric_surface_approach",
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
            0.10,
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
    assert body["configured_marker_size_m"] == 0.10
    assert body["execution_allowed"] is False
    assert body["marker_pose_available"] is True
    assert body["marker_pose_age_s"] == 0.2
    assert body["marker_timeout_s"] == 1.0


def test_health_endpoint_reports_stale_marker_not_ready():
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
    assert body["status"] == "not_ready"
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
    assert adapter.calls[0][0] == "touch"


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
        (api.HealthSnapshot(True, False, True, True, True, True, True, 6, 0.10, False), "ArUco marker pose unavailable"),
        (api.HealthSnapshot(True, True, False, True, True, True, True, 6, 0.10, False), "RealSense point cloud unavailable"),
        (api.HealthSnapshot(True, True, True, False, True, True, True, 6, 0.10, False), "MoveIt is unavailable"),
        (api.HealthSnapshot(True, True, True, True, False, True, True, 6, 0.10, False), "marker task service unavailable"),
    ],
)
def test_readiness_failures_are_reported(health, expected_detail):
    response = client(FakeAdapter(health=health)).post("/tools/piper/approach-marker", json={})
    assert response.status_code == 503
    assert response.json()["detail"] == expected_detail


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


def test_successful_mocked_save_home():
    adapter = FakeAdapter()
    response = client(adapter).post("/tools/piper/save-home", json={"pose_name": "home"})
    assert response.status_code == 200
    assert response.json()["completion_type"] == "saved_home_pose_update"
    assert adapter.calls[0][0] == "save-home"


def test_save_home_requires_fresh_joint_state():
    response = client(
        FakeAdapter(health=api.HealthSnapshot(True, True, True, True, True, True, False, 6, 0.10, False))
    ).post("/tools/piper/save-home", json={"pose_name": "home"})
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
    assert [call[0] for call in adapter.calls] == ["touch", "home"]


def test_home_execution_gate_blocks_execute(monkeypatch):
    monkeypatch.delenv("PIPER_TOUCH_ALLOW_EXECUTION", raising=False)
    response = client(FakeAdapter()).post(
        "/tools/piper/go-home",
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


def test_invalid_final_travel_rejected():
    response = client(FakeAdapter()).post(
        "/tools/piper/touch-marker",
        json={"pre_clearance_m": 0.10, "final_clearance_m": 0.005},
    )
    assert response.status_code == 400
    assert "final travel exceeds" in response.json()["detail"]


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
    assert body["completion_type"] == "geometric_surface_approach"
