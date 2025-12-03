/*author: cafesuada*/

#include "aether_navigation/mode_manager.hpp"

#include <functional>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>

#include "aether_interfaces/msg/robot_mode.hpp"
#include "lifecycle_msgs/msg/transition.hpp"
#include "lifecycle_msgs/srv/change_state.hpp"

namespace aether_navigation {

using namespace std::chrono_literals;

ModeManager::ModeManager(rclcpp::NodeOptions options)
    : rclcpp::Node("mode_manager", options),
      change_mode_srv_{create_service<aether_interfaces::srv::ChangeRobotMode>(
          "/robot_mode/change",
          std::bind(&ModeManager::change_mode_srv_callback_, this,
                    std::placeholders::_1, std::placeholders::_2))} {
  declare_parameters();

  // Init state publisher
  this->mode_publisher_ =
      this->create_publisher<aether_interfaces::msg::RobotMode>(
          this->get_parameter("mode_topic").as_string(),
          rclcpp::QoS(rclcpp::KeepLast(1)));

  update_mode(NO_MODE);

  // Mapping service clients
  this->mapping_srv_client_ =
      this->create_srv_client<lifecycle_msgs::srv::ChangeState>(
          this->get_parameter("mapping_service_name").as_string());

  if (nullptr == this->mapping_srv_client_) {
    return;
  }

  update_mode(MAPPING_MODE);

  // Localization service clients
  this->localization_srv_client_ =
      this->create_srv_client<lifecycle_msgs::srv::ChangeState>(
          this->get_parameter("localization_service_name").as_string());

  if (nullptr == this->localization_srv_client_) {
    return;
  }

  auto configure_request{
      std::make_shared<lifecycle_msgs::srv::ChangeState::Request>()};
  configure_request->transition.id =
      lifecycle_msgs::msg::Transition::TRANSITION_CONFIGURE;
  this->localization_srv_client_->async_send_request(
      configure_request);
}

void ModeManager::declare_parameters() {
  this->declare_parameter("mode_topic", "/robot_mode/status");
  this->declare_parameter("mapping_service_name", "/slam_toolbox/change_state");
  this->declare_parameter("localization_service_name", "/amcl/change_state");
}

template <typename T>
typename rclcpp::Client<T>::SharedPtr ModeManager::create_srv_client(
    const std::string& srv_name) {
  auto client{this->create_client<T>(srv_name)};
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

void ModeManager::change_mode_srv_callback_(
    const aether_interfaces::srv::ChangeRobotMode::Request::SharedPtr request,
    const aether_interfaces::srv::ChangeRobotMode::Response::SharedPtr
        response) {
  const auto mode{static_cast<RobotMode>(request->mode.mode)};

  if (mode == current_mode_.mode) {
    return;
  }

  if (mode < 0 || mode >= NUM_MODES) {
    response->success = false;
    RCLCPP_INFO(this->get_logger(),
                "Failed to change robot mode: invalid mode %ud.", mode);
    return;
  }

  if (mode == MAPPING_MODE) {
    if (current_mode_.mode == LOCALIZATION_MODE) {
      auto deactivate_request{
          std::make_shared<lifecycle_msgs::srv::ChangeState::Request>()};
      deactivate_request->transition.id =
          lifecycle_msgs::msg::Transition::TRANSITION_DEACTIVATE;
      this->localization_srv_client_->async_send_request(
          deactivate_request,
          std::bind(&ModeManager::localization_srv_deactivate_request_callback_,
                    this, std::placeholders::_1));
    } else {
      activate_mapping();
    }

  } else if (mode == LOCALIZATION_MODE) {
    RCLCPP_INFO(this->get_logger(), "called");
    if (current_mode_.mode == MAPPING_MODE) {
      auto deactivate_request{
          std::make_shared<lifecycle_msgs::srv::ChangeState::Request>()};
      deactivate_request->transition.id =
          lifecycle_msgs::msg::Transition::TRANSITION_DEACTIVATE;
      this->mapping_srv_client_->async_send_request(
          deactivate_request,
          std::bind(&ModeManager::mapping_srv_deactivate_request_callback_,
                    this, std::placeholders::_1));
    } else {
      activate_localization();
    }
  }
}

void ModeManager::mapping_srv_deactivate_request_callback_(
    const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture
        future) {
  if (!future.valid()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to call Mapping service");
    return;
  }

  if (!future.get()->success) {
    RCLCPP_ERROR(this->get_logger(), "Failed to deactivate Mapping service");
    return;
  }
  RCLCPP_INFO(this->get_logger(), "Mapping Service deactivated.");
  update_mode(NO_MODE);

  activate_localization();
}
void ModeManager::mapping_srv_activate_request_callback_(
    const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture
        future) {
  if (!future.valid()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to call Mapping service");
    return;
  }

  if (!future.get()->success) {
    RCLCPP_ERROR(this->get_logger(), "Failed to activate Mapping service");
    return;
  }

  RCLCPP_INFO(this->get_logger(), "Mapping Service activated.");
  update_mode(MAPPING_MODE);
}

void ModeManager::activate_mapping() {
  auto active_request{
      std::make_shared<lifecycle_msgs::srv::ChangeState::Request>()};
  active_request->transition.id =
      lifecycle_msgs::msg::Transition::TRANSITION_ACTIVATE;
  this->mapping_srv_client_->async_send_request(
      active_request,
      std::bind(&ModeManager::mapping_srv_activate_request_callback_, this,
                std::placeholders::_1));
}

void ModeManager::localization_srv_deactivate_request_callback_(
    const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture
        future) {
  if (!future.valid()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to call Localization service");
    return;
  }

  if (!future.get()->success) {
    RCLCPP_ERROR(this->get_logger(),
                 "Failed to deactivate Localization service");
    return;
  }
  RCLCPP_INFO(this->get_logger(), "Localization Service deactivated.");
  update_mode(NO_MODE);

  activate_mapping();
}

void ModeManager::localization_srv_activate_request_callback_(
    const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture
        future) {
  if (!future.valid()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to call Localization service");
    return;
  }

  if (!future.get()->success) {
    RCLCPP_ERROR(this->get_logger(), "Failed to activate Localization service");
    return;
  }

  RCLCPP_INFO(this->get_logger(), "Localization Service activated.");
  update_mode(LOCALIZATION_MODE);
}

void ModeManager::activate_localization() {
  auto active_request{
      std::make_shared<lifecycle_msgs::srv::ChangeState::Request>()};
  active_request->transition.id =
      lifecycle_msgs::msg::Transition::TRANSITION_ACTIVATE;
  this->localization_srv_client_->async_send_request(
      active_request,
      std::bind(&ModeManager::localization_srv_activate_request_callback_, this,
                std::placeholders::_1));
}

void ModeManager::update_mode(RobotMode mode) {
  current_mode_.mode = mode;
  mode_publisher_->publish(current_mode_);
}

};  // namespace aether_navigation
