---
name: abotclaw-bunker-navigation
description: Control the Bunker Mini through named landmark navigation and coordinate door-arrival manipulation cycles. Use for Bunker navigation, home/door landmarks, navigation status, and navigation-to-manipulation workflows. Do not use for direct PiPER-X arm movement.
---

# ABotClaw Bunker Mini Navigation

This skill targets Trystan's Bunker Mini Nav2 stack on ROS 2 domain `173`. It is
separate from `abotclaw-piper-x-manipulation`. Never publish `/cmd_vel`, send
CAN commands, call MoveIt, or call PiPER-X APIs on ports `8892` or `8893` from
this skill.

## Runtime contract

```text
ROS_DOMAIN_ID=173
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ROS_LOCALHOST_ONLY=1
```

Named navigation inputs:

```text
/landmark_navigator/go_marker          std_msgs/msg/String
/landmark_navigator/go_home            std_srvs/srv/Trigger
/landmark_navigator/save_current_pose  std_msgs/msg/String
```

Arrival and handoff inputs:

```text
/door_navigation/arrived               std_msgs/msg/String
/landmark_navigator/arrived            std_msgs/msg/String JSON
/manipulation_task/progress             std_msgs/msg/String
/navigation_manipulation/progress       std_msgs/msg/String JSON
```

The known landmarks are `home` and `door`. Their poses must already be saved
and verified in `/ros2_ws/maps/manual_nav_landmarks.json`.

The integrated startup owns Nav2, Bunker CAN, cameras, TF, localization,
odometry, and the front PiPER manipulation listener. Do not start duplicate
drivers or navigation nodes. The Lark bot is connected to the lab group, but
group messages require an explicit `@ABotClaw` mention and an allowlisted group;
a Lark message is a request, not proof that the robot is ready.

## Commands

Run from the repository/workspace root:

```bash
python3 openclaw_layer/skills/abotclaw-bunker-navigation/scripts/bunker_navigation_cycle.py health
python3 openclaw_layer/skills/abotclaw-bunker-navigation/scripts/bunker_navigation_cycle.py go-marker door
python3 openclaw_layer/skills/abotclaw-bunker-navigation/scripts/bunker_navigation_cycle.py go-marker home
python3 openclaw_layer/skills/abotclaw-bunker-navigation/scripts/bunker_navigation_cycle.py go-home
python3 openclaw_layer/skills/abotclaw-bunker-navigation/scripts/bunker_navigation_cycle.py cycle
```

`health` is read-only. For a simple landmark command, use `command_ready`: the
landmark navigator must be visible and subscribed to
`/landmark_navigator/go_marker`. Do not block `go-marker door` or
`go-marker home` on Nav2 action-status, arrival, or manipulation topics. The
additional `nav2_stack_ready` and `ready_for_cycle` fields are diagnostics for
the complete navigation/manipulation `cycle`, not prerequisites for publishing
a named landmark command.

## Cycle behavior

`cycle` implements:

```text
IDLE_AT_HOME -> NAVIGATING_TO_DOOR -> ARM_HOME_FOR_MANIPULATION -> MANIPULATION_RUNNING
-> NAVIGATING_TO_HOME -> IDLE_AT_HOME
```

1. Publish `door` to `/landmark_navigator/go_marker`.
2. Wait for `/door_navigation/arrived` with `arrived_at_door`, or generic
   `/landmark_navigator/arrived` with `landmark=door` and `status=succeeded`.
3. Do not request manipulation before confirmed door arrival.
4. Transition out of navigation: pause map updates without deleting the map,
   then move both PiPER arms to their verified `home` poses and verify fresh
   feedback. `home` is the manipulation-ready pose; it is not `nav pose`.
5. Let `/nav2_arrival_manipulation_trigger` publish the existing
   `/front_piper/task/start` request. The agent does not publish a duplicate.
6. Wait for manipulation progress. Treat `running` as active, and
   `succeeded`, `done`, `finished`, `success`, and
   `manipulation_succeeded` as success. Treat failed, aborted, canceled, and
   rejected as failure.
7. On success, move both arms to their verified `nav pose`, verify feedback,
   resume map updates, and only then publish `home` to
   `/landmark_navigator/go_marker`.
8. Declare completion only after generic `/landmark_navigator/arrived` reports
   `landmark=home` and `status=succeeded`.

If generic arrival is unavailable, the tool sends the home goal but returns
`HOME_ARRIVAL_UNCONFIRMED`; it never claims the cycle completed based on logs.
On any failure or timeout it stops in `FAILED` and requires operator recovery.

Navigation hints are observations, not commands:

```text
home -> door: navigation_direction=forward, active_camera=front_camera
door -> home: navigation_direction=reverse, active_camera=rear_camera
```

## Safety and ownership

- Keep Nav2 lifecycle nodes alive; send goals instead of restarting Nav2.
- Never publish `/cmd_vel`, `/cmd_vel_autonomy`, or `/nav2/cmd_vel_raw`.
- Never send direct Bunker CAN or PiPER joint/MoveIt commands.
- Never send a second manipulation request for an active door arrival.
- Require only a fresh `command_ready` result before publishing a named
  landmark command. Do not reject `go-marker door` or `go-marker home` merely
  because Nav2 action status, manipulation progress, or arrival handoff topics
  are unavailable.
- Stop on navigation failure, manipulation failure, safety stop, or missing
  arrival confirmation.

The existing PiPER-X skill remains authoritative for direct front-arm marker,
touch, home, and pose operations. This skill only coordinates the handoff after
Nav2 has finished reaching the door.
