# Trystan Handoff: ABotClaw PiPER Manipulation API

This is the handoff contract for adding Illiyas' PiPER manipulation commands to
Trystan's Bunker/Nav2 startup.

Goal: after Trystan starts his normal robot stack, anyone can SSH into the Orin
and call low-level HTTP commands for:

- search marker
- touch marker
- approach marker
- go home
- go nav pose
- go previous
- go found-marker pose
- save home / previous / found-marker
- gripper open / close

The user should not need to manually start Illiyas' stack after Trystan's bringup.

## Hardware And ROS Contract

Use these defaults:

```bash
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

Hardware mapping:

```text
front PiPER-X: can3
rear PiPER-X:  can2
Bunker:        can4
camera:        RealSense D435i
```

Trystan's stack should own the shared hardware publishers:

- RealSense camera
- PiPER hardware drivers
- Bunker driver
- TF / robot_state_publisher
- Nav2 / SLAM / safety nodes

Illiyas' manipulation layer should not start duplicate hardware publishers when
Trystan already owns them. It should subscribe to Trystan's topics and expose the
HTTP tools.

## Required Live Topics / Actions

The front-arm marker manipulation layer needs these to work:

```text
/front_camera/color/image_raw
/front_camera/color/camera_info
/front_camera/depth/color/points
/front_piper/feedback/joint_states
/front_piper/control/joint_states
/front_piper/arm_controller/follow_joint_trajectory
/front_piper/enable_agx_arm
```

It also needs compatible MoveIt services/actions for namespace `front_piper`.
The exact names can be checked with:

```bash
ros2 action list | grep front_piper
ros2 service list | grep front_piper
ros2 topic list -t | grep -E 'front_camera|front_piper|joint_states|tf'
```

For marker touch/approach, these ABotClaw-side nodes must be running:

```text
aruco_single
wall_approach_node
search_marker_node
piper_touch_marker_api.py
piper_x_agent_server
```

## Recommended Integration

Add these two processes as the final step of Trystan's startup, after his
camera, PiPER driver, MoveIt, TF, and Nav2 nodes are already running.

The important rule is that Trystan's startup owns the shared hardware. The
ABotClaw launch below must be started with:

```text
use_realsense:=false
use_piper_motion_stack:=false
use_front_piper_joint_state_adapter:=false
use_handeye_tf_publisher:=false
```

That makes ABotClaw subscribe to Trystan's camera, PiPER, MoveIt, and TF instead
of starting duplicate publishers.

### Process 1: ABotClaw ROS Manipulation Overlay

Start this inside `iliyas-abot` after Trystan's hardware stack is live:

```bash
mkdir -p /tmp/abotclaw_logs
cd /workspace/ABot-Claw-piperX
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1

source /opt/ros/humble/setup.bash
source /workspace/agx_arm_ws/install/setup.bash

nohup ros2 launch piper_x_aruco_wall_approach touch_marker_full_stack.launch.py \
  execute_allowed:=true \
  piper_namespace:=front_piper \
  can_port:=can3 \
  use_realsense:=false \
  use_piper_motion_stack:=false \
  use_aruco_detector:=true \
  use_wall_approach_node:=true \
  use_search_marker_node:=true \
  use_marker_api:=true \
  use_front_piper_joint_state_adapter:=false \
  use_handeye_tf_publisher:=false \
  joint_state_topic:=/front_piper/feedback/joint_states \
  control_topic:=/front_piper/control/joint_states \
  trajectory_action:=/front_piper/arm_controller/follow_joint_trajectory \
  enable_service:=/front_piper/enable_agx_arm \
  point_cloud_topic:=/front_camera/depth/color/points \
  camera_image_topic:=/front_camera/color/image_raw \
  camera_info_topic:=/front_camera/color/camera_info \
  marker_id:=6 \
  marker_size:=0.03 \
  > /tmp/abotclaw_logs/piper_touch_marker_stack.log 2>&1 &
```

This starts the ABotClaw-side ROS nodes:

```text
aruco_single
wall_approach_node
search_marker_node
piper_touch_marker_api.py
```

It exposes the low-level HTTP API on:

```text
http://127.0.0.1:8892
```

### Process 2: PiPER-X Agent Server

Start this after Process 1:

```bash
mkdir -p /tmp/abotclaw_logs
cd /workspace/ABot-Claw-piperX
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1
export PIPER_X_AGENT_ALLOW_EXECUTION=1
export PIPER_TOUCH_ALLOW_EXECUTION=1
export PIPER_X_MARKER_API_URL=http://127.0.0.1:8892
export PIPER_X_JOINT_STATE_TOPIC=/front_piper/feedback/joint_states
export PIPER_X_GRIPPER_CONTROL_TOPIC=/front_piper/control/joint_states
export PIPER_X_TRAJECTORY_ACTION=/front_piper/arm_controller/follow_joint_trajectory

nohup ./robot_layer/arm_piper_x/agent_server/start_piper_x_agent_server.sh \
  > /tmp/abotclaw_logs/piper_x_agent_server.log 2>&1 &
```

This exposes the higher-level Agent Server API on:

```text
http://127.0.0.1:8893
```

It also starts passive listeners for Trystan's navigation-to-manipulation trigger:

```text
/manipulation_task/start
/manipulation_task/start_bool
```

### Optional: Put Both Processes In Trystan's Startup

The practical integration is to paste both process blocks into Trystan's startup
script after the robot topics/actions are available. Do not add any ABotClaw
camera or PiPER driver launch unless Trystan intentionally wants ABotClaw to own
that hardware.

## HTTP APIs After Startup

Low-level PiPER API:

```text
http://127.0.0.1:8892
```

Agent Server API:

```text
http://127.0.0.1:8893
```

If the Docker container uses host networking, these ports are reachable from the
Orin host. Otherwise, run the `curl` commands inside the container or expose the
ports.

Health:

```bash
curl -s http://127.0.0.1:8892/health | python3 -m json.tool
curl -s http://127.0.0.1:8893/health | python3 -m json.tool
```

Search marker:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/search-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","direction":"auto"}' | python3 -m json.tool
```

Touch marker:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","return_home_after":true}' | python3 -m json.tool
```

Approach marker:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/approach-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}' | python3 -m json.tool
```

Go home. Home is the neutral zero pose `[0, 0, 0, 0, 0, 0]`:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-home \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

Go nav pose. Nav pose is Trystan's parked/navigation pose:

```text
front: [-1.6, 0, 0, 0, 0, 0]
rear:  [ 1.6, 0, 0, 0, 0, 0]
```

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

Rear nav pose:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"rear","duration_s":6.0}' | python3 -m json.tool
```

Go previous:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-previous \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

Save home:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/save-home \
  -H 'Content-Type: application/json' \
  -d '{"arm":"front"}' | python3 -m json.tool
```

Open gripper:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/open-gripper \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}' | python3 -m json.tool
```

Close gripper:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/close-gripper \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}' | python3 -m json.tool
```

## Agent Server With Lease

For OpenClaw or higher-level calls, use port `8893`. Physical execution through
the Agent Server normally requires a lease:

```bash
LEASE_ID="$(curl -s -X POST http://127.0.0.1:8893/lease/acquire \
  -H 'Content-Type: application/json' \
  -d '{"holder":"manual","ttl_s":60}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["lease_id"])')"

curl -s -X POST http://127.0.0.1:8893/tools/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d "{\"execute\":true,\"arm\":\"front\",\"lease_id\":\"${LEASE_ID}\",\"duration_s\":6.0}" \
  | python3 -m json.tool
```

## What Trystan Should Not Duplicate

Do not start another publisher for:

- RealSense camera
- front/rear PiPER driver
- Bunker driver
- `/joint_states` for the same joints
- `robot_state_publisher` for the same robot
- TF/TF static for the same links
- Nav2 `/cmd_vel` ownership

If a required topic is missing, fix the owner launch. For example, if RGB exists
but `/front_camera/depth/color/points` is missing, enable point cloud in the
existing RealSense launch instead of starting a second RealSense node.

## Quick Acceptance Test

After Trystan's startup finishes:

```bash
curl -s http://127.0.0.1:8892/health | python3 -m json.tool
curl -s http://127.0.0.1:8893/health | python3 -m json.tool

ros2 topic hz /front_camera/color/image_raw
ros2 topic echo /front_piper/feedback/joint_states --once
ros2 action list | grep /front_piper/arm_controller/follow_joint_trajectory
```

Expected for physical manipulation:

```text
camera_ready: true
moveit_ready: true
joint_state_ready: true
execution_allowed: true
```

Then test a non-marker motion first:

```bash
curl -s -X POST http://127.0.0.1:8892/tools/piper/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","duration_s":6.0}' | python3 -m json.tool
```

If that moves the front arm, marker search/touch can use the same motion path.
