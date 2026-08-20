# Robot Models

These directories keep the robot-description files used by the PiPER-X
manipulation layer. They are reference inputs for launch and MoveIt
integration; the active Bunker stack remains the source of runtime topics and
TF.

## `piper-on-bunker/`

The integrated Bunker model used by Trystan's navigation and MoveIt stack.
The front arm uses prefixed names such as `front_piper_joint1` and
`front_piper_flange_link`. The camera chain uses
`front_camera_link -> front_camera_color_optical_frame`.

`piper_arm_macro.xacro` is included by the combined URDF and is kept beside it
so the model can be inspected or reused without losing that dependency.

## `single-piper/`

The standalone AgileX PiPER model used for single-arm development and
calibration. It uses the unprefixed AgileX joint/link names and must not be
combined with the Bunker URDF or its prefixed MoveIt SRDF.
