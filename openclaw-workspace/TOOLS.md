# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## AbotClaw Fleet Notes

Last heartbeat check: 2026-07-31 16:10 Asia/Hong_Kong.

### Piper

- Control/API endpoint: `http://localhost:8888`
- Safe health check: `curl --noproxy '*' http://localhost:8888/health`
- Fleet endpoint and guide locations are documented in `ROBOT.md`.
- Do not use old port `8890`.
- Do not use the regular Piper Agent Server for PiPER-X marker/home commands.
- 2026-07-13 12:10 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`.
- 2026-07-13 12:40 health check: `http://localhost:8888/health` failed to connect; treat Piper Agent Server as unavailable until the endpoint responds again.
- 2026-07-13 14:12 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-13 14:12 `/state` returned six arm joint positions, zero joint velocities, gripper position `0.0`, and table camera state `true`.
- 2026-07-13 15:12 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-13 15:12 `/state` returned six arm joint positions, zero joint velocities, gripper position `0.0194`, and table camera state `true`.
- 2026-07-13 16:10 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-13 18:10 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-13 18:10 `/state` returned six arm joint positions, zero joint velocities, gripper position `0.0003`, and table camera state `true`.
- 2026-07-14 11:10 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-14 11:10 `/state` returned six arm joint positions, zero joint velocities, gripper position `0.0003`, and table camera state `true`.
- 2026-07-14 14:40 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-14 14:40 `/state` returned six arm joint positions, zero joint velocities, gripper position `0.0003`, and table camera state `true`.
- 2026-07-14 17:40 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-14 17:40 `/state` returned six arm joint positions, zero joint velocities, gripper position `0.0003`, and table camera state `true`.
- 2026-07-15 09:40 health check failed twice: `curl --noproxy '*' http://localhost:8888/health` could not connect to port `8888`; `ss -ltnp` showed no listener on `:8888`. Treat Piper Agent Server as unavailable until the endpoint responds again.
- 2026-07-15 11:40 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`.
- 2026-07-15 11:40 `/state` returned six arm joint positions, zero joint velocities, gripper position `-0.0004`, and table camera state `true`.
- 2026-07-16 12:40 health check failed twice: `curl --noproxy '*' http://localhost:8888/health` could not connect to port `8888`; `ss -ltnp` showed no listener on `:8888`. Treat Piper Agent Server as unavailable until the endpoint responds again.
- 2026-07-31 15:40 `/state` returned six zeroed arm joint positions, zero joint velocities, zeroed end pose, gripper position `0.0`, and an empty `cameras` object despite `/cameras` listing `table_camera` as enabled.
- 2026-07-16 14:40 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `6b3356787bd4deb669954a3a972b2b504923c2ef`, git dirty `false`.
- 2026-07-16 15:09 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `407205d7f8ed62806c7e7e62f17e3606f28fee36`, git dirty `false`.
- 2026-07-16 15:39 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `407205d7f8ed62806c7e7e62f17e3606f28fee36`, git dirty `false`.
- 2026-07-16 16:10 health check: `status=ok`, lease holder `piper-manipulation` with about `277s` remaining, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `eca1c66ce619273e62a42828c2124ec24b33fadd`, git dirty `true`.
- 2026-07-16 16:40 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `cd2d38d8c0af0a6030dce1cfa6f3be53bd3647ea`, git dirty `true`.
- 2026-07-16 17:10 health check: `status=ok`, lease holder `piper-manipulation` with about `257s` remaining, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `cd2d38d8c0af0a6030dce1cfa6f3be53bd3647ea`, git dirty `true`.
- 2026-07-17 09:40 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, git dirty `false`.
- 2026-07-17 15:42 health check: `status=ok`, no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, git dirty `true`.

### PiPER-X

- Control/API endpoint: `http://127.0.0.1:8892`
- Safe health check: `curl -sS http://127.0.0.1:8892/health`
- Skill: `abotclaw-piper-x-manipulation`; short alias: `piper-touch-marker`
- Robot layer contract: `/home/dase-hw101/ABot-Claw/robot_layer/arm_piper_x`
- Active ROS 2 package: `/home/dase-hw101/agx_arm_ws/src/piper_x_aruco_wall_approach`
- Use for: `approach the marker`, `touch the marker`, `go home`, `save current pose as home`.
- Do not use `http://127.0.0.1:8888` or `robot_layer/arm_piper` for PiPER-X.
- Physical execution requires the local API health field `execution_allowed: true`.
- "Touch" is geometric only; there is no force-confirmed contact.
- Integrated startup reuses Trystan's ROS 2 stack: front PiPER on `can2`, rear
  PiPER on `can3`, Bunker on `can4`, front MoveIt namespace `/front_piper`,
  group `arm`, tip `tcp_link`, and combined TF chain
  `base_link -> front_piper_flange_link -> front_camera_color_optical_frame`.
  Do not start duplicate drivers, cameras, robot-state publishers, or MoveIt.

### Cameras

- RealSense is visible over USB as `8086:0bdc Intel Corp. Intel RealSense Generic Device` in the 2026-07-13 11:11 Asia/Hong_Kong heartbeat check; `rs-enumerate-devices` is not installed, so model-level identification was not available from librealsense.
- Integrated camera is visible over USB as `5986:11b0 Bison Electronics Inc. Integrated Camera`.
- Piper API reported `cam_low` with alias `table_camera`, enabled `true`, frame endpoint `/cameras/cam_low/frame`; `/cameras/table_camera/frame` returned a live JPEG frame at 2026-07-13 12:10.
- Piper state endpoint reported `table_camera=true`, `left_camera_0_left=false`, `cam_left_wrist=false`, and `cam_right_wrist=false` at 2026-07-13 12:10.
- 2026-07-13 12:40 table camera liveness could not be checked because Piper Agent Server on `http://localhost:8888` was not reachable.
- 2026-07-13 14:12 USB shows Intel RealSense Depth Camera 555 (`8086:0b56`) and integrated camera (`5986:11b0`).
- 2026-07-13 14:12 Piper `/state` reports `table_camera=true`, `left_camera_0_left=false`, `cam_left_wrist=false`, and `cam_right_wrist=false`.
- 2026-07-13 15:12 USB shows Intel RealSense Depth Camera 555 (`8086:0b56`), integrated camera (`5986:11b0`), and OpenMoko CAN adapter (`1d50:606f`).
- 2026-07-13 15:12 Piper `/cameras` reports `cam_low` alias `table_camera`, enabled `true`; `/cameras/table_camera/frame` returned live JPEG `640x360`, 49,391 bytes.
- 2026-07-13 15:12 Piper `/state` reports `table_camera=true`, `left_camera_0_left=false`, `cam_left_wrist=false`, and `cam_right_wrist=false`.
- 2026-07-13 18:10 Piper `/cameras` reports `cam_low` alias `table_camera`, enabled `true`; `/cameras/table_camera/frame` returned live JPEG `640x360`, 46,583 bytes.
- 2026-07-14 11:10 Piper `/cameras` reports `cam_low` alias `table_camera`, enabled `true`; `/cameras/table_camera/frame` returned live JPEG `640x360`, 45,009 bytes.
- 2026-07-14 14:40 Piper `/cameras` reports `cam_low` alias `table_camera`, enabled `true`; `/cameras/table_camera/frame` returned live JPEG `640x360`, 46,151 bytes.
- 2026-07-14 17:40 Piper `/cameras` reports `cam_low` alias `table_camera`, enabled `true`; `/cameras/table_camera/frame` returned live JPEG `640x360`, 46,151 bytes.
- 2026-07-15 09:40 Piper `/cameras` and `/cameras/table_camera/frame` could not be checked because Piper Agent Server on `http://localhost:8888` was not reachable.
- 2026-07-15 11:40 Piper `/cameras` reports `cam_low` alias `table_camera`, enabled `true`, frame endpoint `/cameras/cam_low/frame`.
- 2026-07-31 15:40 Piper `/cameras` again reports `cam_low` alias `table_camera`, enabled `true`, frame endpoint `/cameras/cam_low/frame`, but `/state` currently omits camera flags.
- 2026-07-31 16:10 `/cameras/table_camera/frame` returned HTTP `503 Service Unavailable` even though `/cameras` still lists `table_camera` as enabled. Treat Piper table-camera capture as unhealthy until frame fetch succeeds again.
- Camera ownership/mapping to Piper, G1, or Go2 still needs explicit documentation before camera-dependent robot skills assume a view.

### Shared Services

- Shared service host in `SERVICE.md`: `192.168.1.104`.
- Heartbeat health checks on 2026-07-13 12:10 Asia/Hong_Kong timed out on ports `8012`, `8013`, `8014`, and `8015`.
- Heartbeat health checks on 2026-07-13 14:12 Asia/Hong_Kong timed out on ports `8012`, `8013`, `8014`, and `8015`.
- Heartbeat health checks on 2026-07-13 15:12 Asia/Hong_Kong timed out on ports `8012`, `8013`, `8014`, and `8015`.
- 2026-07-13 16:10 configured Piper/YoloSDK endpoint `http://192.168.1.104:8013/health` returned `status=ok`, `model_loaded=true`, `device=cuda:0`.
- 2026-07-13 16:10 shared-service host checks still timed out on `172.29.24.220:8012`, `:8014`, and `:8015`; do not assume SpatialMemory, VLAC, or GraspAnything are available until `/health` succeeds.
- 2026-07-13 18:10 configured Piper/YoloSDK endpoint `http://192.168.1.104:8013/health` returned `status=ok`, `model_loaded=true`, `device=cuda:0`.
- 2026-07-13 18:10 shared-service host checks timed out on `172.29.24.220:8012`, `:8013`, `:8014`, and `:8015`.
- 2026-07-14 11:10 configured Piper/YoloSDK endpoint `http://192.168.1.104:8013/health` returned `status=ok`, `model_loaded=true`, `device=cuda:0`.
- 2026-07-14 11:10 shared-service host checks timed out on `172.29.24.220:8012`, `:8013`, `:8014`, and `:8015`.
- 2026-07-14 14:40 configured Piper/YoloSDK endpoint `http://192.168.1.104:8013/health` returned `status=ok`, `model_loaded=true`, `device=cuda:0`.
- 2026-07-14 14:40 shared-service host checks timed out on `172.29.24.220:8012`, `:8013`, `:8014`, and `:8015`.
- 2026-07-14 17:40 configured Piper/YoloSDK endpoint `http://192.168.1.104:8013/health` returned `status=ok`, `model_loaded=true`, `device=cuda:0`.
- 2026-07-14 17:40 shared-service host checks timed out on `172.29.24.220:8012`, `:8013`, `:8014`, and `:8015`.
- 2026-07-15 09:40 configured Piper/YoloSDK endpoint `http://192.168.1.104:8013/health` failed twice: connection to port `8013` failed.
- 2026-07-15 09:40 shared-service host checks timed out on `172.29.24.220:8012`, `:8013`, `:8014`, and `:8015`.
- 2026-07-15 11:40 shared-service host checks failed to connect on `192.168.1.104:8012`, `:8013`, `:8014`, and `:8015`; do not assume SpatialMemory, YOLO, VLAC, or GraspAnything are available until `/health` succeeds.
- 2026-07-15 13:10 shared-service host checks failed to connect on `192.168.1.104:8012`, `:8013`, and `:8014`; `192.168.1.104:8015/health` responded with `status=degraded`, `backend=depth_fallback`, `model_loaded=true`, and `yolo_ok=false` because its local `127.0.0.1:8013/health` dependency refused connection. Treat GraspAnything as partially available only for supervised checks until YOLO is healthy.
- 2026-07-15 15:40 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-16 12:40 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-16 15:09 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-16 15:39 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-16 16:10 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-16 16:40 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-16 17:10 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-17 09:40 shared-service host checks: `192.168.1.104:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `192.168.1.104:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`; `192.168.1.104:8012` and `:8014` still refused connection, so SpatialMemory and VLAC remain unavailable until `/health` succeeds.
- 2026-07-17 15:02 live check: `192.168.1.104:8014/health` returned VLAC `status=ok`, `device=cuda:0`, `model_type=internvl2`, `model_loaded=true`; update prior assumption that `:8014` was down.
- 2026-07-17 15:02 live check: `192.168.1.104:8014/health` returned VLAC `status=ok`, `device=cuda:0`, `model_type=internvl2`, `model_loaded=true`; update prior assumption that `:8014` was down.
- 2026-07-17 15:08 non-motion plan-only Piper manipulation preflight for `red cup -> purple folder` failed because TF lookup from `table_camera_color_optical_frame` to `base_link` was missing, even though color/depth/camera_info were live and YOLO/GraspAnything were healthy. Treat perception-grounded autonomous pick/place as not ready until this TF chain is fixed.
- 2026-07-17 15:42 shared-service host checks: `192.168.1.104:8012/health` returned SpatialMemory `status=ok`, `records=1`; `:8013/health` returned YOLO `status=ok`, `device=cuda:0`, `model_loaded=true`; `:8014/health` returned VLAC `status=ok`, `device=cuda:0`, `model_type=internvl2`, `model_loaded=true`; `:8015/health` returned GraspAnything `status=ok`, `backend=depth_fallback`, `model_loaded=true`, `yolo_ok=true`. Update prior assumption that `:8012` was down.
- 2026-07-17 16:17 live non-motion red-cup pick preflight succeeded after adding `local_red_cup_h007_001`; `run_piper_manipulation.py --task pick --source 'red cup' --source-provider perception --grasp-region auto --hover-height 0.07 --plan-only --timeout 180` returned `FINAL_STATUS completed`, selected voxel `local_red_cup_h007_001`, nearest voxel displacement about `0.00355 m`, transit `50` points, descend fraction `1.0`, lift fraction `1.0`, and joint5 critical margin about `0.1175 rad`.
- 2026-07-17 16:20 live full non-motion `red cup -> purple folder` plan-only check still failed at destination placement: transport to destination hover succeeded, but `destination_descend` stopped with `Cartesian path destination_descend incomplete: fraction=0.250000`; source pick and transport hover are now good, remaining blocker is destination descend / place kinematics with tight joint margins (joint5 about `0.0506 rad`, joint6 about `0.0231 rad`).
- 2026-07-17 16:49 live full non-motion `red cup -> purple folder` plan-only check passed end-to-end after destination candidate/IK changes: source transit/descend/lift succeeded, destination transport/descend/rise all succeeded, and full place-sequence critical margin across joint5/joint6 was about `0.1209 rad`.
- 2026-07-17 17:06 physical `--execute` attempt for `red cup -> purple folder` was blocked immediately by `PLACE_EXECUTION_DISABLED destination has no fully validated place region`; no motion executed. Treat destination place execution as disabled until an execution-validated place region/voxel is added for the purple-folder placement pose.
- 2026-07-20 11:11 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder and executor git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, but shared services on `192.168.1.104` all refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 12:10 live heartbeat check: Piper `http://localhost:8888/health` still returned `status=ok` with no lease holder, while shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 12:40 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template remained `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 13:10 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template remained `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 13:40 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template remained `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 14:10 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template still reported `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 14:40 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template still reported `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 15:10 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template still reported `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 16:40 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template still reported `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 16:10 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template still reported `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-20 15:40 live heartbeat check: Piper `http://localhost:8888/health` returned `status=ok` with no lease holder; executor template still reported `lazy-perception-v2`, git SHA `8f37032708b084ec5dd7b49bbd7ce44a0b11dc10`, and git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. G1/Go2 endpoint notes remain placeholders only in `ROBOT.md`; no deployed base URLs or auth details are documented yet.
- 2026-07-23 14:43 live heartbeat check: Piper `http://localhost:8888/health` refused connection, and shared services on `192.168.1.104` also refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Treat Piper, SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-23 16:10 live heartbeat check: Piper `http://localhost:8888/health` still refused connection, and shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Outage persists across the afternoon; treat Piper, SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-23 16:40 live heartbeat check: Piper `http://localhost:8888/health` still refused connection; shared services on `192.168.1.104` timed out on `:8012` and `:8013` and still failed on `:8014` and `:8015`. Outage persists into late afternoon; treat Piper, SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-23 17:10 live heartbeat check: Piper `http://localhost:8888/health` still refused connection. Shared services partially recovered: `192.168.1.104:8012/health` returned SpatialMemory `status=ok` and `192.168.1.104:8014/health` returned VLAC `status=ok`, while YOLO `:8013` and GraspAnything `:8015` still refused connection. Treat Piper, YOLO, and GraspAnything as unavailable; SpatialMemory and VLAC are back up.
- 2026-07-30 10:43 live heartbeat check: Piper `http://localhost:8888/health` refused connection, and shared services on `192.168.1.104` refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. This is a broader regression from the partial recovery seen on 2026-07-23 17:10; treat Piper, SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-30 14:40 live heartbeat check: Piper `http://localhost:8888/health` still refused connection. Shared services partially recovered again: `192.168.1.104:8012/health` returned SpatialMemory `status=ok` and `192.168.1.104:8014/health` returned VLAC `status=ok`, while YOLO `:8013` and GraspAnything `:8015` still refused connection. Treat Piper, YOLO, and GraspAnything as unavailable; SpatialMemory and VLAC are back up.
- 2026-07-30 15:10 live heartbeat check: Piper `http://localhost:8888/health` still refused connection. Shared services remain partially recovered: `192.168.1.104:8012/health` returned SpatialMemory `status=ok` with `records=1`, and `192.168.1.104:8014/health` returned VLAC `status=ok`, `device=cuda:0`, `model_type=internvl2`, `model_loaded=true`, while YOLO `:8013` and GraspAnything `:8015` still refused connection. Treat Piper, YOLO, and GraspAnything as unavailable; SpatialMemory and VLAC are back up.
- 2026-07-30 16:10 live heartbeat check: Piper `http://localhost:8888/health` still refused connection. Shared services remain partially recovered: `192.168.1.104:8012/health` returned SpatialMemory `status=ok` with `records=1`, and `192.168.1.104:8014/health` returned VLAC `status=ok`, `device=cuda:0`, `model_type=internvl2`, `model_loaded=true`, while YOLO `:8013` and GraspAnything `:8015` still refused connection. Treat Piper, YOLO, and GraspAnything as unavailable; SpatialMemory and VLAC are back up.
- 2026-07-31 09:40 live heartbeat check: Piper `http://localhost:8888/health` still refused connection, and shared services on `192.168.1.104` also refused connection on `:8012`, `:8013`, `:8014`, and `:8015`. Partial recovery seen on 2026-07-30 did not hold overnight; treat Piper, SpatialMemory, YOLO, VLAC, and GraspAnything as unavailable until `/health` succeeds again.
- 2026-07-31 15:10 live heartbeat check: Piper `http://localhost:8888/health` recovered and returned `status=ok` with no lease holder, queue length `0`, paused `false`, resetting `false`, `reset_on_release=false`; executor template `lazy-perception-v2`, git SHA `010c7daa6f73597b71671bda9bdfa4cd512a9ee0`, git dirty `true`. Shared services on `192.168.1.104` still refused connection on `:8012`, `:8013`, `:8014`, and `:8015`, so SpatialMemory, YOLO, VLAC, and GraspAnything remain unavailable.

### Missing Fleet Details

- Unitree G1 control/API endpoint is not filled in.
- Unitree Go2 control/API endpoint is not filled in.
- Auth method/API key details are not documented.
- E-stop/recovery procedure and teleoperation fallback path are not documented.
- 2026-07-30 12:10 repo-wide search found no non-placeholder G1/Go2 base URLs or auth notes outside `ROBOT.md` placeholders; current workspace still lacks deployed G1/Go2 connection details.
- 2026-07-30 18:10 repeat repo-wide search still found only placeholder G1/Go2 URLs in `ROBOT.md` and docs/examples; no deployed G1/Go2 endpoint or auth details are documented in the workspace.

## Related

- [Agent workspace](/concepts/agent-workspace)
