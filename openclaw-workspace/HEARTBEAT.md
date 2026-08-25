# HEARTBEAT.md

Current expected runtime heartbeat.

## OpenClaw

- Model: `my-proxy/gpt-5.5`.
- Thinking: `medium`.
- Workspace: `/ros2_ws/src/ABot-Claw-piperX/openclaw-workspace`.
- Gateway port: `18789`.

## Required Robot Services

- PiPER-X Agent Server: `127.0.0.1:8893`.
- PiPER-X Marker API: `127.0.0.1:8892`.
- ROS domain: `173`.
- Front PiPER feedback topic: `/front_piper/feedback/joint_states`.
- Front trajectory action: `/front_piper/arm_controller/follow_joint_trajectory`.
- Front camera topics under `/front_camera`.

## Handoff Topics

- `/door_navigation/arrived`: Bool true pulse on door arrival.
- `/home_navigation/arrived`: Bool true pulse on home arrival.
- `/manipulation_task/finished`: continuous Bool.

If these are missing, report exactly which one is missing. Do not start duplicate drivers to compensate.
