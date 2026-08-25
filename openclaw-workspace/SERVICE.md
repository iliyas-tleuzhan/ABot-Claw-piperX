# SERVICE.md

Current service registry for the piper-on-bunker system.

| Service | Base URL / Topic | Purpose |
|---|---|---|
| PiPER-X Agent Server | `http://127.0.0.1:8893` | OpenClaw-facing front-arm tools, lease, health, state |
| PiPER-X Marker API | `http://127.0.0.1:8892` | ROS bridge behind the Agent Server |
| Landmark command | `/landmark_navigator/go_marker` | Bunker named-goal command topic |
| Door arrival | `/door_navigation/arrived` | Continuous Bool; true after door arrival |
| Home arrival | `/home_navigation/arrived` | Continuous Bool; true after home arrival |
| Manipulation finished | `/manipulation_task/finished` | Continuous Bool; true after one PiPER API request returns |
| Front camera RGB | `/front_camera/color/image_raw` | D435i RGB for marker/perception |
| Front camera depth | `/front_camera/aligned_depth_to_color/image_raw` | D435i aligned depth |
| Front point cloud | `/front_camera/depth/color/points` | Point cloud for marker geometry |
| Front arm feedback | `/front_piper/feedback/joint_states` | Fresh front PiPER joint feedback |
| Front arm trajectory | `/front_piper/arm_controller/follow_joint_trajectory` | MoveIt/hardware trajectory action |

OpenClaw should use the Agent Server on `8893` for arm tools and use ROS topics for Bunker navigation.
