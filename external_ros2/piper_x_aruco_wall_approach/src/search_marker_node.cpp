#include <algorithm>
#include <chrono>
#include <cctype>
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
#include <sensor_msgs/msg/joint_state.hpp>

#include "piper_x_aruco_wall_approach/srv/search_marker.hpp"

using namespace std::chrono_literals;

namespace
{
constexpr std::size_t kJointCount = 6;

std::vector<double> degrees_to_radians(const std::vector<double> & degrees)
{
  std::vector<double> radians;
  radians.reserve(degrees.size());
  for (const auto value : degrees) {
    radians.push_back(value * M_PI / 180.0);
  }
  return radians;
}

bool valid_delta(const std::vector<double> & values)
{
  return values.size() == kJointCount && std::all_of(values.begin(), values.end(), [](const double value) {
    return std::isfinite(value);
  });
}

std::string normalise_direction(std::string direction)
{
  std::transform(direction.begin(), direction.end(), direction.begin(), [](const unsigned char ch) {
    return static_cast<char>(std::tolower(ch));
  });
  direction.erase(std::remove_if(direction.begin(), direction.end(), [](const char ch) {
    return ch == ' ' || ch == '_' || ch == '-';
  }), direction.end());
  if (direction.empty() || direction == "auto" || direction == "reactive") {
    return "auto";
  }
  if (direction == "current" || direction == "check" || direction == "none") {
    return "current";
  }
  if (direction == "left") {
    return "left";
  }
  if (direction == "right") {
    return "right";
  }
  if (direction == "up") {
    return "up";
  }
  if (direction == "down") {
    return "down";
  }
  if (direction == "upleft") {
    return "up_left";
  }
  if (direction == "upright") {
    return "up_right";
  }
  if (direction == "downleft") {
    return "down_left";
  }
  if (direction == "downright") {
    return "down_right";
  }
  if (direction == "center" || direction == "centre") {
    return "center";
  }
  return direction;
}
}  // namespace

class SearchMarkerNode : public rclcpp::Node
{
public:
  SearchMarkerNode()
  : Node("search_marker_node")
  {
    aruco_pose_topic_ = declare_parameter<std::string>("aruco_pose_topic", "/aruco_single/pose");
    joint_state_topic_ = declare_parameter<std::string>("joint_state_topic", "joint_states");
    planning_group_ = declare_parameter<std::string>("planning_group", "arm");
    marker_id_ = declare_parameter<int>("marker_id", 6);
    marker_timeout_s_ = declare_parameter<double>("marker_timeout_s", 1.0);
    joint_state_timeout_s_ = declare_parameter<double>("joint_state_timeout_s", 1.0);
    settle_time_s_ = declare_parameter<double>("settle_time_s", 0.5);
    detection_window_frames_ = declare_parameter<int>("detection_window_frames", 5);
    required_detections_ = declare_parameter<int>("required_detections", 3);
    max_steps_ = declare_parameter<int>("max_steps", 100);
    velocity_scaling_ = declare_parameter<double>("velocity_scaling", 0.10);
    acceleration_scaling_ = declare_parameter<double>("acceleration_scaling", 0.10);
    planning_time_ = declare_parameter<double>("planning_time", 10.0);
    planning_attempts_ = declare_parameter<int>("planning_attempts", 10);
    max_single_joint_step_deg_ = declare_parameter<double>("max_single_joint_step_deg", 8.0);
    center_step_scale_ = declare_parameter<double>("center_step_scale", 1.0);
    auto_sequence_ = declare_parameter<std::vector<std::string>>(
      "auto_sequence",
      std::vector<std::string>{
        "up", "left", "right", "right", "left",
        "up", "right", "left", "left", "right"});

    load_direction_deltas();
    normalise_parameters();

    marker_subscription_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      aruco_pose_topic_, 10,
      [this](const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        last_marker_received_ = now();
        last_marker_header_stamp_s_ = stamp_to_seconds(*msg);
        marker_sequence_++;
      });

    joint_state_subscription_ = create_subscription<sensor_msgs::msg::JointState>(
      joint_state_topic_, rclcpp::SensorDataQoS(),
      [this](const sensor_msgs::msg::JointState::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        last_joint_received_ = now();
        last_joint_state_ = *msg;
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
      "Reactive search service ready: marker_id=%d, max_steps=%d, settle_time_s=%.2f, detection=%d/%d",
      marker_id_, max_steps_, settle_time_s_, required_detections_, detection_window_frames_);
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
    RCLCPP_INFO(get_logger(), "MoveIt ready for reactive marker search: group=%s", planning_group_.c_str());
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

  void load_direction_deltas()
  {
    direction_deltas_["left"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.left", std::vector<double>{5.0, 0.0, 0.0, 0.0, 0.0, 0.0}));
    direction_deltas_["right"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.right", std::vector<double>{-5.0, 0.0, 0.0, 0.0, 0.0, 0.0}));
    direction_deltas_["up"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.up", std::vector<double>{0.0, 0.0, 0.0, 5.0, 0.0, 0.0}));
    direction_deltas_["down"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.down", std::vector<double>{0.0, 0.0, 0.0, -5.0, 0.0, 0.0}));
    direction_deltas_["up_left"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.up_left", std::vector<double>{5.0, 0.0, 0.0, 5.0, 0.0, 0.0}));
    direction_deltas_["up_right"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.up_right", std::vector<double>{-5.0, 0.0, 0.0, 5.0, 0.0, 0.0}));
    direction_deltas_["down_left"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.down_left", std::vector<double>{5.0, 0.0, 0.0, -5.0, 0.0, 0.0}));
    direction_deltas_["down_right"] = degrees_to_radians(declare_parameter<std::vector<double>>(
      "direction_deltas_deg.down_right", std::vector<double>{-5.0, 0.0, 0.0, -5.0, 0.0, 0.0}));
  }

  void normalise_parameters()
  {
    if (!std::isfinite(marker_timeout_s_) || marker_timeout_s_ <= 0.0) {
      marker_timeout_s_ = 1.0;
    }
    if (!std::isfinite(joint_state_timeout_s_) || joint_state_timeout_s_ <= 0.0) {
      joint_state_timeout_s_ = 1.0;
    }
    if (!std::isfinite(settle_time_s_) || settle_time_s_ < 0.0) {
      settle_time_s_ = 0.5;
    }
    detection_window_frames_ = std::max(1, detection_window_frames_);
    required_detections_ = std::clamp(required_detections_, 1, detection_window_frames_);
    max_steps_ = std::max(1, max_steps_);
    if (!std::isfinite(max_single_joint_step_deg_) || max_single_joint_step_deg_ <= 0.0) {
      max_single_joint_step_deg_ = 8.0;
    }
    max_single_joint_step_rad_ = max_single_joint_step_deg_ * M_PI / 180.0;
    if (!std::isfinite(center_step_scale_) || center_step_scale_ <= 0.0) {
      center_step_scale_ = 1.0;
    }

    for (auto & [direction, delta] : direction_deltas_) {
      if (!valid_delta(delta)) {
        RCLCPP_WARN(get_logger(), "Invalid delta for direction '%s'; disabling it", direction.c_str());
        delta.assign(kJointCount, 0.0);
        continue;
      }
      for (auto & value : delta) {
        value = std::clamp(value, -max_single_joint_step_rad_, max_single_joint_step_rad_);
      }
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

  std::optional<std::vector<double>> current_joint_values(std::string & message)
  {
    if (!move_group_) {
      message = "MoveIt interface is not ready";
      return std::nullopt;
    }
    const auto joint_names = move_group_->getJointNames();
    if (joint_names.size() != kJointCount) {
      message = "MoveIt returned " + std::to_string(joint_names.size()) +
        " joint names, expected " + std::to_string(kJointCount);
      return std::nullopt;
    }

    sensor_msgs::msg::JointState joint_state;
    {
      std::lock_guard<std::mutex> lock(data_mutex_);
      if (!last_joint_received_) {
        message = "No joint state received on " + joint_state_topic_;
        return std::nullopt;
      }
      const double age_s = (now() - *last_joint_received_).seconds();
      if (age_s > joint_state_timeout_s_) {
        message = "Joint state on " + joint_state_topic_ + " is stale";
        return std::nullopt;
      }
      joint_state = *last_joint_state_;
    }

    if (joint_state.name.empty() || joint_state.position.size() < joint_state.name.size()) {
      message = "Joint state on " + joint_state_topic_ + " has invalid name/position fields";
      return std::nullopt;
    }

    std::vector<double> values;
    values.reserve(joint_names.size());
    for (const auto & joint_name : joint_names) {
      auto iter = std::find(joint_state.name.begin(), joint_state.name.end(), joint_name);
      if (iter == joint_state.name.end()) {
        message = "Joint state on " + joint_state_topic_ + " does not contain " + joint_name;
        return std::nullopt;
      }
      const auto index = static_cast<std::size_t>(std::distance(joint_state.name.begin(), iter));
      values.push_back(joint_state.position[index]);
    }

    if (!valid_delta(values)) {
      message = "Joint state on " + joint_state_topic_ + " contains invalid joint values";
      return std::nullopt;
    }
    return values;
  }

  bool execute_joint_delta(
    const std::vector<double> & delta,
    const bool execute,
    const std::string & direction,
    std::string & stage,
    std::string & message)
  {
    if (!valid_delta(delta)) {
      stage = "search_step_config";
      message = "invalid search delta for direction '" + direction + "'";
      return false;
    }
    if (!move_group_) {
      stage = "moveit_unavailable";
      message = "MoveIt interface is not ready";
      return false;
    }
    std::string joint_message;
    auto current = current_joint_values(joint_message);
    if (!current) {
      stage = "moveit_state";
      message = joint_message;
      return false;
    }
    std::vector<double> target = *current;
    for (std::size_t i = 0; i < kJointCount; ++i) {
      target[i] += delta[i];
    }

    move_group_->setStartStateToCurrentState();
    move_group_->setJointValueTarget(target);
    moveit::planning_interface::MoveGroupInterface::Plan plan;
    const auto plan_result = move_group_->plan(plan);
    if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
      stage = "search_plan";
      message = "MoveIt planning failed for reactive search direction '" + direction + "'";
      return false;
    }
    if (!execute) {
      stage = "plan_only";
      message = "reactive search direction '" + direction + "' planned; execute=false so no motion was commanded";
      return true;
    }
    const auto execute_result = move_group_->execute(plan);
    if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
      stage = "search_execution";
      message = "MoveIt execution failed for reactive search direction '" + direction + "'";
      return false;
    }
    for (std::size_t i = 0; i < kJointCount; ++i) {
      cumulative_offset_[i] += delta[i];
    }
    stage = "search_motion_complete";
    message = "completed reactive search direction '" + direction + "'";
    return true;
  }

  std::vector<double> center_delta(std::string & message) const
  {
    (void)message;
    std::vector<double> delta(kJointCount, 0.0);
    for (std::size_t i = 0; i < kJointCount; ++i) {
      delta[i] = std::clamp(
        -cumulative_offset_[i] * center_step_scale_,
        -max_single_joint_step_rad_,
        max_single_joint_step_rad_);
    }
    return delta;
  }

  bool perform_step(
    const std::string & requested_direction,
    const bool execute,
    int & steps_used,
    std::string & found_at_pose,
    std::string & stage,
    std::string & message)
  {
    const auto direction = normalise_direction(requested_direction);
    if (direction == "current") {
      stage = "current_view";
      message = "checked current camera view without motion";
    } else {
      std::vector<double> delta;
      if (direction == "center") {
        delta = center_delta(message);
      } else {
        const auto iter = direction_deltas_.find(direction);
        if (iter == direction_deltas_.end()) {
          stage = "search_direction";
          message = "unsupported reactive search direction '" + requested_direction + "'";
          return false;
        }
        delta = iter->second;
      }
      if (!execute_joint_delta(delta, execute, direction, stage, message)) {
        return false;
      }
      steps_used++;
      rclcpp::sleep_for(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::duration<double>(settle_time_s_)));
    }

    std::string confirmation_message;
    if (marker_fresh() && confirm_marker(confirmation_message)) {
      found_at_pose = direction == "current" ? "current_view" : "reactive_" + direction;
      stage = "complete";
      message = direction == "current" ?
        "marker already visible in current camera view" :
        "marker acquired after reactive search direction '" + direction + "'";
      return true;
    }
    return false;
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

    std::string found_at_pose;
    std::string stage;
    std::string message;
    int steps_used = 0;

    if (perform_step("current", false, steps_used, found_at_pose, stage, message)) {
      response->success = true;
      response->marker_found = true;
      response->found_at_pose = found_at_pose;
      response->stage = stage;
      response->message = message;
      response->poses_checked = steps_used;
      return;
    }

    const auto direction = normalise_direction(request->direction);
    const int requested_max_steps = request->max_steps > 0 ? request->max_steps : max_steps_;
    const int step_limit = std::clamp(requested_max_steps, 1, max_steps_);

    if (!request->execute) {
      response->stage = "marker_not_found";
      response->message = "marker is not visible in current view and execute=false prevents reactive search motion";
      response->poses_checked = 0;
      return;
    }

    if (direction != "auto") {
      const bool found = perform_step(
        direction, true, steps_used, found_at_pose, response->stage, response->message);
      response->poses_checked = steps_used;
      if (found) {
        response->success = true;
        response->marker_found = true;
        response->found_at_pose = found_at_pose;
        return;
      }
      if (response->stage == "search_motion_complete" || response->stage == "current_view" || response->stage == "plan_only") {
        response->success = true;
        response->stage = "step_complete";
        response->message = "reactive search step completed; marker_not_found";
      }
      return;
    }

    for (int step = 0; step < step_limit; ++step) {
      const auto & next_direction = auto_sequence_.empty() ? std::string("left") : auto_sequence_[step % auto_sequence_.size()];
      const bool found = perform_step(
        next_direction, true, steps_used, found_at_pose, response->stage, response->message);
      response->poses_checked = steps_used;
      if (found) {
        response->success = true;
        response->marker_found = true;
        response->found_at_pose = found_at_pose;
        return;
      }
      if (response->stage != "search_motion_complete") {
        return;
      }
    }

    response->stage = "search_complete";
    response->message = "marker_not_found after " + std::to_string(steps_used) + " reactive search steps";
    response->poses_checked = steps_used;
  }

  std::string aruco_pose_topic_;
  std::string joint_state_topic_;
  std::string planning_group_;
  int marker_id_{};
  double marker_timeout_s_{};
  double joint_state_timeout_s_{};
  double settle_time_s_{};
  int detection_window_frames_{};
  int required_detections_{};
  int max_steps_{};
  double velocity_scaling_{};
  double acceleration_scaling_{};
  double planning_time_{};
  int planning_attempts_{};
  double max_single_joint_step_deg_{};
  double max_single_joint_step_rad_{};
  double center_step_scale_{};
  std::vector<std::string> auto_sequence_;
  std::unordered_map<std::string, std::vector<double>> direction_deltas_;
  std::vector<double> cumulative_offset_ = std::vector<double>(kJointCount, 0.0);

  std::unique_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr marker_subscription_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_subscription_;
  rclcpp::Service<piper_x_aruco_wall_approach::srv::SearchMarker>::SharedPtr service_;

  mutable std::mutex data_mutex_;
  std::mutex operation_mutex_;
  std::optional<rclcpp::Time> last_marker_received_;
  std::optional<double> last_marker_header_stamp_s_;
  uint64_t marker_sequence_{0};
  std::optional<rclcpp::Time> last_joint_received_;
  std::optional<sensor_msgs::msg::JointState> last_joint_state_;
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
