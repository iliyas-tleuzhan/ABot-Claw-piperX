---
summary: "Current ABotClaw piper-on-bunker robot contract"
read_when:
  - Every session
---

# ROBOT.md

This OpenClaw workspace is for the current piper-on-bunker integration only.

## Robot

- Platform: AgileX Bunker Mini with PiPER-X arms.
- Active manipulation arm: front PiPER-X only.
- Rear PiPER-X: present in the robot description, but ignore it for now. Do not command, search, touch, home, nav-pose, teach, or gripper-control the rear arm unless this file is intentionally updated later.
- Bunker CAN: `can4`.
- Front PiPER CAN: `can2`.
- Rear PiPER CAN: `can3`, currently not used by OpenClaw.
- ROS 2: Humble in Trystan's integrated Docker.
- ROS domain: `173`.
- RMW: `rmw_fastrtps_cpp`.
- Localhost DDS: `ROS_LOCALHOST_ONLY=1`.

## Containers

- Main integrated runtime: `trystan-bunker-navigation`.
- OpenClaw workspace path in that container: `/ros2_ws/src/ABot-Claw-piperX/openclaw-workspace`.
- ABotClaw repo path in that container: `/ros2_ws/src/ABot-Claw-piperX`.

## Cameras

- Front wrist camera: RealSense D435i.
- Front image topics: `/front_camera/color/image_raw`, `/front_camera/color/camera_info`.
- Front depth topics: `/front_camera/aligned_depth_to_color/image_raw`, `/front_camera/depth/color/points`.
- Marker: ArUco ID `6`, size `0.06 m`.
- Camera TF: `front_camera_color_optical_frame`.

## TF And MoveIt

- Use Trystan's integrated URDF/SRDF and robot-state publisher.
- Do not start a second robot-state publisher, camera driver, PiPER driver, MoveIt instance, or Bunker driver.
- Front arm namespace: `/front_piper`.
- Front joint feedback: `/front_piper/feedback/joint_states`.
- Front trajectory action: `/front_piper/arm_controller/follow_joint_trajectory`.
- Front gripper command topic: `/front_piper/control/joint_states`.
- Useful TF chain: `base_link -> front_piper_flange_link -> front_camera_color_optical_frame`.

## APIs

- Low-level PiPER marker API: `http://127.0.0.1:8892`.
- OpenClaw-facing PiPER Agent Server: `http://127.0.0.1:8893`.
- OpenClaw should call `8893`; `8892` is the ROS bridge behind it.

## Operating Rule

Navigation and manipulation are separate modes.

- During navigation, keep the PiPER arms parked in nav pose and do not move them.
- After navigation reaches `door` or `home`, OpenClaw watches for one `data:true` pulse on the corresponding arrival topic. The pulse may clear after about 5 seconds; that still counts as successful arrival.
- Before manipulation, move the front arm to manipulation pose.
- After manipulation tasks are done, move the front arm to nav pose before starting navigation again.
- Keep the map; do not delete or rebuild it because the arm moved.
