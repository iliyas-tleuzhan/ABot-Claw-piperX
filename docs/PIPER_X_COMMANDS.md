# PiPER-X / ABotClaw Command Cheat Sheet

This file is for the Orin setup:

- Orin SSH: `dase-orin@192.168.1.148`
- Docker container: `iliyas-abot`
- front PiPER-X arm CAN: `can2`
- rear PiPER-X arm CAN: `can3`
- Bunker CAN: `can4`
- Camera: RealSense D435i
- Low-level PiPER-X API: `http://127.0.0.1:8892`
- PiPER-X Agent Server API: `http://127.0.0.1:8893`
- OpenClaw gateway: `ws://127.0.0.1:18789`

Run Docker commands on the Orin host. Run ROS, curl, and OpenClaw commands inside the `iliyas-abot` container unless a section says otherwise.

## Enter The Container

```bash
ssh dase-orin@192.168.1.148
docker start iliyas-abot
docker exec -it iliyas-abot bash
```

Inside the container:

```bash
source /opt/ros/humble/setup.bash
source /workspace/agx_arm_ws/install/setup.bash
```

## Start The Full PiPER-X Stack Manually

Inside `iliyas-abot`:

```bash
mkdir -p /tmp/abotclaw_logs
cd /workspace/agx_arm_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch piper_x_aruco_wall_approach touch_marker_full_stack.launch.py \
  execute_allowed:=true \
  calibration_file:=/workspace/handeye/config/piper_x_d435i_eye_in_hand.json \
  point_cloud_topic:=/front_camera/depth/color/points \
  marker_id:=6 \
  marker_size:=0.06 \
  can_port:=can2 \
  pub_rate:=80 \
  joint_state_timeout:=2.5 \
  auto_enable:=true \
  auto_control_gate:=false \
  use_piper_control_gate:=true \
  2>&1 | tee /tmp/abotclaw_logs/full_stack.log
```

Use this version if you want it in the background:

```bash
mkdir -p /tmp/abotclaw_logs
cd /workspace/agx_arm_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

nohup ros2 launch piper_x_aruco_wall_approach touch_marker_full_stack.launch.py \
  execute_allowed:=true \
  calibration_file:=/workspace/handeye/config/piper_x_d435i_eye_in_hand.json \
  point_cloud_topic:=/front_camera/depth/color/points \
  marker_id:=6 \
  marker_size:=0.06 \
  can_port:=can2 \
  pub_rate:=80 \
  joint_state_timeout:=2.5 \
  auto_enable:=true \
  auto_control_gate:=false \
  use_piper_control_gate:=true \
  > /tmp/abotclaw_logs/full_stack.log 2>&1 &
```

## Start The Agent Server

Inside `iliyas-abot`:

```bash
cd /workspace/ABot-Claw-piperX
export PIPER_X_AGENT_ALLOW_EXECUTION=1
./robot_layer/arm_piper_x/agent_server/start_piper_x_agent_server.sh
```

The Agent Server does not start an automatic Bunker-to-manipulation trigger.
OpenClaw owns the task sequence and reads the continuous
`/manipulation_task/finished` Boolean after each individual task.

Background version:

```bash
mkdir -p /tmp/abotclaw_logs
cd /workspace/ABot-Claw-piperX
export PIPER_X_AGENT_ALLOW_EXECUTION=1
nohup ./robot_layer/arm_piper_x/agent_server/start_piper_x_agent_server.sh \
  > /tmp/abotclaw_logs/agent_server.log 2>&1 &
```

## Start OpenClaw Gateway / TUI

Inside `iliyas-abot`:

```bash
openclaw gateway run --bind loopback --port 18789 --force
```

In another container terminal:

```bash
openclaw tui
```

If the gateway is disconnected, restart only the gateway:

```bash
pkill -f "openclaw gateway" || true
pkill -f openclaw-gateway || true
openclaw gateway run --bind loopback --port 18789 --force
```

## Health Checks

Low-level PiPER-X API:

```bash
curl -s http://127.0.0.1:8892/health | python3 -m json.tool
```

Agent Server:

```bash
curl -s http://127.0.0.1:8893/health | python3 -m json.tool
```

Check marker visibility:

```bash
curl -s http://127.0.0.1:8892/health | python3 -m json.tool | grep -E "marker_visible|marker_pose_age_s|joint_state_ready|system_ready"
```

Check ROS joint states:

```bash
ros2 topic echo /feedback/joint_states --once
```

Check PiPER arm status:

```bash
ros2 topic echo /feedback/arm_status --once
```

Check camera point cloud:

```bash
timeout 6 ros2 topic hz /front_camera/depth/color/points
```

Check ArUco pose:

```bash
ros2 topic echo /aruco_single/pose --once
```

## Low-Level Direct Commands

These commands hit port `8892` directly and do not need OpenClaw natural language.

### Search For Marker

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/search-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"direction":"auto"}' | python3 -m json.tool
```

Full `direction:"auto"` search uses this faster absolute camera sequence:

```text
current -> right -> left -> up -> up_right -> up_left -> center
        -> down -> down_right -> down_left
```

Joint1 makes the wide horizontal coverage and joint4 only selects the upper or
lower view. It stops immediately when marker 6 is confirmed; otherwise it
reports `marker_not_found` after the sequence.

Search one step:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/search-step \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"direction":"up"}' | python3 -m json.tool
```

Useful `direction` values:

```text
auto
up
down
left
right
up_left
up_right
down_left
down_right
center
current
```

### Touch Marker

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"return_home_after":false,"retract_after":true}' | python3 -m json.tool
```

Touch marker and return home after:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"return_home_after":true,"retract_after":true}' | python3 -m json.tool
```

### Approach Marker

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/approach-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true}' | python3 -m json.tool
```

### Save Current Pose As Home

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/save-home \
  -H 'Content-Type: application/json' \
  -d '{"pose_name":"home"}' | python3 -m json.tool
```

### Go Home

Fresh-install default front-arm home is:

```text
[0, 0.36, 0.86, 0.56, 0, 0]
```

An operator-taught pose saved to `/ros2_ws/config/piper_x_home_pose.yaml`
overrides this default. Use `go-nav-pose` for Trystan's parked/navigation pose.

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-home \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

Rear arm:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-home \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"rear","duration_s":6.0}' | python3 -m json.tool
```

### Save / Go To Previous Pose

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/save-previous \
  -H 'Content-Type: application/json' \
  -d '{"pose_name":"previous"}' | python3 -m json.tool
```

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-previous \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

### Go To Navigation Pose

Trystan's parked/navigation poses are:

```text
front: [-1.6, 0, 0, 0, 0, 0]
rear:  [ 1.6, 0, 0, 0, 0, 0]
```

Front arm:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

Rear arm:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"rear","duration_s":6.0}' | python3 -m json.tool
```

### Save / Go To Found Marker Pose

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/save-found-marker \
  -H 'Content-Type: application/json' \
  -d '{"pose_name":"found_marker"}' | python3 -m json.tool
```

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-found-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

### Stop / Disable Motion Gate

This disables the PiPER-X control gate when that node is running.

```bash
ros2 service call /control_enable std_srvs/srv/SetBool '{data: false}'
```

Re-enable it:

```bash
ros2 service call /control_enable std_srvs/srv/SetBool '{data: true}'
```

## Full Pipeline Without OpenClaw

This runs:

1. go home;
2. check whether marker 6 is visible;
3. search if it is not visible;
4. touch marker;
5. go home.

```bash
python3 - <<'PY'
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8892"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode())

def post(path, body, timeout=180):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def show(label, value):
    print(f"\n== {label} ==")
    print(json.dumps(value, indent=2))

show("go_home", post("/tools/piper/go-home", {"execute": True, "duration_s": 6.0}, timeout=60))
time.sleep(1.0)

health = get("/health")
show("health", health)

if not health.get("marker_visible"):
    show("search", post("/tools/piper/search-marker", {
        "execute": True,
        "direction": "auto"
    }, timeout=600))

show("touch", post("/tools/piper/touch-marker", {
    "execute": True,
    "return_home_after": False,
    "retract_after": True
}, timeout=180))

show("return_home", post("/tools/piper/go-home", {"execute": True, "duration_s": 6.0}, timeout=60))
PY
```

## Agent Server Commands

These go through port `8893`. Use these when testing the Agent Server layer instead of the low-level ROS API.

```bash
curl -s http://127.0.0.1:8893/health | python3 -m json.tool
```

```bash
curl -s -X POST http://127.0.0.1:8893/tools/search-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true}' | python3 -m json.tool
```

```bash
curl -s -X POST http://127.0.0.1:8893/tools/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"return_home_after":true}' | python3 -m json.tool
```

If port `8893` returns `no active PiPER-X lease`, either use OpenClaw or test the low-level API on port `8892`.

## OpenClaw Natural Language Phrases

OpenClaw should route these to the PiPER-X marker skill when the workspace is configured correctly:

```text
touch the marker
open the door
open door
search for the marker
look for the marker
search
go home
move home
save current pose as home
can it see the marker right now?
```

## Update The Repo In The Docker

Inside `iliyas-abot`:

```bash
cd /workspace/ABot-Claw-piperX
git pull origin main

rsync -a external_ros2/piper_x_aruco_wall_approach/ \
  /workspace/agx_arm_ws/src/piper_x_aruco_wall_approach/

cd /workspace/agx_arm_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select piper_x_aruco_wall_approach
source install/setup.bash
```

## Reset PiPER CAN

Run this on the Orin host, not inside the Docker container.

```bash
sudo ip link set can2 down || true
sudo ip link set can2 type can bitrate 1000000 restart-ms 100
sudo ip link set can2 up
ip -details link show can2
```

## Kill Bunker / Navigation Processes

This is the Bunker cleanup block. It also kills the RealSense camera, so do not run it while the PiPER-X marker stack needs the camera.

```bash
pkill -f realsense2_camera_node || true
pkill -f rtabmap || true
pkill -f rgbd_sync || true
pkill -f rviz2 || true
pkill -f bunker_base_node || true
pkill -f controller_server || true
pkill -f planner_server || true
pkill -f bt_navigator || true
pkill -f lifecycle_manager || true
pkill -f nav2_cmd_vel_safety_mux || true
```

## Clear Stuck PiPER API Task State

Use this when the API reports `another PiPER marker task is active` but the
operator confirms the arm is no longer moving. This clears only API
bookkeeping. It does not kill or restart ROS nodes, MoveIt, drivers, cameras,
TF publishers, RTAB-Map, `search_marker_node`, or `wall_approach_node`.

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/clear-active-piper-tasks \
  -H 'Content-Type: application/json' \
  -d '{"clear_command_lock":true}' | python3 -m json.tool
```

If a ROS service is still missing after this, restart only that specific owner
pane. Do not run the full shutdown blocks below as part of force cleanup.

## Manual Full Shutdown For PiPER-X Manipulation / ABotClaw

Run this only when you intentionally want to stop the full PiPER-X manipulation
stack, Agent Server, and OpenClaw gateway. This is not a recovery step for
`clear-active-piper-tasks`.

```bash
pkill -f "openclaw gateway" || true
pkill -f openclaw-gateway || true
pkill -f "robot_layer/arm_piper_x/agent_server/server.py" || true
pkill -f "start_piper_x_agent_server.sh" || true
pkill -f "touch_marker_full_stack.launch.py" || true
pkill -f "piper_touch_marker_api.py" || true
pkill -f "piper_x_control_gate.py" || true
pkill -f "search_marker_node" || true
pkill -f "wall_approach_node" || true
pkill -f "publish_handeye_tf.py" || true
pkill -f "agx_arm_ctrl_single" || true
pkill -f "move_group" || true
pkill -f "ros2_control_node" || true
pkill -f "robot_state_publisher" || true
pkill -f "aruco_single" || true
pkill -f "aruco_ros" || true
pkill -f "realsense2_camera_node" || true
```

Use this version if you want to stop manipulation but leave the camera running:

```bash
pkill -f "openclaw gateway" || true
pkill -f openclaw-gateway || true
pkill -f "robot_layer/arm_piper_x/agent_server/server.py" || true
pkill -f "start_piper_x_agent_server.sh" || true
pkill -f "touch_marker_full_stack.launch.py" || true
pkill -f "piper_touch_marker_api.py" || true
pkill -f "piper_x_control_gate.py" || true
pkill -f "search_marker_node" || true
pkill -f "wall_approach_node" || true
pkill -f "publish_handeye_tf.py" || true
pkill -f "agx_arm_ctrl_single" || true
pkill -f "move_group" || true
pkill -f "ros2_control_node" || true
pkill -f "robot_state_publisher" || true
pkill -f "aruco_single" || true
pkill -f "aruco_ros" || true
```

Hard stop version if regular `pkill` does not clear everything:

```bash
pkill -9 -f "openclaw gateway" || true
pkill -9 -f openclaw-gateway || true
pkill -9 -f "robot_layer/arm_piper_x/agent_server/server.py" || true
pkill -9 -f "touch_marker_full_stack.launch.py" || true
pkill -9 -f "piper_touch_marker_api.py" || true
pkill -9 -f "piper_x_control_gate.py" || true
pkill -9 -f "search_marker_node" || true
pkill -9 -f "wall_approach_node" || true
pkill -9 -f "agx_arm_ctrl_single" || true
pkill -9 -f "move_group" || true
```

## Logs

Full stack:

```bash
tail -f /tmp/abotclaw_logs/full_stack.log
```

Agent Server:

```bash
tail -f /tmp/abotclaw_logs/agent_server.log
```

Find running PiPER / OpenClaw processes:

```bash
ps aux | grep -E "piper|aruco|move_group|realsense|openclaw|agent_server" | grep -v grep
```

## Common Failures

`no active PiPER-X lease` on port `8893` means the Agent Server did not grant execution. For direct testing, use port `8892`.

`joint_state_ready: false` means the arm driver is not publishing fresh feedback. Check `can2`, check `/feedback/joint_states`, and restart the PiPER stack after a CAN reset.

`marker_visible: false` is not automatically a failure. It means the marker is not currently visible and search should be used.

`camera_ready: false` means the RealSense node is not publishing. Check whether another process owns the camera, then restart the full stack.
