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
4. Wait for `/manipulation_task/finished=true` after each tool call.
5. Use the returned JSON fields such as `success`, `marker_found`, `stage`, and `message` to decide what happened.

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
  -d '{"execute":true,"arm":"front"}'
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

## Search

Use `/tools/search-marker`; do not run a language-model loop of tiny joint steps. The ROS side runs continuous marker detection while the arm moves. If search returns `marker_found:false`, report that clearly and wait for the user's next decision.

## Safety

Never publish raw joint states, CAN frames, `/cmd_vel`, MoveIt goals, or camera launches from OpenClaw when these APIs are available.
