---
name: piper-touch-marker
description: Use the PiPER-X ROS 2 wall-approach tool for requests such as "touch the marker", "touch ArUco marker 6", "move the Piper arm to the marker", "approach the marker", "point at the marker", "press the marked location", "go home", or "return the Piper arm home".
---

# PiPER Touch Marker

This is the short OpenClaw-facing skill for the current PiPER-X marker demo.
For full robot details, use `abotclaw-piper-x-manipulation`.

Default local API:

```text
http://127.0.0.1:8892
```

## Required Health Check

Always call:

```bash
curl -sS http://127.0.0.1:8892/health
```

Physical execution requires `execution_allowed: true`.

## Commands

Approach marker:

```bash
curl -sS -X POST http://127.0.0.1:8892/tools/piper/approach-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"pre_clearance_m":0.05,"final_clearance_m":0.005,"retract_after":false,"retract_distance_m":0.05,"final_velocity_scaling":0.05,"return_home_after":false,"home_duration_s":6.0}'
```

Touch marker, retract, then home:

```bash
curl -sS -X POST http://127.0.0.1:8892/tools/piper/touch-marker \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"pre_clearance_m":0.05,"final_clearance_m":0.005,"retract_after":true,"retract_distance_m":0.05,"final_velocity_scaling":0.05,"return_home_after":true,"home_duration_s":6.0}'
```

Go home:

```bash
curl -sS -X POST http://127.0.0.1:8892/tools/piper/go-home \
  -H 'Content-Type: application/json' \
  -d '{"execute":true,"duration_s":6.0}'
```

Save current pose as home:

```bash
curl -sS -X POST http://127.0.0.1:8892/tools/piper/save-home \
  -H 'Content-Type: application/json' \
  -d '{"pose_name":"home"}'
```

## Safety

This skill targets PiPER-X through the ROS 2 bridge on `8892`, not the regular
Piper Agent Server on `8888`.

"Touch" is geometric only:

```json
{
  "contact_confirmed": false,
  "completion_type": "geometric_surface_approach"
}
```
