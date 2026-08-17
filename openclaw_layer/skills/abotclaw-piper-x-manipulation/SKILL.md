---
name: abotclaw-piper-x-manipulation
description: Route PiPER-X marker, home-pose, previous-pose, found-marker-pose, nav-pose, search, and gripper commands through the PiPER-X Agent Server on 127.0.0.1:8893. Use when the user asks the PiPER-X arm to search for the marker, look for the marker, find the marker, approach/touch ArUco marker 6, press the marked location, open the door, activate the door button, press the door button, trigger the door sensor, go home, go back to the previous pose, go to nav pose, move to the found marker pose, save the current pose as home or previous, open the gripper, or close the gripper.
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
- Front arm CAN: `can2` at 1 Mbps.
- Rear arm CAN: `can3` at 1 Mbps.
- MoveIt group: `arm`
- MoveIt tip/TCP: `tcp_link`
- TCP offset: `[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]`
- Joint feedback: `/feedback/joint_states`
- Gripper command: `/control/joint_states`
- Gripper joint: `gripper`
- Gripper width range: `[0.0, 0.1] m`
- Gripper effort range: `[0.5, 3.0] N`
- Wrist camera: Intel RealSense D435i depth camera
- Point cloud: `/front_camera/depth/color/points`
- ArUco pose: `/aruco_single/pose`
- Marker: ID `6`, size `0.03 m`
- PiPER-X Agent Server: `http://127.0.0.1:8893`
- Low-level marker bridge: `http://127.0.0.1:8892`
- Bunker CAN: `can4`; do not move Bunker during PiPER-X marker search unless a separate Bunker controller is explicitly enabled.

Default arm selection is `front`. If the user says `rear arm`, `back arm`, or
`rear Piper`, pass `--arm rear` or JSON `"arm":"rear"`. Otherwise pass
`--arm front`. Marker search/touch/approach are currently front-arm/front-camera
operations; rear marker operations should fail clearly unless a rear marker
stack is later added.

The Agent Server is under
`robot_layer/arm_piper_x/agent_server`. It wraps the lower-level ROS 2 package
`piper_x_aruco_wall_approach`, which uses ArUco, RealSense depth, hand-eye TF,
and MoveIt to approach a wall marker.

## Required Health Check

Always call health first:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py health
```

For `approach` and `touch`, require:

- `ros_ok: true`
- `marker_pose_available: true`
- `point_cloud_available: true`
- `moveit_available: true`
- `marker_task_service_available: true`
- `joint_state_available: true`
- `execution_allowed: true` for physical execution
- a valid `/lease/acquire` lease for physical execution through the Agent Server.
  The `run_piper_x_agent_task.py` helper acquires and releases this lease
  automatically when `--execute` is used without `--lease-id`.

For `go home` and `go previous`, marker and point-cloud readiness are not
required. Require:

- `ros_ok: true`
- `home_action_available: true`
- `joint_state_available: true`
- `execution_allowed: true` for physical execution

`go home` means the neutral six-joint zero pose for the selected arm:

```text
[0, 0, 0, 0, 0, 0]
```

This is different from `go nav pose`, which uses Trystan's parked/navigation
pose.

For `save current pose as home` and `save current pose as previous`, require
fresh joint state. These commands do not move the robot.

Physical `approach`, `touch`, and `go home` automatically save the current
six-joint pose as `previous` before sending a trajectory. That gives the
operator a bounded "go back to previous pose" command after a move. If the
previous pose file does not exist yet, call `save-previous` from a known safe
pose first.

For `open gripper` and `close gripper`, marker, point-cloud, and camera
readiness are not required. Require:

- `ros_ok: true`
- `gripper_control.supported: true`
- an active ROS 2 driver subscriber on `/control/joint_states` for physical
  execution
- `execution_allowed: true` for physical execution
- a valid `/lease/acquire` lease for physical execution through the Agent
  Server


## Reactive Marker Search

The old 3x3 hardcoded search-pose grid is retired. Full marker search is a
robot-layer joint sweep, not a language-model loop. The PiPER-X robot layer
raises joint4 while scanning left/right, then repeats that scan at joint1
sectors: current/center, `+1.6`, positive joint1 limit, `-1.6`, and negative
joint1 limit. If marker 6 is still not found, the robot returns joint4 and
joint1 to zero and reports `marker_not_found`.

Use this loop when marker 6 is not visible:

1. Check `GET http://127.0.0.1:8893/health`.
2. If `marker_visible: true`, stop searching and call `touch-marker` or
   `approach-marker`.
3. If marker is hidden, acquire a lease and call `/tools/search-marker` with
   `direction:"auto"` so the robot layer runs the full joint-limit sweep.
4. Re-check after the search returns.
5. Stop immediately when marker 6 is found.
6. If the full sweep finishes without a marker, report `marker_not_found`.

Example one-step command:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/search-step \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","direction":"up","max_steps":1}'
```

Do not generate raw joint, CAN, or arbitrary MoveIt commands. The robot layer
clamps each search step and plans it through MoveIt.

For "search for the marker", "look for the marker", "find the marker", "locate
the marker", or "search", run the full search flow. If marker 6 is found, the
low-level bridge saves the current six-joint pose as `found_marker` and leaves
the arm at that pose. Tell the user: "Found marker 6 and saved the current pose
as found_marker." Then the user can ask to "move to the found marker pose" or
"run touch".

## Routing

For "approach the marker", "point at the marker", or "move to the marker":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  approach \
  --arm front \
  --execute
```

For "touch the marker", "press the marked location", "open the door", "open
door", "activate the door button", "press the door button", "trigger the door
sensor", or "wave at the door sensor", use the geometric touch flow. These door
phrases are aliases for `touch`; do not create a separate door-opening motion.
It moves to pre-touch, performs the final approach, retracts, then returns to
saved home:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  touch \
  --arm front \
  --execute \
  --retract \
  --return-home-after
```

For "go home", "front arm go home", or "rear arm go home":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  home \
  --arm front \
  --execute
```

For "go back to previous pose", "return to the previous pose", or "move back":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  previous \
  --arm front \
  --execute
```

For "go nav pose", "go to navigation pose", "move to nav pose", "front arm nav
pose", or "rear arm nav pose", command Trystan's parked/navigation joint pose:

```text
front: [-1.6, 0, 0, 0, 0, 0]
rear:  [ 1.6, 0, 0, 0, 0, 0]
```

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  nav-pose \
  --arm front \
  --execute
```

For "move to the found marker pose", "go to saved marker position", or "return
to detected marker pose":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  found-marker \
  --arm front \
  --execute
```

For "save current pose as home" or "remember current pose as home":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  save-home
```

For "save current pose as previous" or "remember current pose as previous":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  save-previous
```

For "open the gripper", "release the gripper", or "open the claw":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  open-gripper \
  --execute
```

For "close the gripper", "close the claw", or "shut the gripper":

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py \
  close-gripper \
  --execute
```

## Parser

Use `scripts/piper_x_marker_task.py` to classify language into one of:

- `approach`
- `touch`
- `home`
- `save-home`
- `previous`
- `found-marker`
- `nav-pose`
- `search`
- `save-previous`
- `open-gripper`
- `close-gripper`

Example:

```bash
python3 /home/dase-hw101/.openclaw/workspace/skills/abotclaw-piper-x-manipulation/scripts/piper_x_marker_task.py \
  "touch the marker"
```

## Safety Rules

- Do not use `robot_layer/arm_piper` for PiPER-X.
- Do not call the regular Piper Agent Server at `127.0.0.1:8888` for PiPER-X.
- Use `127.0.0.1:8893` for PiPER-X Agent Server commands.
- Treat `127.0.0.1:8892` as the lower-level marker/home bridge, not the OpenClaw-facing Agent Server.
- Do not import or call regular Piper `piper_sdk` from this skill.
- Do not generate arbitrary joint, CAN, gripper, or MoveIt code.
- For gripper commands, use only `/tools/open-gripper` and
  `/tools/close-gripper`; do not publish ROS messages directly from OpenClaw.
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
