---
name: abotclaw-bunker-navigation
description: Send Bunker Mini named landmark goals and wait for door/home arrival topics. Use for "go to door", "go home with bunker", "drive to home", and similar Bunker navigation requests.
---

# Bunker Navigation

Use this only for the Bunker Mini navigation layer. Do not publish `/cmd_vel`, command CAN, move PiPER arms, or call PiPER APIs from this skill.

## Runtime

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1
```

## Commands

Go to door:

```bash
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker std_msgs/msg/String "{data: door}"
```

Go to home:

```bash
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker std_msgs/msg/String "{data: home}"
```

## Completion

Wait for the matching continuous Bool:

```text
/door_navigation/arrived    std_msgs/msg/Bool
/home_navigation/arrived    std_msgs/msg/Bool
```

Only `data: true` confirms arrival. `data: false` means that landmark is not currently reached.

Do not require optional Nav2 node checks before sending a named goal. DDS discovery can be slow; if checking graph state, wait several seconds and treat the direct command path as authoritative.
