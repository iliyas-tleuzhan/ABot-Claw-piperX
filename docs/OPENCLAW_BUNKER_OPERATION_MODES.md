# OpenClaw Bunker Operation Modes

This is the integration contract for the Bunker Mini's wrist-camera mapping and
PiPER manipulation. The map is persistent state: arm motion must not corrupt it,
and switching modes must not delete it.

## Mode policy

### Navigation

- Nav2 owns the Bunker base.
- Both PiPER arms stay in their verified `nav pose`.
- Wrist cameras may feed mapping/localization and navigation perception.
- OpenClaw must reject arm motion commands while navigation is active.

### Manipulation

- The Bunker is stationary and has no active navigation goal.
- The existing map is retained, but map updates that depend on fixed wrist
  cameras are paused through the integrated stack's supported control interface.
- Wrist cameras remain available to ArUco detection and PiPER manipulation.
- OpenClaw may run MoveIt, search, touch, teaching, and gripper operations after
  the normal health and lease checks.

Do not implement map pausing by killing RTAB-Map, killing the RealSense nodes,
clearing the map, or starting duplicate camera nodes. If the integrated stack
does not expose a supported pause/resume control, report that missing interface
instead of guessing a topic or silently moving the arms.

## Required transitions

```text
NAVIGATION
  -> goal reached or user stops navigation
  -> pause map updates, retaining the map
  -> both arms go to home pose
  -> verify fresh arm feedback
  -> MANIPULATION

MANIPULATION
  -> manipulation complete and all arm motion stopped
  -> both arms go to nav pose
  -> verify fresh arm feedback
  -> resume map updates
  -> NAVIGATION
```

`home` is the manipulation-ready pose. `nav pose` is the camera-parked pose.
They are separate commands and must not be substituted for one another.

## Required OpenClaw state

OpenClaw should expose or verify:

```text
operation_mode: navigation | manipulation | transition | unknown
navigation_active: true | false
base_stationary: true | false
map_updates: active | paused | unknown
front_arm_at_home: true | false | unknown
rear_arm_at_home: true | false | unknown
front_arm_at_nav_pose: true | false | unknown
rear_arm_at_nav_pose: true | false | unknown
```

Do not infer these values from a command being accepted. Use the relevant Nav2
arrival/status, map-update status, and fresh joint feedback interfaces.

The detailed OpenClaw routing rules live in:

```text
openclaw-workspace/skills/abotclaw-operation-modes/SKILL.md
```
