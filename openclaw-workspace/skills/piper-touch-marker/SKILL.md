---
name: piper-touch-marker
description: Use the front PiPER-X Agent Server for marker search, touch, manipulation pose, nav pose, previous pose, found marker pose, and gripper commands. Also handles "open door" as touch-marker.
---

# Front PiPER-X Marker Tools

Use this for the current front PiPER-X only. The rear PiPER-X is intentionally disabled in OpenClaw; do not pass `arm:"rear"` or offer rear-arm actions.

Route phrases like `touch the marker`, `search for the marker`, and `open the door` to this skill.

## Runtime Contract

- Agent Server: `http://127.0.0.1:8893`.
- Low-level marker API: `http://127.0.0.1:8892`.
- Arm: `front`.
- Marker: ArUco ID `6`, size `0.06 m`.
- Camera topics: `/front_camera/*`.
- Feedback: `/front_piper/feedback/joint_states`.
- Trajectory action: `/front_piper/arm_controller/follow_joint_trajectory`.
- Gripper command topic: `/front_piper/control/joint_states`.

OpenClaw should call `8893`. Do not launch duplicate drivers, cameras, TF publishers, robot-state publishers, MoveIt, or marker APIs.

## Required Flow

1. Call `GET /health`.
2. Acquire a lease for physical commands.
3. Use `arm:"front"` in requests.
4. Before search, touch, or other arm motion, call `/rtabmap/pause` if that
   service exists so map updates do not consume moving wrist-camera images.
5. Wait for `/manipulation_task/finished=true` after each tool call.
6. Use the returned JSON fields such as `success`, `marker_found`, `stage`, and `message` to decide what happened.

## Commands

Health:

```bash
curl -sS http://127.0.0.1:8893/health
```

Lease:

```bash
curl -sS -X POST http://127.0.0.1:8893/lease/acquire \
  -H 'Content-Type: application/json' \
  -d '{"client":"openclaw","ttl_s":120}'
```

Search marker:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/search-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front","direction":"auto","max_steps":0}'
```

Touch marker / open door:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Move to manipulation pose:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-manipulation-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Move to nav pose:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Previous pose:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-previous \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Found-marker pose:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-found-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Gripper:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/open-gripper \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'

curl -sS -X POST http://127.0.0.1:8893/tools/close-gripper \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Clear stuck active task state:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/clear-active-piper-tasks \
  -H 'Content-Type: application/json' \
  -d '{"clear_command_lock":false}'
```

If this returns `stage:"command_lock_active"`, do not force-clear it while the arm is moving. If the operator confirms the previous command is dead/stuck and no arm motion is active, retry with:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/clear-active-piper-tasks \
  -H 'Content-Type: application/json' \
  -d '{"clear_command_lock":true}'
```

Force-clear is API bookkeeping only. It must not kill, restart, or relaunch
`8892`, `8893`, `search_marker_node`, `wall_approach_node`, MoveIt, arm
drivers, camera nodes, TF publishers, or RTAB-Map.

## Search

Use `/tools/search-marker`; do not run a language-model loop of tiny joint steps. For normal search, use `direction:"auto"` and `max_steps:0`; this means the ROS side keeps cycling the search pattern indefinitely until marker 6 is found or the operator cancels/stops the task. The ROS side runs continuous marker detection while the arm moves. If search returns `marker_found:false`, report that clearly and wait for the user's next decision.

Do not apply a fixed 120 s or 180 s timeout to search, touch, or
search-then-touch. These commands can legitimately run until marker 6 is found
or until the operator explicitly cancels/stops them.

Before normal search or touch, pause RTAB-Map if available:

```bash
ros2 service call /rtabmap/pause std_srvs/srv/Empty "{}"
```

After the manipulation sequence is complete and the front arm is back in nav pose, resume RTAB-Map if available:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Do not manually call `/rtabmap/resume` before `go-nav-pose` returns. The
low-level nav-pose endpoint pauses mapping during arm motion, waits for the arm
to settle, then resumes RTAB-Map.

## Safety

Never publish raw joint states, CAN frames, `/cmd_vel`, MoveIt goals, or camera launches from OpenClaw when these APIs are available.

If a command fails with `another PiPER marker task is active`, use
`/tools/clear-active-piper-tasks`. Do not restart the 8892 Marker API as part of
force cleanup. If `/search_marker`, `/run_marker_task`, MoveIt, or another ROS
service is unavailable after cleanup, report the missing service and ask the
startup owner to restore that specific node in its visible terminal.
