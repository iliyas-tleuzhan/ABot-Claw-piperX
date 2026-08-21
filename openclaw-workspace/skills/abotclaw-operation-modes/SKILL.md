---
name: abotclaw-operation-modes
description: Coordinate Bunker Mini navigation and PiPER-X manipulation modes. Use whenever a task changes between driving/navigation and arm manipulation, including navigation arrival, stop-navigation, touch, search, go-nav-pose, and requests to resume navigation. Keep the existing map while preventing wrist-camera motion from corrupting it.
---

# ABotClaw Operation Modes

This skill is the mode contract for the integrated Bunker Mini plus dual PiPER
system. It coordinates the existing `abotclaw-bunker-navigation` and
`abotclaw-piper-x-manipulation` skills; it does not replace either one and does
not send direct CAN, `/cmd_vel`, or joint commands.

## Modes

The system has two mutually exclusive operating modes:

```text
NAVIGATION
MANIPULATION
```

### NAVIGATION

In `NAVIGATION`:

- Nav2 and the Bunker base own movement.
- The front and rear PiPER arms are parked in their verified navigation poses.
- The wrist RealSense cameras may be used by localization, mapping, and Nav2
  perception.
- Do not call MoveIt, PiPER search, touch, approach, teaching, gripper, home,
  previous-pose, or arbitrary joint-pose tools.
- Do not move either arm, even if the user asks for a quick arm movement.
- The existing map may be localized against and may be updated by the navigation
  stack.

### MANIPULATION

In `MANIPULATION`:

- Navigation has stopped and the Bunker must remain stationary.
- The existing map is retained; never delete, clear, reset, or rebuild it.
- Mapping/localization camera ingestion that assumes fixed wrist-camera poses
  must be paused through the system's supported lifecycle/control interface.
- The wrist cameras remain available to PiPER perception and ArUco detection.
- PiPER MoveIt, search, touch, approach, gripper, teaching, and pose commands
  may run after their normal health, lease, and execution checks pass.
- Do not publish `/cmd_vel` or send Nav2 goals while an arm is moving.

If the stack has no supported control interface for pausing map updates, do not
guess a topic, kill RTAB-Map, kill cameras, or delete the map. Report that the
mode transition is incomplete and require the integrated navigation owner to
expose the pause/resume control.

## Required transitions

```text
NAVIGATION --goal reached or user stops navigation--> ARM_HOME_FOR_MANIPULATION --> MANIPULATION
MANIPULATION --manipulation complete--> NAVIGATION
```

### Navigation to manipulation

1. Confirm Nav2 has reached its goal or has been explicitly stopped.
2. Confirm there is no active base goal and the Bunker is stationary.
3. Confirm both arms are no longer needed for navigation.
4. Pause map updates using the supported integrated interface while retaining
   the current map and localization state.
5. Move both PiPER arms to their verified `home` poses. This is the
   manipulation-ready pose and is distinct from `nav pose`.
6. Confirm fresh joint feedback for both home poses and confirm that no arm
   trajectory remains active.
7. Mark the system `MANIPULATION`.
8. Only then allow PiPER manipulation tools.

For the normal door workflow, the `/door_navigation/arrived` or generic
`/landmark_navigator/arrived` success event is the transition trigger. Do not
start manipulation merely because a goal was sent.

### Manipulation to navigation

1. Finish the manipulation action and confirm it is no longer moving either arm.
2. Move both PiPER arms to their verified navigation poses using the PiPER
   `go nav pose` operation. For dual-arm navigation, both arms must be parked.
3. Confirm fresh feedback for the parked arm poses and confirm no arm trajectory
   remains active.
4. Resume map updates/localization through the supported integrated interface.
5. Wait for fresh camera/map/TF health before sending a Nav2 goal.
6. Mark the system `NAVIGATION`.

Do not resume navigation while an arm is still in a search, touch, teaching, or
arbitrary MoveIt pose. A saved `home` pose is not automatically a navigation
pose.

## Natural-language routing

Treat these as mode-aware requests:

| User request | Mode behavior |
| --- | --- |
| `go to the door`, `navigate home`, `drive to ...` | Require `NAVIGATION`; reject if an arm is moving. |
| `stop navigation`, `stop driving` | Stop navigation intent, keep Nav2 alive, then prepare `MANIPULATION` only after the base is stationary. |
| `touch the marker`, `search for the marker`, `go home`, `move the arm` | Require `MANIPULATION`; never execute while `NAVIGATION` is active. |
| `go nav pose`, `park the arms`, `prepare for navigation` | Complete the arm parking and map-resume transition before allowing navigation. |
| `prepare manipulation`, `move arms home`, `home the arms for manipulation` | Pause map updates, move both arms to their verified `home` poses, verify feedback, then allow manipulation. |
| `open door` | In `MANIPULATION`, route to the existing marker touch pipeline; in `NAVIGATION`, wait for arrival first. |
| Lark message requesting movement | Treat it exactly like a local OpenClaw request; mention/allowlist rules do not bypass mode, health, lease, or safety gates. |

## State and reporting

OpenClaw should maintain or query these conceptual fields:

```text
operation_mode: navigation | manipulation | transition | unknown
navigation_active: true | false
base_stationary: true | false
map_updates: active | paused | unknown
front_arm_at_nav_pose: true | false | unknown
rear_arm_at_nav_pose: true | false | unknown
```

Never infer `map_updates=paused` just because the Bunker is stationary. Never
infer `front_arm_at_nav_pose=true` from a command response without fresh joint
feedback.

When a transition cannot be verified, report the exact missing state and do not
send the next physical command. In particular, do not claim that the map was
paused if only the cameras stopped publishing, and do not claim that navigation
is safe because a single arm reached its pose.

## Ownership and non-interference

- Trystan's integrated startup owns Nav2, Bunker CAN, cameras, TF, mapping,
  localization, and both arm drivers.
- Reuse existing publishers and lifecycle nodes; never launch duplicate cameras,
  drivers, TF publishers, Nav2, or mapping nodes.
- The PiPER-X skill remains authoritative for marker search/touch and arm poses.
- The Bunker navigation skill remains authoritative for named navigation goals.
- This skill only decides whether those skills are currently allowed and in what
  order they may run.
- Lark is an OpenClaw transport, not a separate control path. The same mode and
  safety rules apply to direct messages and group messages.
