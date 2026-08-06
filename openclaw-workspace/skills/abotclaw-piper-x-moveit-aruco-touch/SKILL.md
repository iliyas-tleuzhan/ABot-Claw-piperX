---
name: abotclaw-piper-x-moveit-aruco-touch
description: Legacy alias for the current ROS 2 PiPER-X ArUco marker approach API. Use piper-touch-marker behavior for "touch marker", "approach marker", "go home", and "save current pose as home".
---

# Legacy Alias

This skill used to describe the old ROS 1 `piper-pipeline-testbed` MoveIt touch flow.

That path is superseded for the current demo. Do not call the old
`piper-pipeline-testbed` commands from this skill.

Use the active `piper-touch-marker` skill contract instead:

- `approach the marker` -> `POST http://127.0.0.1:8892/tools/piper/approach-marker`
- `touch the marker` -> `POST http://127.0.0.1:8892/tools/piper/touch-marker`
- `go home` -> `POST http://127.0.0.1:8892/tools/piper/go-home`
- `save current pose as home` -> `POST http://127.0.0.1:8892/tools/piper/save-home`

Always call:

```bash
curl -sS http://127.0.0.1:8892/health
```

before a physical command.

Never generate arbitrary MoveIt, joint, CAN, gripper, or shell movement code
when the local PiPER marker API is available.
