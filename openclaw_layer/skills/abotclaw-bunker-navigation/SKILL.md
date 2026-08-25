---
name: abotclaw-bunker-navigation
description: Control the Bunker Mini through named landmark navigation and read the explicit navigation/manipulation handoff state. Do not use for direct PiPER-X arm movement.
---

# ABotClaw Bunker Mini Navigation

Use direct landmark commands on ROS 2 domain `173`; do not publish base
velocity or start duplicate Bunker, camera, TF, or Nav2 nodes.

```text
/landmark_navigator/go_marker          std_msgs/msg/String
/door_navigation/arrived               std_msgs/msg/Bool
/home_navigation/arrived               std_msgs/msg/Bool
/manipulation_task/finished             std_msgs/msg/Bool
/landmark_navigator/arrived             std_msgs/msg/String JSON (legacy/optional)
```

`/door_navigation/arrived` and `/home_navigation/arrived` are continuous
Boolean state topics. `true` confirms successful arrival at that landmark.
`/manipulation_task/finished` resets to `false` when an individual PiPER task
starts and becomes `true` when it returns, whether successful or not. OpenClaw
uses the task API response's `success`, `marker_found`, and `stage` fields to
decide the result. Task completion does not end manipulation mode.

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1

ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker \
  std_msgs/msg/String "{data: door}"

ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker \
  std_msgs/msg/String "{data: home}"
```

OpenClaw sends the goal, waits for the matching arrival topic to become true,
explicitly enters manipulation mode, runs PiPER tasks one at a time, and waits
for `/manipulation_task/finished=true` after each task. It decides whether to
retry, run another task, move to nav pose, or resume navigation. No automatic
navigation-cycle node or manipulation-start topic is used.
