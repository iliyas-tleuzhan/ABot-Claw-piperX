# ABot-Claw PiPER-X

ABot-Claw/OpenClaw integration files for an AgileX PiPER-X arm using ROS 2
Jazzy, `agx_arm_ros`, MoveIt, a wrist Intel RealSense D435i, and ArUco marker
approach/touch skills.

This repository is a curated public export of the PiPER-X-specific parts of the
local ABot-Claw setup. It does not include private logs, model weights, build
trees, OpenClaw identity files, or raw local backups.

## What This Supports

Current PiPER-X commands exposed to OpenClaw:

- `approach the marker`
- `touch the marker`
- `go home`
- `save current pose as home`

The physical path is a geometric marker approach:

- ArUco marker ID: `6`
- marker size: `0.10 m`
- pre-touch clearance: `0.05 m`
- final clearance default: `0.005 m`
- no force/tactile confirmation

The result must be reported as:

```json
{
  "contact_confirmed": false,
  "completion_type": "geometric_surface_approach"
}
```

## Layout

```text
robot_layer/arm_piper_x/
  ABot-Claw-side PiPER-X contract and local API client.

openclaw_layer/
  Skills and shared routing docs to tell OpenClaw that PiPER-X uses the ROS 2
  marker/home API on 127.0.0.1:8892, not the regular Piper Agent Server.

openclaw-workspace/
  Sanitized copy of the active OpenClaw workspace files relevant to PiPER-X
  routing.

external_ros2/piper_x_aruco_wall_approach/
  ROS 2 package source for wall plane fitting, MoveIt target generation,
  marker touch service/API, hand-eye TF publishing, and operator client.

docs/
  PiPER-X ABot-Claw stack notes and D435i hand-eye calibration guide.
```

## PiPER-X Contract

- ROS: Jazzy
- driver: `agx_arm_ros`
- driver package: `agx_arm_ctrl`
- MoveIt package: `agx_arm_moveit`
- description package: `agx_arm_description`
- arm type: `piper_x`
- effector type: `agx_gripper`
- firmware argument: `v189`
- CAN: `can0`, `1000000`
- MoveIt group: `arm`
- tip/TCP link: `tcp_link`
- TCP offset: `[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]`
- joint feedback: `/feedback/joint_states`
- TCP feedback: `/feedback/tcp_pose`
- point cloud: `/camera/camera/depth/color/points`
- ArUco pose: `/aruco_single/pose`
- local API: `http://127.0.0.1:8892`

See:

```text
robot_layer/arm_piper_x/agent_server/config/piper_x_robot_contract.yaml
docs/PIPER_X_ABOTCLAW_STACK.md
```

## Important Boundary

`robot_layer/arm_piper` from the original ABot-Claw stack is the regular Piper
workcell path. PiPER-X marker/home commands must use:

```text
robot_layer/arm_piper_x
http://127.0.0.1:8892
```

Do not route PiPER-X to:

```text
http://127.0.0.1:8888
```

## Build The ROS 2 Package

Copy or symlink the package into your ROS 2 workspace:

```bash
mkdir -p ~/agx_arm_ws/src
cp -a external_ros2/piper_x_aruco_wall_approach ~/agx_arm_ws/src/

cd ~/agx_arm_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select piper_x_aruco_wall_approach
```

## Start The Full Stack

Configure CAN first:

```bash
sudo ip link set can0 down 2>/dev/null || true
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

Launch the PiPER-X marker stack:

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch piper_x_aruco_wall_approach touch_marker_full_stack.launch.py \
  execute_allowed:=true \
  can_port:=can0 \
  auto_enable:=false \
  follow:=true \
  auto_control_gate:=false \
  enable_color:=true \
  enable_depth:=true \
  align_depth:=true \
  pointcloud:=true \
  use_rviz:=true \
  point_cloud_topic:=/camera/camera/depth/color/points
```

`auto_control_gate:=false` is intentional for the local tested setup because the
installed AgileX workspace did not provide the optional `agx_arm_control_gate`
executable.

## Health Check

```bash
curl -sS http://127.0.0.1:8892/health | python3 -m json.tool
```

For physical marker commands, required fields should be true:

```text
ros_ok
marker_pose_available
point_cloud_available
moveit_available
marker_task_service_available
joint_state_available
execution_allowed
```

## Manual API Examples

Approach marker:

```bash
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py approach --execute
```

Touch marker, retract, then home:

```bash
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py touch --execute --retract --return-home-after
```

Save current pose as home:

```bash
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py save-home
```

Go home:

```bash
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py home --execute
```

## OpenClaw Skills

Install/sync these into `~/.openclaw/workspace/skills`:

```text
openclaw_layer/skills/abotclaw-piper-x-manipulation
openclaw_layer/skills/piper-touch-marker
openclaw_layer/skills/abotclaw-piper-x-moveit-aruco-touch
```

Use natural language such as:

```text
approach the marker
touch the marker and return home
save current pose as home
go home
```

## Validation Performed Before Export

- Python syntax checks for PiPER-X client/parser.
- Unit tests for PiPER-X marker task parsing.
- ROS 2 launch argument parsing for the full-stack launch.
- OpenClaw skill visibility checks on the source machine.

No physical robot motion is performed by this repository export.
