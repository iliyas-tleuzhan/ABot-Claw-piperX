# PiPER-X ABot-Claw Stack

This document records the ABot-Claw/OpenClaw-side split between the regular
Piper arm and the AgileX PiPER-X arm.

## Current Routing

Use the regular Piper stack only for the older tabletop Agent Server workflow:

- repo path: `robot_layer/arm_piper`
- service: `http://127.0.0.1:8888`
- skills: `abotclaw-piper-manipulation`
- purpose: regular Piper workcell pick/place

Use the PiPER-X stack for the current ROS 2 marker/home workflow:

- repo path: `robot_layer/arm_piper_x`
- service: `http://127.0.0.1:8892`
- skills: `abotclaw-piper-x-manipulation`, `piper-touch-marker`
- legacy alias: `abotclaw-piper-x-moveit-aruco-touch`
- purpose: approach marker, touch marker, save home, go home

Do not route PiPER-X to the regular Piper Agent Server on `8888`.

## PiPER-X Robot Contract

The PiPER-X contract is stored in:

```text
robot_layer/arm_piper_x/agent_server/config/piper_x_robot_contract.yaml
```

Important values:

- ROS: Jazzy
- driver: `agx_arm_ros`
- launch arm type: `piper_x`
- launch effector type: `agx_gripper`
- launch firmware: `v189`
- CAN: `can0`, `1000000`
- MoveIt group: `arm`
- MoveIt tip: `tcp_link`
- TCP offset: `[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]`
- joint feedback: `/feedback/joint_states`
- ArUco marker: ID `6`, size `0.10 m`
- point cloud: `/front_camera/depth/color/points`

The contract points to the installed AgileX ROS 2 sources:

```text
/home/dase-hw101/agx_arm_ws/src/agx_arm_ros
/home/dase-hw101/agx_arm_ws/src/agx_arm_ros/src/agx_arm_description/agx_arm_urdf/piper_x
/home/dase-hw101/agx_arm_ws/src/agx_arm_ros/src/agx_arm_moveit/config
```

## OpenClaw Skills

Active workspace skills are under:

```text
/home/dase-hw101/.openclaw/workspace/skills
```

The current PiPER-X skills are:

```text
skills/abotclaw-piper-x-manipulation/SKILL.md
skills/piper-touch-marker/SKILL.md
skills/abotclaw-piper-x-moveit-aruco-touch/SKILL.md
```

`abotclaw-piper-x-moveit-aruco-touch` is now only a legacy alias that points to
the ROS 2 `8892` API. It must not call the old `piper-pipeline-testbed` flow.

## Commands The Skills Should Use

Health:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py health
```

Approach marker:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py approach --execute
```

Touch marker, retract, then return home:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py touch --execute --retract --return-home-after
```

Save current pose as home:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py save-home
```

Go home:

```bash
cd /home/dase-hw101/ABot-Claw &&
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py home --execute
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
