/*author: cafesuada*/

#include "aether_navigation/mode_manager.hpp"

#include <rmw/types.h>

#include <memory>
#include <rclcpp/executors.hpp>
#include <rclcpp/publisher_options.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/create_server.hpp>

#include "aether_interfaces/action/change_robot_mode.hpp"
#include "aether_interfaces/msg/robot_mode.hpp"
#include "lifecycle_msgs/msg/transition.hpp"
#include "lifecycle_msgs/srv/change_state.hpp"

namespace aether_navigation {

using namespace std::chrono_literals;

ModeManager::ModeManager(rclcpp::NodeOptions options)
    : rclcpp::Node("mode_manager", options),
      client_callback_group_{
          create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive)},
      action_callback_group_{
          create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive)} {
  declare_parameters();

  rclcpp::QoS mode_update_topic_qos(rclcpp::KeepLast(1));
  mode_update_topic_qos.durability(RMW_QOS_POLICY_DURABILITY_TRANSIENT_LOCAL);
  mode_update_topic_qos.reliability(RMW_QOS_POLICY_RELIABILITY_RELIABLE);
  // Robot Mode publisher
  this->mode_update_topic_ =
      this->create_publisher<aether_interfaces::msg::RobotMode>(
          this->get_parameter("update_topic").as_string(),
          mode_update_topic_qos);

  update_mode(NO_MODE);

  // #####################Server##################################

  auto change_mode_goal_cb{[this](const rclcpp_action::GoalUUID& uuid,
                                  ChangeRobotMode::Goal::ConstSharedPtr goal) {
    RCLCPP_INFO(this->get_logger(), "Received change mode request: %u",
                goal->mode.mode);
    if (this->handling_request_) {
      RCLCPP_WARN(this->get_logger(),
                  "Previous request is being executed! Rejecting new mode "
                  "changing request.");
      return rclcpp_action::GoalResponse::REJECT;
    }
    (void)uuid;
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }};
  auto change_mode_cancel_cb{
      [this](const std::shared_ptr<GoalHandleChangeRobotMode> goal_handle) {
        RCLCPP_INFO(this->get_logger(),
                    "Received request to cancel change mode");
        (void)goal_handle;
        return rclcpp_action::CancelResponse::ACCEPT;
      }};
  auto change_mode_accepted_cb{
      [this](const std::shared_ptr<GoalHandleChangeRobotMode> goal_handle) {
        return this->change_state_(goal_handle);
        // auto execute_in_thread{
        //     [this, goal_handle]() { return this->change_state_(goal_handle); }};
        // std::thread{execute_in_thread}.detach();
      }};

  this->change_mode_server_ = rclcpp_action::create_server<ChangeRobotMode>(
      this, "/robot_mode/change", change_mode_goal_cb, change_mode_cancel_cb,
      change_mode_accepted_cb, rcl_action_server_get_default_options(),
      action_callback_group_);

  // #############################################################

  // ###########################Mapping services##################
  this->mapping_srv_client_ =
      this->create_srv_client<lifecycle_msgs::srv::ChangeState>(
          this->get_parameter("mapping_service_name").as_string());
  if (!this->mapping_srv_client_) {
    throw std::runtime_error(
        "FATAL: Failed to initialize Mapping service client.");
  }

  // #############################################################

  // #####################Localization services###################
  this->localization_srv_client_ =
      this->create_srv_client<lifecycle_msgs::srv::ChangeState>(
          this->get_parameter("localization_service_name").as_string());

  if (!this->localization_srv_client_) {
    throw std::runtime_error(
        "FATAL: Failed to initialize Localization service client.");
  }

  this->map_server_srv_client_ =
      this->create_srv_client<lifecycle_msgs::srv::ChangeState>(
          this->get_parameter("map_server_service_name").as_string());

  if (!this->map_server_srv_client_) {
    throw std::runtime_error(
        "FATAL: Failed to initialize Map server service client.");
  }
  // #############################################################

  // Some node need initial configure state
  // call_lifecycle_transition_(
  //     mapping_srv_client_,
  //     lifecycle_msgs::msg::Transition::TRANSITION_CONFIGURE, "Mapping");
  std::thread{[this]() {
    return call_lifecycle_transition_(
        mapping_srv_client_,
        lifecycle_msgs::msg::Transition::TRANSITION_CONFIGURE, "Mapping");
  }}.detach();
}

ModeManager::~ModeManager() {}

void ModeManager::declare_parameters() {
  this->declare_parameter("update_topic", "/robot_mode/status_update");

  this->declare_parameter("mapping_service_name", "/slam_toolbox/change_state");

  this->declare_parameter("localization_service_name", "/amcl/change_state");
  this->declare_parameter("map_server_service_name",
                          "/map_server/change_state");
}

void ModeManager::change_state_(
    const std::shared_ptr<GoalHandleChangeRobotMode> goal_handle) {
  RCLCPP_INFO(this->get_logger(), "Start changing state");

  const auto goal_mode{goal_handle->get_goal()->mode.mode};
  auto feedback{std::make_shared<ChangeRobotMode::Feedback>()};
  auto result{std::make_shared<ChangeRobotMode::Result>()};
  result->success = true;

  if (goal_mode >= NUM_MODES) {
    RCLCPP_INFO(this->get_logger(), "Invalid mode: %u", goal_mode);
    result->success = false;
    return send_robot_change_mode_action_result_(goal_handle, result);
  }

  if (goal_mode == current_mode_.mode) {
    return send_robot_change_mode_action_result_(goal_handle, result);
  }

  if (current_mode_.mode == LOCALIZATION_MODE) {
    feedback->msg = "Deactivating Localization mode";
    goal_handle->publish_feedback(feedback);
    if (!deactivate_localization_()) {
      RCLCPP_INFO(this->get_logger(), "Failed to deactivate localization mode");
      result->success = false;
      return send_robot_change_mode_action_result_(goal_handle, result);
    }
    update_mode(NO_MODE);
    feedback->msg = "Localization mode deactivated";
    goal_handle->publish_feedback(feedback);
  }

  if (current_mode_.mode == MAPPING_MODE) {
    feedback->msg = "Deactivating Mapping mode";
    goal_handle->publish_feedback(feedback);
    if (!deactivate_mapping_()) {
      RCLCPP_INFO(this->get_logger(), "Failed to deactivate mapping mode");
      result->success = false;
      return send_robot_change_mode_action_result_(goal_handle, result);
    }
    update_mode(NO_MODE);
    feedback->msg = "Mapping mode deactivated";
    goal_handle->publish_feedback(feedback);
  }

  if (goal_mode == MAPPING_MODE) {
    feedback->msg = "Activating Mapping mode";
    goal_handle->publish_feedback(feedback);
    if (!activate_mapping_()) {
      RCLCPP_INFO(this->get_logger(), "Failed to activate mapping mode");
      result->success = false;
      return send_robot_change_mode_action_result_(goal_handle, result);
    }
    update_mode(MAPPING_MODE);
  }

  if (goal_mode == LOCALIZATION_MODE) {
    feedback->msg = "Activating Localization mode";
    goal_handle->publish_feedback(feedback);
    if (!activate_localization_()) {
      RCLCPP_INFO(this->get_logger(), "Failed to activate localization mode");
      result->success = false;
      return send_robot_change_mode_action_result_(goal_handle, result);
    }
    update_mode(LOCALIZATION_MODE);
  }

  return send_robot_change_mode_action_result_(goal_handle, result);
}

void ModeManager::send_robot_change_mode_action_result_(
    const std::shared_ptr<GoalHandleChangeRobotMode> goal_handle,
    const ChangeRobotMode::Result::SharedPtr result) {
  handling_request_ = false;
  if (rclcpp::ok()) {
    goal_handle->succeed(result);
    if (result->success) {
      RCLCPP_INFO(this->get_logger(), "Robot state changed to: %u",
                  goal_handle->get_goal()->mode.mode);
    } else {
      RCLCPP_INFO(this->get_logger(), "Failed to change robot state");
    }
  }
}

bool ModeManager::activate_mapping_() {
  return call_lifecycle_transition_(
      mapping_srv_client_, lifecycle_msgs::msg::Transition::TRANSITION_ACTIVATE,
      "Mapping");
}

bool ModeManager::deactivate_mapping_() {
  return call_lifecycle_transition_(
      mapping_srv_client_,
      lifecycle_msgs::msg::Transition::TRANSITION_DEACTIVATE, "Mapping");
}

bool ModeManager::activate_localization_() {
  if (!call_lifecycle_transition_(
          map_server_srv_client_,
          lifecycle_msgs::msg::Transition::TRANSITION_CONFIGURE,
          "Map Server") ||
      !call_lifecycle_transition_(
          localization_srv_client_,
          lifecycle_msgs::msg::Transition::TRANSITION_CONFIGURE,
          "Localization")) {
    return false;
  }

  return call_lifecycle_transition_(
             map_server_srv_client_,
             lifecycle_msgs::msg::Transition::TRANSITION_ACTIVATE,
             "Map Server") &&
         call_lifecycle_transition_(
             localization_srv_client_,
             lifecycle_msgs::msg::Transition::TRANSITION_ACTIVATE,
             "Localization");
}

bool ModeManager::deactivate_localization_() {
  if (!call_lifecycle_transition_(
          localization_srv_client_,
          lifecycle_msgs::msg::Transition::TRANSITION_DEACTIVATE,
          "Localization") ||
      !call_lifecycle_transition_(
          map_server_srv_client_,
          lifecycle_msgs::msg::Transition::TRANSITION_DEACTIVATE,
          "Map Server")) {
    return false;
  }

  return call_lifecycle_transition_(
             localization_srv_client_,
             lifecycle_msgs::msg::Transition::TRANSITION_CLEANUP,
             "Localization") &&
         call_lifecycle_transition_(
             map_server_srv_client_,
             lifecycle_msgs::msg::Transition::TRANSITION_CLEANUP, "Map Server");
}

template <typename T>
typename rclcpp::Client<T>::SharedPtr ModeManager::create_srv_client(
    const std::string& srv_name) {
  auto client{this->create_client<T>(srv_name, rclcpp::ServicesQoS(),
                                     client_callback_group_)};
  while (!client->wait_for_service(1s)) {
    if (!rclcpp::ok()) {
      RCLCPP_ERROR(this->get_logger(),
                   "Interrupted while waiting for service %s. Exiting.",
                   srv_name.c_str());
      return nullptr;
    }
    RCLCPP_INFO(this->get_logger(), "Service not available, waiting again...");
  }
  RCLCPP_INFO(this->get_logger(), "Service available. %s service ready.",
              srv_name.c_str());
  return client;
}

void ModeManager::update_mode(RobotMode mode) {
  std::lock_guard<std::mutex> lock(current_mode_mutex_);
  current_mode_.mode = mode;
  mode_update_topic_->publish(current_mode_);
}

inline bool ModeManager::call_lifecycle_transition_(
    rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr client,
    const uint8_t transition_id, const std::string& client_name,
    const std::chrono::seconds timeout) {
  auto transition_request =
      std::make_shared<lifecycle_msgs::srv::ChangeState::Request>();
  transition_request->transition.id = transition_id;

  auto future{client->async_send_request(transition_request)};

  if (future.wait_for(timeout) != std::future_status::ready) {
    RCLCPP_ERROR(
        this->get_logger(),
        "Failed to call %s service with transition %u: Timeout/Client Error",
        client_name.c_str(), transition_id);
    return false;
  }

  const auto success{future.valid() && future.get()->success};

  if (!success) {
    RCLCPP_ERROR(this->get_logger(), "%s transition %u failed.",
                 client_name.c_str(), transition_id);
  }

  return success;
}

};  // namespace aether_navigation
