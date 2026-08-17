# PiPER-X D435i Wrist-Camera Hand-Eye Calibration

This guide calibrates a wrist-mounted Intel RealSense D435i on an AgileX PiPER-X using ROS 2 Jazzy, ArUco, AgileX `handeye_calibration_ros`, and the current AgileX `agx_arm_ros` stack.

It deliberately does **not** use the older ROS 1 `piper_ros` package or `ros2 launch piper ...`: that is not the PiPER-X workflow. The hardware driver is `agx_arm_ctrl` with `arm_type:=piper_x`.

## Quick Start Checklist

1. Keep the D435i and gripper mechanically rigid. The calibration becomes invalid if the camera mount moves.
2. Place a measured ArUco marker on a fixed surface. Do not move it during collection.
3. Start the PiPER-X driver with `fw_version:=v189` and `control_enabled:=false`.
4. Start RealSense, ArUco, and the TCP pose bridge.
5. Collect 15--20 materially different stationary arm poses, then save the result.
6. Copy the result to `~/handeye/config/piper_x_d435i_eye_in_hand.json`.
7. Start the normal runtime, publish the resulting `flange_link -> camera_link` TF, and verify the complete TF chain in RViz.

> Warning: the calibration result is valid only for this PiPER-X, gripper/TCP definition, D435i serial number, and unchanged mechanical camera mount. It is not a universal PiPER-X transform.

## 1. Architecture

### Hardware and software contract

| Item | Value |
| --- | --- |
| Arm | AgileX PiPER-X |
| End effector | Standard AgileX parallel gripper |
| Driver parameters | `arm_type:=piper_x`, `effector_type:=agx_gripper` |
| Camera | Intel RealSense D435i fixed to wrist |
| Calibration method | Eye-in-hand |
| ROS distribution | ROS 2 Jazzy, `/opt/ros/jazzy` |
| AgileX workspace | `~/agx_arm_ws` |
| Calibration workspace | `~/ros2_ws` |
| Hand-eye helper directory | `~/handeye` |

### Runtime data and TF chain

```text
PiPER-X CAN / agx_arm_ctrl
  -> /feedback/joint_states
  -> /feedback/tcp_pose (geometry_msgs/msg/PoseStamped)
  -> robot_state_publisher
  -> base_link -> ... -> flange_link

RealSense D435i
  -> color image + camera_info
  -> camera_link -> ... -> camera_color_optical_frame

Hand-eye result + RealSense internal TF
  -> static flange_link -> camera_link
  -> complete chain below

base_link
  └── PiPER-X links
       └── flange_link
            └── camera_link
                 └── RealSense internal frames
                      └── camera_color_optical_frame
```

The hand-eye package consumes a `geometry_msgs/msg/Pose`, while the current PiPER-X driver publishes `/feedback/tcp_pose` as `geometry_msgs/msg/PoseStamped`. The documented bridge removes only the header; it does not change position or orientation.

The calibrated transform is published to `camera_link`, not directly to `camera_color_optical_frame`. RealSense already owns its internal camera TF tree; publishing a second parent directly to the optical frame would create competing TF authority.

## 2. Official Repositories and Packages

Use the current AgileX ROS 2 stack:

```text
agx_arm_ros
agx_arm_ctrl
agx_arm_description
```

Official hand-eye package:

```bash
git clone -b humble \
  https://github.com/agilexrobotics/handeye_calibration_ros.git
```

The `humble` branch built successfully under ROS 2 Jazzy in this setup. Do **not** source `/opt/ros/humble/setup.bash`: it does not exist on this machine.

Required packages are:

```text
handeye_calibration_ros
aruco_ros
realsense2_camera
tf2_ros
robot_state_publisher
joint_state_publisher
joint_state_publisher_gui
rviz2
```

Install ArUco on Jazzy:

```bash
sudo apt update
sudo apt install -y ros-jazzy-aruco-ros
```

Verify package availability:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 pkg prefix handeye_calibration_ros
ros2 pkg prefix aruco_ros
ros2 pkg prefix realsense2_camera
```

Expected prefixes:

```text
/home/dase-hw101/ros2_ws/install/handeye_calibration_ros
/opt/ros/jazzy
/opt/ros/jazzy
```

## 3. One-Time Calibration Workspace Setup

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

git clone -b humble \
  https://github.com/agilexrobotics/handeye_calibration_ros.git

cd ~/ros2_ws

rosdep install \
  --from-paths src \
  --ignore-src \
  -r \
  -y

colcon build --symlink-install
```

Every new terminal starts with:

```bash
source /opt/ros/jazzy/setup.bash
```

Then source the needed overlays:

```bash
source ~/agx_arm_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash
```

## 4. Firmware and Driver Warnings

PiPER-X firmware auto-detection returned an empty software-version string in this setup and caused:

```text
Invalid firmware version:
```

Use this known working explicit setting:

```text
fw_version:=v189
```

During calibration, command input must remain disabled:

```text
control_enabled:=false
```

Never run two hardware driver launches against `can0`. In particular, do not run `start_single_agx_arm_rviz.launch.py` with the standalone hardware driver below: it starts another driver.

## 5. Create the TCP Pose Bridge

Create `~/handeye/tcp_pose_bridge.py` with the following exact content:

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose, PoseStamped


class TcpPoseBridge(Node):
    def __init__(self):
        super().__init__('tcp_pose_bridge')

        self.publisher = self.create_publisher(
            Pose,
            '/end_pose',
            10,
        )

        self.subscription = self.create_subscription(
            PoseStamped,
            '/feedback/tcp_pose',
            self.pose_callback,
            10,
        )

        self.get_logger().info(
            'Bridging /feedback/tcp_pose [PoseStamped] '
            'to /end_pose [Pose]'
        )

    def pose_callback(self, msg: PoseStamped):
        self.publisher.publish(msg.pose)


def main():
    rclpy.init()
    node = TcpPoseBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

Make it executable:

```bash
chmod +x ~/handeye/tcp_pose_bridge.py
```

## 6. Calibration Startup: Five Fresh Terminals

Close earlier ROS processes before beginning. The following commands assume fresh terminals.

### Terminal 1: PiPER-X driver

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash

ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
  can_port:=can0 \
  arm_type:=piper_x \
  effector_type:=agx_gripper \
  fw_version:=v189 \
  control_enabled:=false
```

Verify before proceeding:

```bash
ros2 topic type /feedback/tcp_pose
ros2 topic echo /feedback/tcp_pose --once
```

Expected type:

```text
geometry_msgs/msg/PoseStamped
```

### Terminal 2: RealSense D435i

Colour is required for calibration; depth may be disabled.

```bash
source /opt/ros/jazzy/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  enable_color:=true \
  enable_depth:=false \
  rgb_camera.color_profile:=640x480x30
```

Expected topics normally include:

```text
/front_camera/color/image_raw
/front_camera/color/camera_info
```

Verify:

```bash
ros2 topic list | grep color
ros2 topic echo /front_camera/color/camera_info --once
```

The usual optical frame is `camera_color_optical_frame`.

### Terminal 3: ArUco detector

Replace the example marker ID and marker size with your actual marker. The size is the **physical black-square side length**, in metres.

Example: marker ID `582`, size `0.0677` metres.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 run aruco_ros single --ros-args \
  -p marker_id:=582 \
  -p marker_size:=0.0677 \
  -p image_is_rectified:=true \
  -p reference_frame:=camera_color_optical_frame \
  -p camera_frame:=camera_color_optical_frame \
  -p marker_frame:=aruco_marker_frame \
  -p corner_refinement:=LINES \
  -r /image:=/front_camera/color/image_raw \
  -r /camera_info:=/front_camera/color/camera_info
```

Verify:

```bash
ros2 topic type /aruco_single/pose
ros2 topic echo /aruco_single/pose --once
```

Expected type:

```text
geometry_msgs/msg/PoseStamped
```

The ArUco marker must stay completely stationary for the entire calibration.

### Terminal 4: TCP pose bridge

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash

python3 ~/handeye/tcp_pose_bridge.py
```

Expected startup message:

```text
Bridging /feedback/tcp_pose [PoseStamped] to /end_pose [Pose]
```

Verify:

```bash
ros2 topic type /end_pose
ros2 topic echo /end_pose --once
```

Expected type:

```text
geometry_msgs/msg/Pose
```

### Terminal 5: Hand-eye calibration program

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash

mkdir -p ~/ros2_ws/result
cd ~/ros2_ws

ros2 run handeye_calibration_ros handeye_calibration --ros-args \
  -p piper_topic:=/end_pose \
  -p marker_topic:=/aruco_single/pose \
  -p mode:=eye_in_hand \
  -p result_save_path:=$HOME/ros2_ws/result
```

Expected startup includes:

```text
mode: eye_in_hand
min_num: 10
piper_topic: /end_pose
marker_topic: /aruco_single/pose
result_save_path: /home/dase-hw101/ros2_ws/result
```

Controls:

```text
Enter  collect a sample
d      delete the previous sample
q      calculate and save the result
c      exit
```

A valid collected sample prints:

```text
wait marker data... [ok]
wait piper data... [ok]
```

## 7. Collect Good Eye-in-Hand Samples

1. Keep the marker fixed on a table or calibration board.
2. Move the wrist-mounted camera around the marker using a safe, controlled method.
3. Stop the arm fully before every sample and wait for the image to settle.
4. Keep the whole marker visible in every image.
5. Change roll, pitch, yaw, distance, left/right position, and height between samples.
6. Do not collect many nearly identical poses.
7. Collect at least 10 samples; prefer 15--20 good, diverse samples.

The verified run collected 21 samples and calculated after sample 22 by entering `q`.

## 8. Save the Calibration

Verified example result:

```json
{
  "position": [
    -0.03325362536889407,
    -0.04784194427852743,
    0.08630445414919316
  ],
  "orientation": [
    -0.0400543683846712,
    -0.0020645358673945235,
    0.011914828710571071,
    0.9991243276598539
  ],
  "rpy": [
    [
      -0.08017405150425999,
      -0.0031709794581423934,
      0.023976595541682157
    ]
  ]
}
```

This example was saved as:

```text
~/ros2_ws/result/2026-08-04_19-17-00_calibration.json
```

Copy it to the stable runtime location:

```bash
mkdir -p ~/handeye/config

cp \
  ~/ros2_ws/result/2026-08-04_19-17-00_calibration.json \
  ~/handeye/config/piper_x_d435i_eye_in_hand.json
```

The result represents the camera optical frame relative to the gripper/TCP frame used by `/feedback/tcp_pose`.

## 9. Create the Hand-Eye TF Publisher

Create `~/handeye/publish_handeye_tf.py`:

```python
#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from scipy.spatial.transform import Rotation
from tf2_ros import (
    Buffer,
    StaticTransformBroadcaster,
    TransformException,
    TransformListener,
)


def matrix_from_values(position, quaternion):
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = Rotation.from_quat(quaternion).as_matrix()
    matrix[:3, 3] = np.asarray(position, dtype=float)
    return matrix


def matrix_from_transform(transform):
    translation = transform.transform.translation
    rotation = transform.transform.rotation

    return matrix_from_values(
        [translation.x, translation.y, translation.z],
        [rotation.x, rotation.y, rotation.z, rotation.w],
    )


class HandEyeTFPublisher(Node):
    def __init__(self, calibration_file, parent_frame, camera_root, optical_frame):
        super().__init__('piper_x_handeye_tf_publisher')
        self.parent_frame = parent_frame
        self.camera_root = camera_root
        self.optical_frame = optical_frame

        with open(calibration_file, 'r', encoding='utf-8') as file:
            calibration = json.load(file)

        self.t_parent_optical = matrix_from_values(
            calibration['position'], calibration['orientation']
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=False)
        self.static_broadcaster = StaticTransformBroadcaster(self)
        self.published = False
        self.wait_message_printed = False
        self.timer = self.create_timer(0.5, self.try_publish)

        self.get_logger().info(f'Loaded calibration: {calibration_file}')
        self.get_logger().info(f'Will publish {parent_frame} -> {camera_root}')

    def try_publish(self):
        if self.published:
            return

        try:
            camera_to_optical_msg = self.tf_buffer.lookup_transform(
                self.camera_root,
                self.optical_frame,
                Time(),
                timeout=Duration(seconds=0.25),
            )
        except TransformException:
            if not self.wait_message_printed:
                self.get_logger().info(
                    'Waiting for RealSense TF '
                    f'{self.camera_root} -> {self.optical_frame}...'
                )
                self.wait_message_printed = True
            return

        t_camera_optical = matrix_from_transform(camera_to_optical_msg)
        t_parent_camera = self.t_parent_optical @ np.linalg.inv(t_camera_optical)
        translation = t_parent_camera[:3, 3]
        quaternion = Rotation.from_matrix(t_parent_camera[:3, :3]).as_quat()

        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = self.parent_frame
        transform.child_frame_id = self.camera_root
        transform.transform.translation.x = float(translation[0])
        transform.transform.translation.y = float(translation[1])
        transform.transform.translation.z = float(translation[2])
        transform.transform.rotation.x = float(quaternion[0])
        transform.transform.rotation.y = float(quaternion[1])
        transform.transform.rotation.z = float(quaternion[2])
        transform.transform.rotation.w = float(quaternion[3])

        self.static_broadcaster.sendTransform(transform)
        self.published = True
        self.timer.cancel()
        self.get_logger().info(
            f'Published calibrated TF: {self.parent_frame} -> {self.camera_root}'
        )
        self.get_logger().info(
            'Translation [m]: '
            f'x={translation[0]:+.6f}, y={translation[1]:+.6f}, '
            f'z={translation[2]:+.6f}'
        )
        self.get_logger().info('Keep this node running during robot operation.')


def main():
    parser = argparse.ArgumentParser(
        description='Publish PiPER-X hand-eye calibration as ROS TF.'
    )
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--parent-frame', default='flange_link')
    parser.add_argument('--camera-root', default='camera_link')
    parser.add_argument('--optical-frame', default='camera_color_optical_frame')
    args = parser.parse_args()

    calibration_file = Path(args.calibration).expanduser()
    if not calibration_file.is_file():
        raise FileNotFoundError(
            f'Calibration file does not exist: {calibration_file}'
        )

    rclpy.init()
    node = HandEyeTFPublisher(
        str(calibration_file), args.parent_frame, args.camera_root, args.optical_frame
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

```bash
chmod +x ~/handeye/publish_handeye_tf.py
```

## 10. Normal Runtime After Calibration

ArUco, the TCP bridge, and the calibration program are not needed in normal operation. Use four terminals.

### Runtime Terminal 1: Physical PiPER-X driver

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash

ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
  can_port:=can0 \
  arm_type:=piper_x \
  effector_type:=agx_gripper \
  fw_version:=v189 \
  control_enabled:=false
```

### Runtime Terminal 2: Robot model and RViz

The RobotModel did not display correctly with `control:=false`. Use the description/RViz launch separately:

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash

ros2 launch agx_arm_description display.launch.py \
  arm_type:=piper_x \
  effector_type:=agx_gripper \
  follow:=true \
  control:=true \
  feedback_topic:=/feedback/joint_states \
  control_topic:=/control/joint_states
```

This starts RViz, RobotModel, `robot_state_publisher`, and the joint-state GUI. Its sliders may publish `/control/joint_states`, but the separate physical driver remains protected by `control_enabled:=false`.

### Runtime Terminal 3: D435i colour, depth, and point cloud

```bash
source /opt/ros/jazzy/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  enable_color:=true \
  enable_depth:=true \
  align_depth.enable:=true \
  pointcloud.enable:=true
```

### Runtime Terminal 4: Calibrated TF publisher

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash

python3 ~/handeye/publish_handeye_tf.py \
  --calibration ~/handeye/config/piper_x_d435i_eye_in_hand.json \
  --parent-frame flange_link \
  --camera-root camera_link \
  --optical-frame camera_color_optical_frame
```

Expected output:

```text
Loaded calibration: ...
Will publish flange_link -> camera_link
Published calibrated TF: flange_link -> camera_link
Keep this node running during robot operation.
```

## 11. Verify TF and RViz

The complete wrist-camera transform should change as the physical wrist moves:

```bash
source /opt/ros/jazzy/setup.bash
source ~/agx_arm_ws/install/setup.bash

ros2 run tf2_ros tf2_echo \
  base_link \
  camera_color_optical_frame
```

The direct calibrated transform stays static:

```bash
ros2 run tf2_ros tf2_echo \
  flange_link \
  camera_link
```

In RViz set:

```text
Fixed Frame: base_link
```

Add `RobotModel`, `TF`, and `PointCloud2`. Locate the D435i cloud topic:

```bash
ros2 topic list | grep points
```

It commonly resembles:

```text
/front_camera/depth/color/points
```

The point cloud should be attached to the wrist and move with the arm.

## 12. Troubleshooting

### `Package 'handeye_calibration_ros' not found`

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 pkg prefix handeye_calibration_ros
```

### `Package 'piper' not found`

Do not install the older driver for this workflow. Use `agx_arm_ctrl` with `arm_type:=piper_x`.

### Calibration waits at `wait piper data...`

`/end_pose` is absent or wrong. Confirm `/feedback/tcp_pose`, start `~/handeye/tcp_pose_bridge.py`, then verify `/end_pose` has type `geometry_msgs/msg/Pose`.

### Calibration waits at `wait marker data...`

Confirm the stationary marker is visible, the ID and black-square side length are correct, `/aruco_single/pose` exists, remappings are correct, and `camera_color_optical_frame` is the actual optical frame.

### `Invalid firmware version:`

Use `fw_version:=v189`.

### `/opt/ros/humble/setup.bash: No such file or directory`

This machine uses Jazzy:

```bash
source /opt/ros/jazzy/setup.bash
```

### RobotModel missing or broken

Use the separate description launch with `follow:=true` and `control:=true`, while keeping the actual physical driver separate with `control_enabled:=false`.

### TF publisher waits for RealSense TF

Start RealSense first, then check:

```bash
ros2 run tf2_ros tf2_echo \
  camera_link \
  camera_color_optical_frame
```

### Point cloud detached from wrist

Check the whole chain:

```bash
ros2 run tf2_ros tf2_echo \
  base_link \
  camera_color_optical_frame
```

Confirm the publisher parameters are `flange_link`, `camera_link`, and `camera_color_optical_frame` respectively.

## 13. Known Working Configuration

```text
ROS:                 Jazzy
PiPER-X driver:      agx_arm_ctrl
Arm type:            piper_x
Effector type:       agx_gripper
Firmware parameter:  v189
Hardware CAN:        can0
Calibration mode:    eye_in_hand
Driver TCP topic:    /feedback/tcp_pose (PoseStamped)
Calibration TCP:     /end_pose (Pose, via bridge)
Marker pose:         /aruco_single/pose (PoseStamped)
Calibration output:  ~/handeye/config/piper_x_d435i_eye_in_hand.json
Calibrated TF:       flange_link -> camera_link
RViz fixed frame:    base_link
```

Do not claim precision from a solver result alone. After calibration, validate it by observing a fixed marker from multiple arm poses: its computed base-frame position should remain consistent. Recalibrate after any camera-bracket, gripper/TCP, arm-mount, or camera replacement.
