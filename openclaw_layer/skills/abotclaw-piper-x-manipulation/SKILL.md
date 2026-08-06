---
name: abotclaw-piper-x-manipulation
description: Route PiPER-X marker and home-pose commands through the ROS 2 Jazzy MoveIt wall-approach API. Use when the user asks the PiPER-X arm to approach/touch ArUco marker 6, press the marked location, go home, or save the current pose as home.
---

# AbotClaw PiPER-X Manipulation

Use this skill for the AgileX PiPER-X arm. This is not the regular Piper
workcell stack.

## Active PiPER-X Contract

- Robot: AgileX PiPER-X
- Driver: ROS 2 Jazzy `agx_arm_ros`
- Arm launch argument: `arm_type:=piper_x`
- End effector: `effector_type:=agx_gripper`
- Firmware argument: `fw_version:=v189`
- CAN: `can0` at 1 Mbps
- MoveIt group: `arm`
- MoveIt tip/TCP: `tcp_link`
- TCP offset: `[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]`
- Joint feedback: `/feedback/joint_states`
- Wrist camera: Intel RealSense D435i
- Point cloud: `/camera/camera/depth/color/points`
- ArUco pose: `/aruco_single/pose`
- Marker: ID `6`, size `0.10 m`
- Local API: `http://127.0.0.1:8892`

The local API is served by the ROS 2 package
`piper_x_aruco_wall_approach`. It uses ArUco, RealSense depth, hand-eye TF,
and MoveIt to approach a wall marker.

## Required Health Check

Always call health first:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py health
```

For `approach` and `touch`, require:

- `ros_ok: true`
- `marker_pose_available: true`
- `point_cloud_available: true`
- `moveit_available: true`
- `marker_task_service_available: true`
- `joint_state_available: true`
- `execution_allowed: true` for physical execution

For `go home`, marker and point-cloud readiness are not required. Require:

- `ros_ok: true`
- `home_action_available: true`
- `joint_state_available: true`
- `execution_allowed: true` for physical execution

For `save current pose as home`, require fresh joint state. This command does
not move the robot.

## Routing

For "approach the marker", "point at the marker", or "move to the marker":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py \
  approach \
  --execute
```

For "touch the marker" or "press the marked location", use the geometric touch
flow. It moves to pre-touch, performs a slow final approach, retracts, then
returns to saved home:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py \
  touch \
  --execute \
  --retract \
  --return-home-after
```

For "go home":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py \
  home \
  --execute
```

For "save current pose as home" or "remember current pose as home":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py \
  save-home
```

## Parser

Use `scripts/piper_x_marker_task.py` to classify language into one of:

- `approach`
- `touch`
- `home`
- `save-home`

Example:

```bash
python3 /home/dase-hw101/.openclaw/workspace/skills/abotclaw-piper-x-manipulation/scripts/piper_x_marker_task.py \
  "touch the marker"
```

## Safety Rules

- Do not use `robot_layer/arm_piper` for PiPER-X.
- Do not call the regular Piper Agent Server at `127.0.0.1:8888` for PiPER-X.
- Do not import or call regular Piper `piper_sdk` from this skill.
- Do not generate arbitrary joint, CAN, gripper, or MoveIt code.
- Do not retry physical commands automatically.
- Do not call `execute=true` when `/health` reports `execution_allowed=false`.
- Report the exact failed `stage` and `message` returned by the API.
- Never claim force-confirmed contact. Report:

```json
{
  "contact_confirmed": false,
  "completion_type": "geometric_surface_approach"
}
```
