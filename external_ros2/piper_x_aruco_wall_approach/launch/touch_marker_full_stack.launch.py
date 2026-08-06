from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    execute_allowed = LaunchConfiguration("execute_allowed")
    calibration_file = LaunchConfiguration("calibration_file")
    point_cloud_topic = LaunchConfiguration("point_cloud_topic")
    marker_id = LaunchConfiguration("marker_id")
    marker_size = LaunchConfiguration("marker_size")
    api_port = LaunchConfiguration("api_port")
    api_host = LaunchConfiguration("api_host")
    pre_clearance = LaunchConfiguration("pre_clearance")
    final_clearance = LaunchConfiguration("final_clearance")
    retract_after = LaunchConfiguration("retract_after")
    can_port = LaunchConfiguration("can_port")
    auto_enable = LaunchConfiguration("auto_enable")
    follow = LaunchConfiguration("follow")
    auto_control_gate = LaunchConfiguration("auto_control_gate")
    enable_color = LaunchConfiguration("enable_color")
    enable_depth = LaunchConfiguration("enable_depth")
    align_depth = LaunchConfiguration("align_depth")
    pointcloud = LaunchConfiguration("pointcloud")
    marker_timeout = LaunchConfiguration("marker_timeout")
    point_cloud_timeout = LaunchConfiguration("point_cloud_timeout")
    home_pose_file = LaunchConfiguration("home_pose_file")
    joint_state_topic = LaunchConfiguration("joint_state_topic")
    joint_state_timeout = LaunchConfiguration("joint_state_timeout")

    package_share = FindPackageShare("piper_x_aruco_wall_approach")

    return LaunchDescription([
        DeclareLaunchArgument("execute_allowed", default_value="false"),
        DeclareLaunchArgument(
            "calibration_file",
            default_value="/home/dase-hw101/handeye/config/piper_x_d435i_eye_in_hand.json",
        ),
        DeclareLaunchArgument(
            "point_cloud_topic",
            default_value="/camera/camera/depth/color/points",
        ),
        DeclareLaunchArgument("marker_id", default_value="6"),
        DeclareLaunchArgument("marker_size", default_value="0.10"),
        DeclareLaunchArgument("api_port", default_value="8892"),
        DeclareLaunchArgument("api_host", default_value="127.0.0.1"),
        DeclareLaunchArgument("pre_clearance", default_value="0.05"),
        DeclareLaunchArgument("final_clearance", default_value="0.005"),
        DeclareLaunchArgument("retract_after", default_value="true"),
        DeclareLaunchArgument("use_rviz", default_value="false"),
        DeclareLaunchArgument("can_port", default_value="can0"),
        DeclareLaunchArgument("auto_enable", default_value="false"),
        DeclareLaunchArgument("follow", default_value="true"),
        DeclareLaunchArgument("auto_control_gate", default_value="false"),
        DeclareLaunchArgument("enable_color", default_value="true"),
        DeclareLaunchArgument("enable_depth", default_value="true"),
        DeclareLaunchArgument("align_depth", default_value="true"),
        DeclareLaunchArgument("pointcloud", default_value="true"),
        DeclareLaunchArgument("marker_timeout", default_value="1.0"),
        DeclareLaunchArgument("point_cloud_timeout", default_value="2.0"),
        DeclareLaunchArgument("joint_state_topic", default_value="/feedback/joint_states"),
        DeclareLaunchArgument("joint_state_timeout", default_value="1.0"),
        DeclareLaunchArgument(
            "home_pose_file",
            default_value=PathJoinSubstitution([
                package_share,
                "config",
                "piper_x_home_pose.yaml",
            ]),
        ),
        SetEnvironmentVariable("PIPER_TOUCH_ALLOW_EXECUTION", execute_allowed),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare("agx_arm_ctrl"),
                    "launch",
                    "start_single_agx_arm_moveit.launch.py",
                ])
            ]),
            launch_arguments={
                "can_port": can_port,
                "arm_type": "piper_x",
                "effector_type": "agx_gripper",
                "fw_version": "v189",
                "auto_enable": auto_enable,
                "follow": follow,
                "auto_control_gate": auto_control_gate,
                "use_rviz": LaunchConfiguration("use_rviz"),
                "tcp_offset": "[0.0, 0.0, 0.1425, 0.0, 0.0, 0.0]",
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare("realsense2_camera"),
                    "launch",
                    "rs_launch.py",
                ])
            ]),
            launch_arguments={
                "enable_color": enable_color,
                "enable_depth": enable_depth,
                "align_depth.enable": align_depth,
                "pointcloud.enable": pointcloud,
            }.items(),
        ),
        Node(
            package="piper_x_aruco_wall_approach",
            executable="publish_handeye_tf.py",
            name="piper_x_handeye_tf_publisher",
            output="screen",
            arguments=[
                "--calibration",
                calibration_file,
                "--parent-frame",
                "flange_link",
                "--camera-root",
                "camera_link",
                "--optical-frame",
                "camera_color_optical_frame",
            ],
        ),
        Node(
            package="aruco_ros",
            executable="single",
            name="aruco_single",
            output="screen",
            parameters=[{
                "marker_id": ParameterValue(marker_id, value_type=int),
                "marker_size": ParameterValue(marker_size, value_type=float),
                "image_is_rectified": True,
                "reference_frame": "base_link",
                "camera_frame": "camera_color_optical_frame",
                "marker_frame": "aruco_marker_frame",
            }],
            remappings=[
                ("/image", "/camera/camera/color/image_raw"),
                ("/camera_info", "/camera/camera/color/camera_info"),
            ],
        ),
        Node(
            package="piper_x_aruco_wall_approach",
            executable="wall_approach_node",
            name="wall_approach_node",
            output="screen",
            parameters=[
                PathJoinSubstitution([package_share, "config", "wall_approach.yaml"]),
                {
                    "execute": False,
                    "clearance": ParameterValue(pre_clearance, value_type=float),
                    "final_clearance": ParameterValue(final_clearance, value_type=float),
                    "retract_after": ParameterValue(retract_after, value_type=bool),
                    "point_cloud_topic": point_cloud_topic,
                },
            ],
        ),
        Node(
            package="piper_x_aruco_wall_approach",
            executable="piper_touch_marker_api.py",
            name="piper_touch_marker_api",
            output="screen",
            arguments=[
                "--host",
                api_host,
                "--port",
                api_port,
                "--marker-id",
                marker_id,
                "--marker-size-m",
                marker_size,
                "--point-cloud-topic",
                point_cloud_topic,
                "--marker-timeout-s",
                marker_timeout,
                "--point-cloud-timeout-s",
                point_cloud_timeout,
                "--home-pose-file",
                home_pose_file,
                "--joint-state-topic",
                joint_state_topic,
                "--joint-state-timeout-s",
                joint_state_timeout,
            ],
        ),
    ])
