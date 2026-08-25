---
name: abotclaw-bunker-navigation
description: Control the Bunker Mini through named landmark navigation and read the explicit navigation/manipulation handoff state. Do not use for direct PiPER-X arm movement.
---

# ABotClaw Bunker Mini Navigation

This skill targets Trystan's Bunker Mini Nav2 stack on ROS 2 domain `173`. It
does not publish `/cmd_vel`, send CAN commands, call MoveIt, or call PiPER-X
APIs on ports `8892` or `8893` for navigation.

## Runtime contract

```text
ROS_DOMAIN_ID=173
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ROS_LOCALHOST_ONLY=1
```

Named navigation input:

```text
/landmark_navigator/go_marker          std_msgs/msg/String
```

Handoff state topics:

```text
/door_navigation/arrived               std_msgs/msg/Bool
/home_navigation/arrived               std_msgs/msg/Bool
/manipulation_task/finished             std_msgs/msg/Bool
/landmark_navigator/arrived             std_msgs/msg/String JSON (legacy/optional)
```

The two navigation topics are continuous state: `false` means the named
landmark has not been reached and `true` means Nav2 successfully reached it.
The manipulation topic is also continuous: it is reset to `false` when an
individual PiPER task starts and becomes `true` when that task returns,
regardless of whether that task succeeded. OpenClaw must use the task API
response's `success` and task-specific fields to decide the result.

`manipulation_task/finished=true` means one task ended. It does not mean that
manipulation mode ended. OpenClaw decides whether to run another manipulation
task, move the arms to nav pose, or start navigation.

The known landmarks are `home` and `door`. Their poses must already be saved
and verified in `/ros2_ws/maps/manual_nav_landmarks.json`.

## Navigation commands

Use these direct commands for named landmark requests. Do not replace them
with the PiPER `/tools/go-home` API.

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1

# Bunker to door
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker \
  std_msgs/msg/String "{data: door}"

# Bunker to home
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker \
  std_msgs/msg/String "{data: home}"
```

OpenClaw should send the goal, then wait for the matching topic:

```bash
ros2 topic echo /door_navigation/arrived
ros2 topic echo /home_navigation/arrived
```

Only `data: true` confirms that the corresponding landmark was reached.

## OpenClaw-controlled handoff

OpenClaw owns the handoff state machine. There is no automatic navigation-cycle
node and no ROS topic that starts manipulation automatically.

For a navigation task followed by manipulation:

1. Send `door` or `home` to `/landmark_navigator/go_marker`.
2. Wait for the matching arrival topic to become `true`.
3. Decide explicitly to enter manipulation mode.
4. Pause map updates without deleting the map and move the required arms to
   manipulation pose before physical PiPER motion.
5. Run one PiPER task through the Agent Server.
6. Wait for `/manipulation_task/finished=true`.
7. Read that task's API response. `success`, `marker_found`, and the task's
   `stage` determine what happened; the Boolean only says the task stopped.
8. Run another manipulation task if needed. Only after the manipulation work
   is complete should OpenClaw move the arms to nav pose, resume map updates,
   and send another Bunker navigation goal.

For `search then touch`, a search ending with `finished=true` and
`success=false` is not automatically a system failure. OpenClaw reads
`marker_found`; it may retry/search differently or stop. If `marker_found=true`,
OpenClaw may issue the touch task next.

## Safety and ownership

- Keep Nav2 lifecycle nodes alive; send goals instead of restarting Nav2.
- Never publish `/cmd_vel`, `/cmd_vel_autonomy`, or `/nav2/cmd_vel_raw`.
- Never send direct Bunker CAN or PiPER joint/MoveIt commands from this skill.
- Do not start a second physical task while `/manipulation_task/finished` is
  `false`.
- Do not infer manipulation success or mode completion from the handoff topics.
- The existing PiPER-X skill remains authoritative for marker, touch, home, and
  pose operations.
