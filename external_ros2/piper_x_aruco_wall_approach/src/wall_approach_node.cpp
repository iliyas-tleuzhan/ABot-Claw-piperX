#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <memory>
#include <mutex>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include <Eigen/Geometry>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <moveit_msgs/msg/collision_object.hpp>
#include <moveit_msgs/msg/constraints.hpp>
#include <moveit_msgs/msg/joint_constraint.hpp>
#include <pcl/ModelCoefficients.h>
#include <pcl/filters/filter.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <pcl_conversions/pcl_conversions.h>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <shape_msgs/msg/solid_primitive.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <visualization_msgs/msg/marker.hpp>

#include "piper_x_aruco_wall_approach/srv/run_marker_task.hpp"

namespace
{
constexpr double kMinimumFinalClearanceM = 0.003;
constexpr double kMaximumFinalVelocityScaling = 0.25;

Eigen::Vector3d to_eigen(const geometry_msgs::msg::Point & point)
{
  return {point.x, point.y, point.z};
}

geometry_msgs::msg::Quaternion to_msg(const Eigen::Quaterniond & quaternion)
{
  geometry_msgs::msg::Quaternion message;
  message.x = quaternion.x();
  message.y = quaternion.y();
  message.z = quaternion.z();
  message.w = quaternion.w();
  return message;
}

Eigen::Vector3d rotate_vector(
  const geometry_msgs::msg::TransformStamped & transform,
  const Eigen::Vector3d & vector)
{
  const auto & rotation = transform.transform.rotation;
  const Eigen::Quaterniond quaternion(rotation.w, rotation.x, rotation.y, rotation.z);
  return quaternion.normalized() * vector;
}
}  // namespace

class WallApproachNode : public rclcpp::Node
{
public:
  WallApproachNode()
  : Node("wall_approach_node"), tf_buffer_(this->get_clock()), tf_listener_(tf_buffer_)
  {
    aruco_pose_topic_ = declare_parameter<std::string>("aruco_pose_topic", "/aruco_single/pose");
    point_cloud_topic_ = declare_parameter<std::string>(
      "point_cloud_topic", "/front_camera/depth/color/points");
    planning_group_ = declare_parameter<std::string>("planning_group", "arm");
    move_group_namespace_ = declare_parameter<std::string>("move_group_namespace", "");
    planning_scene_ = std::make_unique<moveit::planning_interface::PlanningSceneInterface>(
      move_group_namespace_);
    end_effector_link_ = declare_parameter<std::string>("end_effector_link", "tcp_link");
    base_frame_ = declare_parameter<std::string>("base_frame", "base_link");
    clearance_ = declare_parameter<double>("clearance", 0.05);
    crop_width_ = declare_parameter<double>("crop_width", 0.30);
    crop_height_ = declare_parameter<double>("crop_height", 0.30);
    crop_depth_ = declare_parameter<double>("crop_depth", 0.15);
    ransac_distance_threshold_ = declare_parameter<double>("ransac_distance_threshold", 0.01);
    wall_width_ = declare_parameter<double>("wall_width", 1.0);
    wall_height_ = declare_parameter<double>("wall_height", 1.0);
    wall_thickness_ = declare_parameter<double>("wall_thickness", 0.02);
    velocity_scaling_ = declare_parameter<double>("velocity_scaling", 0.10);
    acceleration_scaling_ = declare_parameter<double>("acceleration_scaling", 0.10);
    planning_time_ = declare_parameter<double>("planning_time", 10.0);
    planning_attempts_ = declare_parameter<int>("planning_attempts", 10);
    goal_position_tolerance_ = declare_parameter<double>("goal_position_tolerance", 0.01);
    goal_orientation_tolerance_ = declare_parameter<double>("goal_orientation_tolerance", 0.35);
    tool_roll_ = declare_parameter<double>("tool_roll", 0.0);
    execute_ = declare_parameter<bool>("execute", false);
    final_clearance_ = declare_parameter<double>("final_clearance", 0.005);
    retract_distance_ = declare_parameter<double>("retract_distance", 0.05);
    final_velocity_scaling_ = declare_parameter<double>("final_velocity_scaling", 0.05);
    retract_after_ = declare_parameter<bool>("retract_after", true);
    max_final_travel_ = declare_parameter<double>("max_final_travel", 0.06);
    prefer_elbow_motion_ = declare_parameter<bool>("prefer_elbow_motion", true);
    joint1_name_ = declare_parameter<std::string>("joint1_name", "joint1");
    joint1_planning_tolerances_rad_ = declare_parameter<std::vector<double>>(
      "joint1_planning_tolerances_rad", std::vector<double>{0.03, 0.06, 0.10, 0.15});
    normalise_joint1_tolerances();

    target_publisher_ = create_publisher<geometry_msgs::msg::PoseStamped>(
      "/wall_approach/target_pose", 10);
    pre_touch_publisher_ = create_publisher<geometry_msgs::msg::PoseStamped>(
      "/wall_approach/pre_touch_target", 10);
    final_target_publisher_ = create_publisher<geometry_msgs::msg::PoseStamped>(
      "/wall_approach/final_target", 10);
    marker_publisher_ = create_publisher<visualization_msgs::msg::Marker>(
      "/wall_approach/normal", 10);
    aruco_subscription_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      aruco_pose_topic_, rclcpp::QoS(1),
      [this](geometry_msgs::msg::PoseStamped::ConstSharedPtr message) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        marker_pose_ = *message;
      });
    cloud_subscription_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      point_cloud_topic_, rclcpp::SensorDataQoS(),
      [this](sensor_msgs::msg::PointCloud2::ConstSharedPtr message) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        cloud_ = *message;
      });
    service_ = create_service<std_srvs::srv::Trigger>(
      "/run_wall_approach",
      std::bind(&WallApproachNode::run, this, std::placeholders::_1, std::placeholders::_2));
    marker_task_service_ = create_service<piper_x_aruco_wall_approach::srv::RunMarkerTask>(
      "/run_marker_task",
      std::bind(
        &WallApproachNode::run_marker_task, this, std::placeholders::_1, std::placeholders::_2));

    RCLCPP_INFO(
      get_logger(), "Waiting for %s and %s; services: /run_wall_approach, /run_marker_task",
      aruco_pose_topic_.c_str(), point_cloud_topic_.c_str());
  }

  void initialise_moveit()
  {
    moveit::planning_interface::MoveGroupInterface::Options options(
      planning_group_, "robot_description", move_group_namespace_);
    move_group_ = std::make_unique<moveit::planning_interface::MoveGroupInterface>(
      shared_from_this(), options);
    move_group_->setEndEffectorLink(end_effector_link_);
    move_group_->setPoseReferenceFrame(base_frame_);
    move_group_->setMaxVelocityScalingFactor(velocity_scaling_);
    move_group_->setMaxAccelerationScalingFactor(acceleration_scaling_);
    move_group_->setPlanningTime(planning_time_);
    move_group_->setNumPlanningAttempts(planning_attempts_);
    move_group_->setGoalPositionTolerance(goal_position_tolerance_);
    move_group_->setGoalOrientationTolerance(goal_orientation_tolerance_);
    RCLCPP_INFO(
      get_logger(),
      "MoveIt ready: group=%s, namespace=%s, tip=%s, frame=%s, execute=%s, prefer_elbow_motion=%s",
      planning_group_.c_str(), move_group_namespace_.c_str(), end_effector_link_.c_str(), base_frame_.c_str(),
      execute_ ? "true" : "false", prefer_elbow_motion_ ? "true" : "false");
  }

private:
  void normalise_joint1_tolerances()
  {
    std::vector<double> filtered;
    for (const auto tolerance : joint1_planning_tolerances_rad_) {
      if (std::isfinite(tolerance) && tolerance > 0.0) {
        filtered.push_back(tolerance);
      }
    }
    if (filtered.empty()) {
      filtered = {0.03, 0.06, 0.10, 0.15};
    }
    std::sort(filtered.begin(), filtered.end());
    filtered.erase(std::unique(filtered.begin(), filtered.end()), filtered.end());
    joint1_planning_tolerances_rad_ = filtered;
  }

  std::optional<double> current_joint_position(
    const std::string & joint_name,
    std::string & error)
  {
    if (!move_group_) {
      error = "MoveIt interface is not ready";
      return std::nullopt;
    }
    const auto joint_names = move_group_->getJointNames();
    const auto joint_values = move_group_->getCurrentJointValues();
    if (joint_names.size() != joint_values.size()) {
      error = "MoveIt joint name/value sizes differ";
      return std::nullopt;
    }
    for (std::size_t index = 0; index < joint_names.size(); ++index) {
      if (joint_names[index] == joint_name) {
        return joint_values[index];
      }
    }
    error = "MoveIt current state does not contain " + joint_name;
    return std::nullopt;
  }

  moveit_msgs::msg::Constraints joint1_path_constraint(
    const double current_joint1,
    const double tolerance) const
  {
    moveit_msgs::msg::Constraints constraints;
    constraints.name = "prefer_elbow_motion_keep_joint1_near_current";

    moveit_msgs::msg::JointConstraint joint_constraint;
    joint_constraint.joint_name = joint1_name_;
    joint_constraint.position = current_joint1;
    joint_constraint.tolerance_above = tolerance;
    joint_constraint.tolerance_below = tolerance;
    joint_constraint.weight = 1.0;
    constraints.joint_constraints.push_back(joint_constraint);
    return constraints;
  }

  moveit::core::MoveItErrorCode plan_once(
    const geometry_msgs::msg::PoseStamped & target,
    moveit::planning_interface::MoveGroupInterface::Plan & plan)
  {
    move_group_->setStartStateToCurrentState();
    move_group_->setPoseTarget(target, end_effector_link_);
    const auto plan_result = move_group_->plan(plan);
    move_group_->clearPoseTargets();
    move_group_->clearPathConstraints();
    return plan_result;
  }

  bool marker_in_base(
    const geometry_msgs::msg::PoseStamped & input,
    geometry_msgs::msg::PoseStamped & output,
    std::string & error)
  {
    try {
      if (input.header.frame_id == base_frame_) {
        output = input;
        output.header.frame_id = base_frame_;
        return true;
      }
      const auto transform = tf_buffer_.lookupTransform(
        base_frame_, input.header.frame_id, input.header.stamp, rclcpp::Duration::from_seconds(1.0));
      tf2::doTransform(input, output, transform);
      return true;
    } catch (const tf2::TransformException & exception) {
      error = "cannot transform marker into " + base_frame_ + ": " + exception.what();
      return false;
    }
  }

  bool fit_plane(
    const geometry_msgs::msg::PoseStamped & marker_base,
    const sensor_msgs::msg::PointCloud2 & cloud_message,
    Eigen::Vector3d & normal_base,
    Eigen::Vector3d & centroid_base,
    std::string & error)
  {
    if (cloud_message.header.frame_id.empty()) {
      error = "point cloud has no frame_id";
      return false;
    }

    geometry_msgs::msg::PoseStamped marker_cloud;
    try {
      const auto transform = tf_buffer_.lookupTransform(
        cloud_message.header.frame_id, base_frame_, cloud_message.header.stamp,
        rclcpp::Duration::from_seconds(1.0));
      tf2::doTransform(marker_base, marker_cloud, transform);
    } catch (const tf2::TransformException & exception) {
      error = "cannot transform marker into cloud frame " + cloud_message.header.frame_id + ": " +
        exception.what();
      return false;
    }

    pcl::PointCloud<pcl::PointXYZ>::Ptr source(new pcl::PointCloud<pcl::PointXYZ>());
    pcl::fromROSMsg(cloud_message, *source);
    std::vector<int> finite_indices;
    pcl::removeNaNFromPointCloud(*source, *source, finite_indices);

    const auto centre = to_eigen(marker_cloud.pose.position);
    pcl::PointCloud<pcl::PointXYZ>::Ptr cropped(new pcl::PointCloud<pcl::PointXYZ>());
    cropped->reserve(source->size());
    for (const auto & point : source->points) {
      if (std::abs(point.x - centre.x()) <= crop_width_ / 2.0 &&
        std::abs(point.y - centre.y()) <= crop_height_ / 2.0 &&
        std::abs(point.z - centre.z()) <= crop_depth_ / 2.0)
      {
        cropped->push_back(point);
      }
    }
    if (cropped->size() < 50) {
      error = "depth crop has fewer than 50 finite points";
      return false;
    }

    pcl::SACSegmentation<pcl::PointXYZ> segmentation;
    segmentation.setOptimizeCoefficients(true);
    segmentation.setModelType(pcl::SACMODEL_PLANE);
    segmentation.setMethodType(pcl::SAC_RANSAC);
    segmentation.setDistanceThreshold(ransac_distance_threshold_);
    segmentation.setInputCloud(cropped);
    pcl::PointIndices::Ptr inliers(new pcl::PointIndices());
    pcl::ModelCoefficients::Ptr coefficients(new pcl::ModelCoefficients());
    segmentation.segment(*inliers, *coefficients);
    if (inliers->indices.size() < 50 || coefficients->values.size() < 4) {
      error = "RANSAC did not find a plane with at least 50 inliers";
      return false;
    }

    Eigen::Vector3d centroid_cloud = Eigen::Vector3d::Zero();
    for (const auto index : inliers->indices) {
      const auto & point = cropped->points.at(static_cast<std::size_t>(index));
      centroid_cloud += Eigen::Vector3d(point.x, point.y, point.z);
    }
    centroid_cloud /= static_cast<double>(inliers->indices.size());

    Eigen::Vector3d normal_cloud(
      coefficients->values[0], coefficients->values[1], coefficients->values[2]);
    normal_cloud.normalize();
    // Camera origin is [0, 0, 0] in the point-cloud frame. Point toward it.
    if (normal_cloud.dot(-centroid_cloud) < 0.0) {
      normal_cloud = -normal_cloud;
    }

    try {
      const auto cloud_to_base = tf_buffer_.lookupTransform(
        base_frame_, cloud_message.header.frame_id, cloud_message.header.stamp,
        rclcpp::Duration::from_seconds(1.0));
      normal_base = rotate_vector(cloud_to_base, normal_cloud).normalized();
      const Eigen::Vector3d translation(
        cloud_to_base.transform.translation.x,
        cloud_to_base.transform.translation.y,
        cloud_to_base.transform.translation.z);
      centroid_base = rotate_vector(cloud_to_base, centroid_cloud) + translation;
    } catch (const tf2::TransformException & exception) {
      error = "cannot transform wall normal into " + base_frame_ + ": " + exception.what();
      return false;
    }

    RCLCPP_INFO(
      get_logger(), "Plane fit: crop=%zu, inliers=%zu, cloud_frame=%s",
      cropped->size(), inliers->indices.size(), cloud_message.header.frame_id.c_str());
    return true;
  }

  void update_wall(const Eigen::Vector3d & marker, const Eigen::Vector3d & normal)
  {
    moveit_msgs::msg::CollisionObject wall;
    wall.id = "detected_wall";
    wall.header.frame_id = base_frame_;
    shape_msgs::msg::SolidPrimitive box;
    box.type = shape_msgs::msg::SolidPrimitive::BOX;
    box.dimensions = {wall_width_, wall_height_, wall_thickness_};

    const Eigen::Quaterniond orientation = Eigen::Quaterniond::FromTwoVectors(
      Eigen::Vector3d::UnitZ(), normal);
    geometry_msgs::msg::Pose pose;
    const Eigen::Vector3d centre = marker - normal * (wall_thickness_ / 2.0);
    pose.position.x = centre.x();
    pose.position.y = centre.y();
    pose.position.z = centre.z();
    pose.orientation = to_msg(orientation.normalized());
    wall.primitives.push_back(box);
    wall.primitive_poses.push_back(pose);
    wall.operation = moveit_msgs::msg::CollisionObject::ADD;
    planning_scene_->applyCollisionObject(wall);
  }

  geometry_msgs::msg::PoseStamped target_pose(
    const geometry_msgs::msg::PoseStamped & marker,
    const Eigen::Vector3d & normal,
    const double clearance)
  {
    geometry_msgs::msg::PoseStamped target;
    target.header.stamp = now();
    target.header.frame_id = base_frame_;
    const Eigen::Vector3d position = to_eigen(marker.pose.position) + normal * clearance;
    target.pose.position.x = position.x();
    target.pose.position.y = position.y();
    target.pose.position.z = position.z();

    // tcp_link +Z approaches the wall, opposite the normal that points toward the robot.
    const Eigen::Quaterniond align = Eigen::Quaterniond::FromTwoVectors(
      Eigen::Vector3d::UnitZ(), -normal);
    const Eigen::Quaterniond roll(Eigen::AngleAxisd(tool_roll_, Eigen::Vector3d::UnitZ()));
    target.pose.orientation = to_msg((align * roll).normalized());
    return target;
  }

  void publish_normal(const Eigen::Vector3d & point, const Eigen::Vector3d & normal)
  {
    visualization_msgs::msg::Marker arrow;
    arrow.header.frame_id = base_frame_;
    arrow.header.stamp = now();
    arrow.ns = "wall_approach";
    arrow.id = 0;
    arrow.type = visualization_msgs::msg::Marker::ARROW;
    arrow.action = visualization_msgs::msg::Marker::ADD;
    geometry_msgs::msg::Point start;
    start.x = point.x(); start.y = point.y(); start.z = point.z();
    geometry_msgs::msg::Point end;
    const Eigen::Vector3d endpoint = point + normal * 0.20;
    end.x = endpoint.x(); end.y = endpoint.y(); end.z = endpoint.z();
    arrow.points = {start, end};
    arrow.scale.x = 0.015;
    arrow.scale.y = 0.03;
    arrow.scale.z = 0.04;
    arrow.color.r = 0.0F;
    arrow.color.g = 1.0F;
    arrow.color.b = 0.0F;
    arrow.color.a = 1.0F;
    marker_publisher_->publish(arrow);
  }

  bool plan_and_maybe_execute(
    const geometry_msgs::msg::PoseStamped & target,
    const double velocity_scaling,
    const bool execute,
    const std::string & plan_stage,
    const std::string & execution_stage,
    std::string & failed_stage,
    std::string & message)
  {
    if (!move_group_) {
      failed_stage = "readiness";
      message = "MoveIt interface is not ready";
      return false;
    }
    const double previous_velocity_scaling = velocity_scaling_;
    move_group_->setMaxVelocityScalingFactor(velocity_scaling);

    moveit::planning_interface::MoveGroupInterface::Plan plan;
    moveit::core::MoveItErrorCode plan_result(moveit::core::MoveItErrorCode::FAILURE);
    std::string joint_error;
    const auto current_joint1 = prefer_elbow_motion_ ?
      current_joint_position(joint1_name_, joint_error) : std::nullopt;

    if (prefer_elbow_motion_ && current_joint1) {
      for (const auto tolerance : joint1_planning_tolerances_rad_) {
        move_group_->setPathConstraints(joint1_path_constraint(*current_joint1, tolerance));
        RCLCPP_INFO(
          get_logger(), "Planning %s with %s constrained to %.4f +/- %.4f rad",
          plan_stage.c_str(), joint1_name_.c_str(), *current_joint1, tolerance);
        plan_result = plan_once(target, plan);
        if (plan_result == moveit::core::MoveItErrorCode::SUCCESS) {
          RCLCPP_INFO(
            get_logger(), "Planning %s succeeded with %s tolerance %.4f rad",
            plan_stage.c_str(), joint1_name_.c_str(), tolerance);
          break;
        }
      }
    } else {
      if (prefer_elbow_motion_) {
        RCLCPP_WARN(
          get_logger(), "Cannot apply %s preference for %s: %s",
          joint1_name_.c_str(), plan_stage.c_str(), joint_error.c_str());
      }
      plan_result = plan_once(target, plan);
    }

    move_group_->setMaxVelocityScalingFactor(previous_velocity_scaling);
    if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
      failed_stage = plan_stage;
      if (prefer_elbow_motion_ && current_joint1) {
        message = "MoveIt planning failed for " + plan_stage +
          " after trying bounded " + joint1_name_ +
          " tolerances; target was published for RViz";
      } else {
        message = "MoveIt planning failed for " + plan_stage + "; target was published for RViz";
      }
      return false;
    }
    if (!execute) {
      return true;
    }
    const auto execution_result = move_group_->execute(plan);
    if (execution_result != moveit::core::MoveItErrorCode::SUCCESS) {
      failed_stage = execution_stage;
      message = "MoveIt execution failed for " + execution_stage;
      return false;
    }
    return true;
  }

  bool validate_marker_task(
    const std::string & mode,
    const double pre_clearance,
    const double final_clearance,
    const double retract_distance,
    const double final_velocity_scaling,
    std::string & stage,
    std::string & message) const
  {
    stage = "readiness";
    if (mode != "approach" && mode != "touch") {
      message = "unsupported mode: " + mode;
      return false;
    }
    if (mode == "approach" && (!std::isfinite(pre_clearance) || pre_clearance < 0.0)) {
      message = "pre_clearance_m must be finite and non-negative";
      return false;
    }
    if (mode == "touch") {
      if (!std::isfinite(final_clearance) || final_clearance < kMinimumFinalClearanceM) {
        message = "final_clearance_m must be finite and at least 0.003 m";
        return false;
      }
      if (!std::isfinite(final_velocity_scaling) || final_velocity_scaling <= 0.0 ||
        final_velocity_scaling > kMaximumFinalVelocityScaling)
      {
        message = "final_velocity_scaling must be in (0.0, 0.25]";
        return false;
      }
    }
    return true;
  }

  struct MarkerTaskResult
  {
    bool success{false};
    std::string stage{"readiness"};
    std::string message;
    bool contact_confirmed{false};
    std::string completion_type{"geometric_surface_approach"};
  };

  MarkerTaskResult execute_marker_task(
    const std::string & mode,
    const bool execute,
    const double pre_clearance,
    const double final_clearance,
    const double retract_distance,
    const double final_velocity_scaling,
    const bool retract_after)
  {
    MarkerTaskResult result;
    if (!move_group_) {
      result.stage = "readiness";
      result.message = "MoveIt interface is not ready";
      return result;
    }
    if (!validate_marker_task(
        mode, pre_clearance, final_clearance, retract_distance, final_velocity_scaling,
        result.stage, result.message))
    {
      return result;
    }

    geometry_msgs::msg::PoseStamped marker;
    sensor_msgs::msg::PointCloud2 cloud;
    {
      std::lock_guard<std::mutex> data_lock(data_mutex_);
      if (!marker_pose_ || !cloud_) {
        result.stage = !marker_pose_ ? "marker_detection" : "point_cloud";
        result.message = "waiting for both ArUco pose and PointCloud2";
        return result;
      }
      marker = *marker_pose_;
      cloud = *cloud_;
    }

    std::string error;
    geometry_msgs::msg::PoseStamped marker_base;
    if (!marker_in_base(marker, marker_base, error)) {
      result.stage = "transform";
      result.message = error;
      return result;
    }

    Eigen::Vector3d normal_base;
    Eigen::Vector3d centroid_base;
    if (!fit_plane(marker_base, cloud, normal_base, centroid_base, error)) {
      result.stage = "plane_fit";
      result.message = error;
      return result;
    }

    const Eigen::Vector3d marker_position = to_eigen(marker_base.pose.position);
    update_wall(marker_position, normal_base);
    publish_normal(centroid_base, normal_base);

    if (mode == "approach") {
      const auto approach_target = target_pose(marker_base, normal_base, pre_clearance);
      target_publisher_->publish(approach_target);
      pre_touch_publisher_->publish(approach_target);

      if (!plan_and_maybe_execute(
          approach_target, velocity_scaling_, execute, "approach_plan", "approach_execution",
          result.stage, result.message))
      {
        return result;
      }

      result.success = true;
      result.stage = "complete";
      result.message = execute ?
        "geometric marker approach completed" :
        "geometric marker approach plan succeeded (execute=false)";
      return result;
    }

    const auto final_target = target_pose(marker_base, normal_base, final_clearance);
    target_publisher_->publish(final_target);
    final_target_publisher_->publish(final_target);
    if (!plan_and_maybe_execute(
        final_target, final_velocity_scaling, execute, "touch_plan", "touch_execution",
        result.stage, result.message))
    {
      return result;
    }

    result.success = true;
    result.stage = "complete";
    result.completion_type = "single_moveit_marker_touch";
    result.message = execute ?
      "single MoveIt marker touch completed; retract_after ignored by direct touch mode" :
      "single MoveIt marker touch plan succeeded (execute=false)";
    if (retract_after && execute) {
      RCLCPP_INFO(
        get_logger(), "touch request had retract_after=true, but direct touch mode uses one plan only");
    }
    return result;
  }

  void run(
    const std::shared_ptr<std_srvs::srv::Trigger::Request> /* request */,
    std::shared_ptr<std_srvs::srv::Trigger::Response> response)
  {
    std::lock_guard<std::mutex> operation_lock(operation_mutex_);
    const auto result = execute_marker_task(
      "approach", execute_, clearance_, final_clearance_, retract_distance_,
      final_velocity_scaling_, false);
    response->success = result.success;
    response->message = result.message;
  }

  void run_marker_task(
    const std::shared_ptr<piper_x_aruco_wall_approach::srv::RunMarkerTask::Request> request,
    std::shared_ptr<piper_x_aruco_wall_approach::srv::RunMarkerTask::Response> response)
  {
    std::lock_guard<std::mutex> operation_lock(operation_mutex_);
    const auto result = execute_marker_task(
      request->mode, request->execute, request->pre_clearance_m, request->final_clearance_m,
      request->retract_distance_m, request->final_velocity_scaling, request->retract_after);
    response->success = result.success;
    response->stage = result.stage;
    response->message = result.message;
    response->contact_confirmed = result.contact_confirmed;
    response->completion_type = result.completion_type;
  }

  std::string aruco_pose_topic_;
  std::string point_cloud_topic_;
  std::string planning_group_;
  std::string move_group_namespace_;
  std::string end_effector_link_;
  std::string base_frame_;
  double clearance_{};
  double crop_width_{};
  double crop_height_{};
  double crop_depth_{};
  double ransac_distance_threshold_{};
  double wall_width_{};
  double wall_height_{};
  double wall_thickness_{};
  double velocity_scaling_{};
  double acceleration_scaling_{};
  double planning_time_{};
  int planning_attempts_{};
  double goal_position_tolerance_{};
  double goal_orientation_tolerance_{};
  double tool_roll_{};
  double final_clearance_{};
  double retract_distance_{};
  double final_velocity_scaling_{};
  double max_final_travel_{};
  bool execute_{};
  bool retract_after_{};
  bool prefer_elbow_motion_{};
  std::string joint1_name_;
  std::vector<double> joint1_planning_tolerances_rad_;

  std::mutex data_mutex_;
  std::mutex operation_mutex_;
  std::optional<geometry_msgs::msg::PoseStamped> marker_pose_;
  std::optional<sensor_msgs::msg::PointCloud2> cloud_;
  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;
  std::unique_ptr<moveit::planning_interface::PlanningSceneInterface> planning_scene_;
  std::unique_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr aruco_subscription_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_subscription_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr target_publisher_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pre_touch_publisher_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr final_target_publisher_;
  rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr marker_publisher_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr service_;
  rclcpp::Service<piper_x_aruco_wall_approach::srv::RunMarkerTask>::SharedPtr marker_task_service_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<WallApproachNode>();
  node->initialise_moveit();
  rclcpp::executors::MultiThreadedExecutor executor;
  executor.add_node(node);
  executor.spin();
  rclcpp::shutdown();
  return 0;
}
