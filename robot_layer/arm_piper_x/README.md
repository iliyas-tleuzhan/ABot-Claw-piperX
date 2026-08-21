# ABot-Claw PiPER-X Robot Layer

This folder is the ABot-Claw-side contract for the AgileX PiPER-X arm.

It is intentionally separate from `robot_layer/arm_piper`, which is the older
regular-Piper Agent Server path on `127.0.0.1:8888`.

## Current Supported PiPER-X Capability

The active PiPER-X path is the ROS 2 Jazzy MoveIt wall-marker approach stack
wrapped by a PiPER-X Agent Server:

- OpenClaw-facing Agent Server: `http://127.0.0.1:8893`
- low-level marker/home bridge: `http://127.0.0.1:8892`
- health: `GET /health`
- state: `GET /state`
- lease: `POST /lease/acquire`, `POST /lease/release`
- approach marker: `POST /tools/approach-marker`
- geometric touch marker: `POST /tools/touch-marker`
- reactive marker search: `POST /tools/search-step`, `POST /tools/search-marker`
- move to saved found-marker pose: `POST /tools/go-found-marker`
- go to saved home pose: `POST /tools/go-home`
- save current pose as home: `POST /tools/save-home`
- go to saved previous pose: `POST /tools/go-previous`
- save current pose as previous: `POST /tools/save-previous`
- open AgileX gripper: `POST /tools/open-gripper`
- close AgileX gripper: `POST /tools/close-gripper`

The Agent Server reads ROS 2 feedback topics for state and calls the low-level
marker/home bridge for the already validated marker demo tools. It does not
talk directly to CAN or expose arbitrary joint commands.

## Hardware Contract

- robot model: AgileX PiPER-X
- ROS driver: `agx_arm_ros`
- arm launch argument: `arm_type:=piper_x`
- end effector: AgileX parallel gripper
- effector launch argument: `effector_type:=agx_gripper`
- firmware launch argument: `fw_version:=v189`
- CAN interface: `can2`, 1 Mbps, configured before ROS launch.
- Bunker CAN interface: `can4`; Bunker movement is outside the PiPER-X marker-search primitive.
- MoveIt namespace: `/front_piper`
- MoveIt planning group: `arm` in Trystan's front-arm semantic model
- MoveIt TCP/tip link: `tcp_link` inside that namespaced planning model
- TCP offset: `[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]`
- arm feedback topic: `/front_piper/feedback/joint_states`
- TCP feedback topic: `/feedback/tcp_pose`
- gripper command topic: `/control/joint_states`
- gripper command type: `sensor_msgs/msg/JointState`
- gripper joint name: `gripper`
- gripper opening width range: `[0.0, 0.1] m`
- gripper effort range: `[0.5, 3.0] N`
- wrist camera: Intel RealSense D435i depth camera
- integrated front color image: `/front_camera/color/image_raw`
- integrated front camera info: `/front_camera/color/camera_info`
- integrated front point cloud: `/front_camera/depth/color/points`
- ArUco pose: `/aruco_single/pose`
- marker: ID `6`, size `0.06 m`
- hand-eye calibration file:
  `/home/dase-hw101/handeye/config/piper_x_d435i_eye_in_hand.json`
- calibrated TF parent: `front_piper_flange_link`
- calibrated camera frames: `front_camera_link` and
  `front_camera_color_optical_frame`

## Bunker Integration Defaults

For the combined PiPER-on-Bunker system, Trystan's Nav2 full-system stack owns
the RealSense camera, Bunker base, front/rear PiPER hardware drivers, combined
`/joint_states`, and robot TF. The PiPER-X marker stack defaults to consuming
those integrated front-camera/front-arm topics instead of starting another
RealSense publisher:

- `use_realsense:=false`
- RGB image: `/front_camera/color/image_raw`
- camera info: `/front_camera/color/camera_info`
- point cloud: `/front_camera/depth/color/points`
- camera optical frame: `front_camera_color_optical_frame`
- integrated robot joint state input: `/joint_states`
- adapted raw front-arm feedback output: `/front_piper/feedback/joint_states`

The integrated robot has two intentional naming layers. The combined URDF/TF
tree uses `front_piper_joint1..6`, `front_piper_flange_link`, and
`front_camera_color_optical_frame`. Trystan's namespaced front MoveIt instance
uses its front-only semantic model with raw `joint1..6` and `tcp_link`, and its
trajectory bridge converts those raw trajectory names into commands for the
front driver. The front driver already publishes raw feedback on
`/front_piper/feedback/joint_states`, so the adapter is disabled by default;
enable it only when that raw topic is absent and only prefixed `/joint_states`
is available.

This adapter handles feedback only. The trajectory action and control topic
are provided by this package when `use_piper_motion_stack:=true`; otherwise
they must already be provided by another compatible front-PiPER controller:

- `/front_piper/arm_controller/follow_joint_trajectory`
- `/front_piper/control/joint_states`

The marker/search nodes talk to the existing namespaced MoveIt instance through
`move_group_namespace:=front_piper` and consume the combined
`/robot_description` plus the matching integrated front SRDF. Planning uses
`front_piper_joint1..6` and `front_piper_flange_link`; saved trajectory goals
must use the same prefixed names. Perception uses the combined TF tree:
`base_link -> front_piper_flange_link -> front_camera_color_optical_frame`.
Their ROS services and HTTP API stay at the root namespace for OpenClaw.

## Reactive Marker Search

The old calibrated 3x3 search-pose grid is replaced by a fast directional
search. Full auto search uses the sequence `current -> right -> left -> up ->
up_right -> up_left -> center -> down -> down_right -> down_left`. Joint1 makes
the wide horizontal sweeps; joint4 only selects the upper/lower camera levels.
OpenClaw may decide one direction at a time, but must call the Agent Server
`/tools/search-step` endpoint. The robot layer executes configured MoveIt
targets and stops as soon as marker 6 is visible.
Successful `search-marker` saves the current six-joint pose as `found_marker`
and leaves the arm at that pose.

The only search-ending limit is `max_steps: 100`; there is no wall-clock search
time limit.

Allowed directions: `left`, `right`, `up`, `down`, `up_left`, `up_right`,
`down_left`, `down_right`, `center`, `current`. Full auto search is horizontal-
coverage-first; it no longer prioritizes joint4 upward motion.

## Official Source Boundary

Use the installed AgileX ROS 2 stack as the source of truth:

- driver and MoveIt launch files:
  `/home/dase-hw101/agx_arm_ws/src/agx_arm_ros`
- PiPER-X URDF and meshes:
  `/home/dase-hw101/agx_arm_ws/src/agx_arm_ros/src/agx_arm_description/agx_arm_urdf/piper_x`
- MoveIt joint limits and controllers:
  `/home/dase-hw101/agx_arm_ws/src/agx_arm_ros/src/agx_arm_moveit/config`

The public AgileX organization documents that `agx_arm_ros` is the ROS 2 driver
for Piper-family arms including PiPER-X, and that `agx_arm_urdf` owns the URDF,
Xacro, and mesh resources.

## Current Generality Boundary

This folder does not claim PiPER-X general tabletop pick/place support yet.
Regular tabletop pick/place is still handled by `robot_layer/arm_piper`.

The Agent Server now supports the verified AgileX gripper width command
interface. Generic Cartesian/joint pose endpoints still fail closed until the
real PiPER-X MoveIt pose-command contract and workspace validation are
implemented.

Current PiPER-X skills are:

- approach ArUco marker
- geometric touch of ArUco marker
- save current pose as home
- go to saved home pose
- save current pose as previous
- go to saved previous pose
- open gripper
- close gripper

There is no force sensor in this path. "Touch" means a geometric approach to a
small clearance from the fitted wall surface, not force-confirmed contact.
"Close gripper" means command the configured opening width, not confirmed
object grasp.

The previous pose is a six-joint snapshot. Physical marker and home motions
save the current pose as previous before sending the new trajectory. The
operator can also call `save-previous` manually from a known safe pose.

## Quick Checks

```bash
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py health
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py state
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py approach --plan-only
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py touch --plan-only --retract --return-home-after
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py save-home
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py home --plan-only
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py save-previous
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py previous --plan-only
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py open-gripper --plan-only
python3 robot_layer/arm_piper_x/agent_server/run_piper_x_agent_task.py close-gripper --plan-only
```

Use `--execute` only when the ROS 2 stack health reports
`execution_allowed: true` and the operator is ready to supervise the arm.
