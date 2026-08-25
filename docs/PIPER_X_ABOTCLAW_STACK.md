# PiPER-X ABot-Claw Stack

This document records the current ABot-Claw/OpenClaw routing for the
piper-on-bunker integration.

## Current Routing

Use the Bunker Mini plus front PiPER-X stack for the current workflow:

- repo path: `robot_layer/arm_piper_x`
- OpenClaw workspace: `openclaw-workspace`
- Agent Server: `http://127.0.0.1:8893`
- low-level marker API: `http://127.0.0.1:8892`
- active skills: `abotclaw-bunker-navigation`, `abotclaw-operation-modes`, `piper-touch-marker`
- purpose: Bunker named navigation, front-arm marker search/touch, manipulation pose, nav pose, previous pose, found-marker pose

Do not route this system to old regular Piper or legacy PiPER-X skill aliases.

## PiPER-X Robot Contract

The PiPER-X contract is stored in:

```text
robot_layer/arm_piper_x/agent_server/config/piper_x_robot_contract.yaml
```

Important values:

- ROS: Humble in `trystan-bunker-navigation`
- front PiPER CAN: `can2`, `1000000`
- rear PiPER CAN: `can3`, ignored by OpenClaw for now
- Bunker CAN: `can4`
- MoveIt namespace: `/front_piper`
- MoveIt group: `arm`
- MoveIt trajectory action: `/front_piper/arm_controller/follow_joint_trajectory`
- MoveIt tip: `front_piper_flange_link`
- TCP offset: `[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]`
- joint feedback: `/front_piper/feedback/joint_states`
- ArUco marker: ID `6`, size `0.06 m`
- point cloud: `/front_camera/depth/color/points`
- navigation command topic: `/landmark_navigator/go_marker`
- arrival topics: `/door_navigation/arrived`, `/home_navigation/arrived`; each emits a short `data:true` pulse on successful arrival
- manipulation completion topic: `/manipulation_task/finished`

## OpenClaw Skills

Active workspace files are under:

```text
openclaw-workspace/
```

The current skills are:

```text
skills/abotclaw-bunker-navigation/SKILL.md
skills/abotclaw-operation-modes/SKILL.md
skills/piper-touch-marker/SKILL.md
```

The duplicate OpenClaw skill folder and old PiPER-X alias skills are removed.

## Commands The Skills Should Use

Health:

```bash
curl -sS http://127.0.0.1:8893/health
```

Approach marker:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/approach-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Touch marker, retract, then return home:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Go to nav pose:

```bash
curl -sS -X POST http://127.0.0.1:8893/tools/go-nav-pose \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"arm":"front"}'
```

Go to Bunker door:

```bash
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker std_msgs/msg/String "{data: door}"
```

## Safety Boundary

- Physical execution is disabled unless the `8892` API reports
  `execution_allowed: true`.
- The current PiPER-X capability is not generic pick/place.
- "Touch" is geometric only:

```json
{
  "contact_confirmed": false,
  "completion_type": "geometric_surface_approach"
}
```

- Do not generate arbitrary joint targets, CAN commands, gripper commands, or
  MoveIt scripts from OpenClaw when the PiPER-X API is available.

## Startup Note

The local `agx_arm_moveit` install does not currently provide
`agx_arm_control_gate`. Use:

```text
auto_control_gate:=false
```

The PiPER-X full-stack launch default and the systemd user service have been
set accordingly.
