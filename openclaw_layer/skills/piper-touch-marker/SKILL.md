---
name: piper-touch-marker
description: Use the PiPER-X ROS 2 Agent Server for requests such as "touch the marker", "touch ArUco marker 6", "move the Piper arm to the marker", "approach the marker", "point at the marker", "press the marked location", "go home", "return the Piper arm home", "go back to the previous pose", "save current pose as previous", "open the gripper", or "close the gripper".
---

# PiPER Touch Marker

This is the short OpenClaw-facing skill for the current PiPER-X marker demo.
For full robot details, use `abotclaw-piper-x-manipulation`.

Default PiPER-X Agent Server:

```text
http://127.0.0.1:8893
```

The lower-level ROS 2 marker bridge remains on `http://127.0.0.1:8892`, but
OpenClaw should call the Agent Server on `8893`.

## Required Health Check

Always call:

```bash
curl -sS http://127.0.0.1:8893/health
```

Physical execution requires `execution_allowed: true` and a lease from
`POST /lease/acquire`.

Health separates marker visibility from system readiness. If marker 6 is
visible, direct `touch-marker`/`approach-marker` may run without search. If the
marker is not visible, use reactive search steps through the Agent Server.

For OpenClaw shell execution, prefer:

```bash
python3 /home/dase-hw101/ABot-Claw/robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py touch --execute
```

That helper acquires and releases a temporary lease automatically.

## Commands

Approach marker:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/approach-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","pre_clearance_m":0.05,"final_clearance_m":0.005,"retract_after":false,"retract_distance_m":0.05,"final_velocity_scaling":0.05,"return_home_after":false,"home_duration_s":6.0}'
```

If marker `6` is not currently visible, use reactive search instead of the old
3x3 hardcoded pose grid. Prefer `up` as the first search step because the marker
is usually mounted high. OpenClaw may choose the next direction, but must only
call the bounded `/tools/search-step` endpoint. Do not publish raw joint, CAN,
or MoveIt commands.

Reactive search loop:

1. Call `GET /health`.
2. If `marker_visible: true`, call `touch-marker` or `approach-marker`.
3. If marker is hidden, acquire a lease and call one search step. Start with `up` unless the latest camera evidence clearly suggests another direction.
4. Re-check health/result after every step.
5. Stop immediately when `marker_found: true` or `marker_visible: true`.
6. Stop after `100` total steps and report `marker_not_found`.

Search one step:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/search-step \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","direction":"up","max_steps":1}'
```

Allowed directions are `left`, `right`, `up`, `down`, `center`, and `current`. The `up` step is implemented as a bounded joint4 wrist-camera tilt so the camera looks upward first.

Touch marker directly:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","pre_clearance_m":0.05,"final_clearance_m":0.005,"retract_after":false,"retract_distance_m":0.05,"final_velocity_scaling":0.05,"return_home_after":false,"home_duration_s":6.0}'
```

The touch planner targets the `tcp_link` contact point at the ArUco marker center using one MoveIt plan from the current robot state. The ROS 2 stack prefers elbow/wrist motion by keeping `joint1` near its current angle during planning.

Go home:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-home \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","duration_s":6.0}'
```

Save current pose as home:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/save-home \
  -H 'Content-Type: application/json' \
  -d '{"pose_name":"home"}'
```

Go back to previous pose:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-previous \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","duration_s":6.0}'
```

Save current pose as previous:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/save-previous \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Open gripper:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/open-gripper \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","width_m":0.10,"effort_n":1.0}'
```

Close gripper:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/close-gripper \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"lease_id":"<LEASE_ID>","width_m":0.0,"effort_n":1.0}'
```

## Safety

This skill targets PiPER-X through the Agent Server on `8893`, not the regular
Piper Agent Server on `8888`. The Agent Server wraps the lower-level ROS 2
marker bridge on `8892`.

The previous pose is a saved six-joint snapshot. Physical marker and home
commands save the current pose as previous before sending motion, and
`save-previous` can also be called manually from a known safe pose.

Gripper commands use the AgileX ROS 2 command topic `/control/joint_states`,
message type `sensor_msgs/msg/JointState`, joint name `gripper`, and command
opening width in metres. They do not require the wrist camera.

"Touch" is geometric only:

```json
{
  "contact_confirmed": false,
  "completion_type": "single_moveit_marker_touch"
}
```
