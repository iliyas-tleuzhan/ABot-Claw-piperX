---
name: abotclaw-operation-modes
description: Coordinate transitions between Bunker navigation mode and front PiPER-X manipulation mode.
---

# Operation Modes

The current system has two modes: `NAVIGATION` and `MANIPULATION`.

## NAVIGATION

- Bunker/Nav2 may move.
- PiPER arms must stay parked in nav pose.
- Do not run search, touch, gripper, teaching, or arbitrary arm motion.
- Use `/landmark_navigator/go_marker` for goals.
- Wait on `/door_navigation/arrived` or `/home_navigation/arrived`.

## MANIPULATION

- Bunker must be stopped.
- Front PiPER-X may move through the Agent Server on `8893`.
- Rear PiPER-X is ignored and must not be commanded.
- Use the front D435i for marker detection.
- Keep the existing map; do not delete or rebuild it because the arm moved.

## Transition Rules

Navigation to manipulation:

1. Wait until the requested arrival topic is `data: true`.
2. Announce that navigation ended.
3. Move the front PiPER-X to manipulation pose through `POST /tools/go-manipulation-pose`.
4. Run the requested manipulation tasks one at a time.
5. For each task, wait for `/manipulation_task/finished=true` and then inspect the API response for success or failure.

Manipulation to navigation:

1. Finish or stop the current front-arm task.
2. Move the front PiPER-X to nav pose through `POST /tools/go-nav-pose`.
3. Only then send the next Bunker navigation goal.

`/manipulation_task/finished=true` means one API request returned. It does not mean manipulation mode is over.
