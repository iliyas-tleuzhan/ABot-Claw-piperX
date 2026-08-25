# TOOLS.md

Current local tool notes for the piper-on-bunker system.

## Runtime

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=173
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOCALHOST_ONLY=1
```

## Bunker Navigation

Send named goals directly:

```bash
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker std_msgs/msg/String "{data: door}"
ros2 topic pub --once --keep-alive 2 /landmark_navigator/go_marker std_msgs/msg/String "{data: home}"
```

Arrival topics:

```text
/door_navigation/arrived    std_msgs/msg/Bool
/home_navigation/arrived    std_msgs/msg/Bool
```

`data: true` means Nav2 reached that landmark. The true value is a short pulse,
currently about 5 seconds, so treat a single observed true as success even if
the topic returns to false afterward.

## Front PiPER-X APIs

Agent Server:

```text
http://127.0.0.1:8893
```

Low-level marker API:

```text
http://127.0.0.1:8892
```

Use `8893` from OpenClaw.

Important commands:

```bash
curl -sS http://127.0.0.1:8893/health
curl -sS -X POST http://127.0.0.1:8893/lease/acquire -H 'Content-Type: application/json' -d '{"client":"openclaw","ttl_s":120}'
curl -sS -X POST http://127.0.0.1:8893/tools/search-marker -H 'Content-Type: application/json' -d '{"execute":true,"arm":"front"}'
curl -sS -X POST http://127.0.0.1:8893/tools/touch-marker -H 'Content-Type: application/json' -d '{"execute":true,"arm":"front"}'
curl -sS -X POST http://127.0.0.1:8893/tools/go-manipulation-pose -H 'Content-Type: application/json' -d '{"execute":true,"arm":"front"}'
curl -sS -X POST http://127.0.0.1:8893/tools/go-nav-pose -H 'Content-Type: application/json' -d '{"execute":true,"arm":"front"}'
curl -sS -X POST http://127.0.0.1:8893/tools/go-previous -H 'Content-Type: application/json' -d '{"execute":true,"arm":"front"}'
curl -sS -X POST http://127.0.0.1:8893/tools/go-found-marker -H 'Content-Type: application/json' -d '{"execute":true,"arm":"front"}'
```

Manipulation completion topic:

```text
/manipulation_task/finished    std_msgs/msg/Bool
```

`true` means one PiPER API request returned. Use the API JSON to decide whether it succeeded.

## Do Not Start Duplicates

If Trystan's stack already publishes a driver, camera, TF, MoveIt, or Nav2 node, use it. Do not launch another one.
