#include <algorithm>
#include <chrono>
#include <cmath>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <rclcpp/rclcpp.hpp>

#include "piper_x_aruco_wall_approach/srv/search_marker.hpp"

using namespace std::chrono_literals;

namespace
{
constexpr std::size_t kJointCount = 6;

struct SearchPose
{
  std::string name;
  bool calibrated{false};
  double camera_yaw_deg{0.0};
  double camera_pitch_deg{0.0};
  std::vector<double> joints;
};

bool valid_joint_target(const std::vector<double> & joints)
{
  if (joints.size() != kJointCount) {
    return false;
  }
  return std::all_of(joints.begin(), joints.end(), [](const double value) {
    return std::isfinite(value);
  });
}
}  // namespace

class SearchMarkerNode : public rclcpp::Node
{
public:
  SearchMarkerNode()
  : Node("search_marker_node")
  {
    aruco_pose_topic_ = declare_parameter<std::string>("aruco_pose_topic", "/aruco_single/pose");
    planning_group_ = declare_parameter<std::string>("planning_group", "arm");
    marker_id_ = declare_parameter<int>("marker_id", 6);
    marker_timeout_s_ = declare_parameter<double>("marker_timeout_s", 1.0);
    settle_time_s_ = declare_parameter<double>("settle_time_s", 0.5);
    detection_window_frames_ = declare_parameter<int>("detection_window_frames", 5);
    required_detections_ = declare_parameter<int>("required_detections", 3);
    velocity_scaling_ = declare_parameter<double>("velocity_scaling", 0.10);
    acceleration_scaling_ = declare_parameter<double>("acceleration_scaling", 0.10);
    planning_time_ = declare_parameter<double>("planning_time", 10.0);
    planning_attempts_ = declare_parameter<int>("planning_attempts", 10);
    return_to_center_on_failure_ = declare_parameter<bool>("return_to_center_on_failure", true);
    search_center_pose_ = declare_parameter<std::string>("search_center_pose", "search_mid_center");
    search_order_ = declare_parameter<std::vector<std::string>>(
      "search_order",
      std::vector<std::string>{
        "search_mid_center",
        "search_mid_left",
        "search_up_left",
        "search_up_center",
        "search_up_right",
        "search_mid_right",
        "search_down_right",
        "search_down_center",
        "search_down_left"});
    local_reacquisition_enabled_ =
      declare_parameter<bool>("local_reacquisition.enabled", true);
    local_pose_suffixes_ = declare_parameter<std::vector<std::string>>(
      "local_reacquisition.pose_suffixes",
      std::vector<std::string>{
        "yaw_p5", "yaw_m5", "yaw_p10", "yaw_m10", "yaw_p15", "yaw_m15",
        "pitch_p5", "pitch_m5", "pitch_p10", "pitch_m10", "pitch_p15", "pitch_m15"});
    (void)declare_parameter<int>("local_reacquisition.step_deg", 5);
    (void)declare_parameter<int>("local_reacquisition.max_offset_deg", 15);

    normalise_detection_parameters();
    load_search_poses();

    marker_subscription_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      aruco_pose_topic_, 10,
      [this](const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        last_marker_received_ = now();
        last_marker_header_stamp_s_ = stamp_to_seconds(*msg);
        marker_sequence_++;
      });

    service_ = create_service<piper_x_aruco_wall_approach::srv::SearchMarker>(
      "/search_marker",
      [this](
        const std::shared_ptr<piper_x_aruco_wall_approach::srv::SearchMarker::Request> request,
        std::shared_ptr<piper_x_aruco_wall_approach::srv::SearchMarker::Response> response) {
        handle_search(request, response);
      });

    RCLCPP_INFO(
      get_logger(),
      "Search marker service ready: marker_id=%d, poses=%zu, settle_time_s=%.2f, detection=%d/%d",
      marker_id_, search_order_.size(), settle_time_s_, required_detections_, detection_window_frames_);
  }

  void initialise_moveit(const rclcpp::Node::SharedPtr & node)
  {
    move_group_ = std::make_unique<moveit::planning_interface::MoveGroupInterface>(
      node,
      planning_group_);
    move_group_->setMaxVelocityScalingFactor(velocity_scaling_);
    move_group_->setMaxAccelerationScalingFactor(acceleration_scaling_);
    move_group_->setPlanningTime(planning_time_);
    move_group_->setNumPlanningAttempts(planning_attempts_);
    RCLCPP_INFO(get_logger(), "MoveIt ready for marker search: group=%s", planning_group_.c_str());
  }

private:
  static std::optional<double> stamp_to_seconds(const geometry_msgs::msg::PoseStamped & msg)
  {
    const auto & stamp = msg.header.stamp;
    if (stamp.sec == 0 && stamp.nanosec == 0) {
      return std::nullopt;
    }
    return static_cast<double>(stamp.sec) + static_cast<double>(stamp.nanosec) * 1e-9;
  }

  void normalise_detection_parameters()
  {
    if (!std::isfinite(marker_timeout_s_) || marker_timeout_s_ <= 0.0) {
      marker_timeout_s_ = 1.0;
    }
    if (!std::isfinite(settle_time_s_) || settle_time_s_ < 0.0) {
      settle_time_s_ = 0.5;
    }
    detection_window_frames_ = std::max(1, detection_window_frames_);
    required_detections_ = std::clamp(required_detections_, 1, detection_window_frames_);
  }

  void load_search_poses()
  {
    std::vector<std::string> pose_names = search_order_;
    for (const auto & base_name : search_order_) {
      for (const auto & suffix : local_pose_suffixes_) {
        pose_names.push_back(base_name + "_" + suffix);
      }
    }
    std::sort(pose_names.begin(), pose_names.end());
    pose_names.erase(std::unique(pose_names.begin(), pose_names.end()), pose_names.end());

    for (const auto & name : pose_names) {
      SearchPose pose;
      pose.name = name;
      pose.calibrated = declare_parameter<bool>("poses." + name + ".calibrated", false);
      pose.camera_yaw_deg = declare_parameter<double>("poses." + name + ".camera_yaw_deg", 0.0);
      pose.camera_pitch_deg = declare_parameter<double>("poses." + name + ".camera_pitch_deg", 0.0);
      pose.joints = declare_parameter<std::vector<double>>("poses." + name + ".joints", std::vector<double>{});
      poses_[name] = pose;
    }
  }

  bool marker_fresh_locked(const rclcpp::Time & current_time) const
  {
    if (!last_marker_received_) {
      return false;
    }
    const double monotonic_age_s = (current_time - *last_marker_received_).seconds();
    if (monotonic_age_s > marker_timeout_s_) {
      return false;
    }
    if (!last_marker_header_stamp_s_) {
      return true;
    }
    const double wall_age_s = rclcpp::Clock(RCL_SYSTEM_TIME).now().seconds() - *last_marker_header_stamp_s_;
    return wall_age_s <= marker_timeout_s_;
  }

  bool marker_fresh() const
  {
    std::lock_guard<std::mutex> lock(data_mutex_);
    return marker_fresh_locked(now());
  }

  bool confirm_marker(std::string & message)
  {
    int detections = 0;
    uint64_t seen_sequence = 0;
    {
      std::lock_guard<std::mutex> lock(data_mutex_);
      seen_sequence = marker_sequence_;
    }

    for (int frame = 0; frame < detection_window_frames_; ++frame) {
      const auto deadline = now() + rclcpp::Duration::from_seconds(marker_timeout_s_);
      bool got_new_marker = false;
      while (rclcpp::ok() && now() < deadline) {
        {
          std::lock_guard<std::mutex> lock(data_mutex_);
          if (marker_sequence_ != seen_sequence && marker_fresh_locked(now())) {
            seen_sequence = marker_sequence_;
            got_new_marker = true;
            break;
          }
        }
        rclcpp::sleep_for(50ms);
      }
      if (got_new_marker) {
        detections++;
      }
    }

    message = "marker detections " + std::to_string(detections) + "/" +
      std::to_string(detection_window_frames_);
    return detections >= required_detections_;
  }

  bool move_to_pose(
    const SearchPose & pose,
    const bool execute,
    std::string & stage,
    std::string & message)
  {
    if (!pose.calibrated || !valid_joint_target(pose.joints)) {
      stage = "search_pose_config";
      message = "search pose '" + pose.name +
        "' is not calibrated; capture six joint values in piper_x_search_poses.yaml";
      return false;
    }
    if (!execute) {
      stage = "plan_only";
      message = "search pose '" + pose.name + "' is calibrated; execute=false so no motion was commanded";
      return true;
    }
    if (!move_group_) {
      stage = "moveit_unavailable";
      message = "MoveIt interface is not ready";
      return false;
    }

    move_group_->setStartStateToCurrentState();
    move_group_->setJointValueTarget(pose.joints);
    moveit::planning_interface::MoveGroupInterface::Plan plan;
    const auto plan_result = move_group_->plan(plan);
    if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
      stage = "search_plan";
      message = "MoveIt planning failed for search pose '" + pose.name + "'";
      return false;
    }
    const auto execute_result = move_group_->execute(plan);
    if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
      stage = "search_execution";
      message = "MoveIt execution failed for search pose '" + pose.name + "'";
      return false;
    }
    stage = "search_motion_complete";
    message = "reached search pose '" + pose.name + "'";
    return true;
  }

  bool try_local_reacquisition(
    const std::string & base_pose_name,
    const bool execute,
    int & poses_checked,
    std::string & found_at_pose,
    std::string & stage,
    std::string & message)
  {
    if (!local_reacquisition_enabled_) {
      return false;
    }
    for (const auto & suffix : local_pose_suffixes_) {
      const auto pose_name = base_pose_name + "_" + suffix;
      const auto pose_iter = poses_.find(pose_name);
      if (pose_iter == poses_.end() || !pose_iter->second.calibrated) {
        continue;
      }
      if (!move_to_pose(pose_iter->second, execute, stage, message)) {
        return false;
      }
      poses_checked++;
      rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(settle_time_s_)));
      std::string confirmation_message;
      if (confirm_marker(confirmation_message)) {
        found_at_pose = pose_name;
        stage = "complete";
        message = "marker acquired at local search pose '" + pose_name + "'";
        return true;
      }
    }
    return false;
  }

  void return_to_center_if_configured()
  {
    if (!return_to_center_on_failure_) {
      return;
    }
    const auto center_iter = poses_.find(search_center_pose_);
    if (center_iter == poses_.end() || !center_iter->second.calibrated) {
      return;
    }
    std::string stage;
    std::string message;
    (void)move_to_pose(center_iter->second, true, stage, message);
  }

  void handle_search(
    const std::shared_ptr<piper_x_aruco_wall_approach::srv::SearchMarker::Request> request,
    std::shared_ptr<piper_x_aruco_wall_approach::srv::SearchMarker::Response> response)
  {
    std::lock_guard<std::mutex> operation_lock(operation_mutex_);
    response->marker_id = marker_id_;
    response->marker_found = false;
    response->success = false;
    response->found_at_pose = "";
    response->poses_checked = 0;

    std::string confirmation_message;
    if (marker_fresh() && confirm_marker(confirmation_message)) {
      response->success = true;
      response->marker_found = true;
      response->found_at_pose = "current_view";
      response->stage = "complete";
      response->message = "marker already visible in current camera view";
      return;
    }

    if (!request->execute) {
      response->stage = "marker_not_found";
      response->message = "marker is not visible in current view and execute=false prevents search motion";
      return;
    }

    for (const auto & pose_name : search_order_) {
      const auto pose_iter = poses_.find(pose_name);
      if (pose_iter == poses_.end()) {
        response->stage = "search_pose_config";
        response->message = "search pose '" + pose_name + "' is missing from piper_x_search_poses.yaml";
        return;
      }

      if (!move_to_pose(pose_iter->second, request->execute, response->stage, response->message)) {
        return;
      }
      response->poses_checked++;
      rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(settle_time_s_)));

      if (confirm_marker(confirmation_message)) {
        response->success = true;
        response->marker_found = true;
        response->found_at_pose = pose_name;
        response->stage = "complete";
        response->message = "marker acquired at search pose '" + pose_name + "'";
        return;
      }

      if (confirmation_message != "marker detections 0/" + std::to_string(detection_window_frames_)) {
        std::string found_at_pose;
        if (try_local_reacquisition(
            pose_name, request->execute, response->poses_checked, found_at_pose,
            response->stage, response->message))
        {
          response->success = true;
          response->marker_found = true;
          response->found_at_pose = found_at_pose;
          return;
        }
        if (response->stage != "complete" && response->stage != "search_motion_complete") {
          return;
        }
      }
    }

    return_to_center_if_configured();
    response->stage = "search_complete";
    response->message = "marker_not_found";
  }

  std::string aruco_pose_topic_;
  std::string planning_group_;
  int marker_id_{};
  double marker_timeout_s_{};
  double settle_time_s_{};
  int detection_window_frames_{};
  int required_detections_{};
  double velocity_scaling_{};
  double acceleration_scaling_{};
  double planning_time_{};
  int planning_attempts_{};
  bool return_to_center_on_failure_{};
  std::string search_center_pose_;
  std::vector<std::string> search_order_;
  bool local_reacquisition_enabled_{};
  std::vector<std::string> local_pose_suffixes_;

  std::unordered_map<std::string, SearchPose> poses_;
  std::unique_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr marker_subscription_;
  rclcpp::Service<piper_x_aruco_wall_approach::srv::SearchMarker>::SharedPtr service_;

  mutable std::mutex data_mutex_;
  std::mutex operation_mutex_;
  std::optional<rclcpp::Time> last_marker_received_;
  std::optional<double> last_marker_header_stamp_s_;
  uint64_t marker_sequence_{0};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<SearchMarkerNode>();
  node->initialise_moveit(node);
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
