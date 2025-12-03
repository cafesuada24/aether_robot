/* author: cafesuada */

#ifndef AETHER_NAVIGATION__MODE_MANAGER_HPP_
#define AETHER_NAVIGATION__MODE_MANAGER_HPP_

#include <aether_interfaces/msg/robot_mode.hpp>
#include <lifecycle_msgs/srv/change_state.hpp>
#include <rclcpp/client.hpp>
#include <rclcpp/publisher.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/service.hpp>

#include "aether_interfaces/srv/change_robot_mode.hpp"

namespace aether_navigation {
enum RobotMode {
  NO_MODE,
  MAPPING_MODE,
  LOCALIZATION_MODE,
  NUM_MODES,
};
class ModeManager : public rclcpp::Node {
 public:
  explicit ModeManager(rclcpp::NodeOptions);

 private:
  void declare_parameters();

  aether_interfaces::msg::RobotMode current_mode_ {};
  void update_mode(RobotMode mode);

  void change_mode_srv_callback_(
      const aether_interfaces::srv::ChangeRobotMode::Request::SharedPtr request,
      const aether_interfaces::srv::ChangeRobotMode::Response::SharedPtr
          response);

  template <typename T>
  typename rclcpp::Client<T>::SharedPtr create_srv_client(
      const std::string& srv_name);

  rclcpp::Service<aether_interfaces::srv::ChangeRobotMode>::SharedPtr
      change_mode_srv_;
  rclcpp::Publisher<aether_interfaces::msg::RobotMode>::SharedPtr
      mode_publisher_;
  rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr
      mapping_srv_client_;
  void activate_mapping();
  void mapping_srv_deactivate_request_callback_(const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture future);
  void mapping_srv_activate_request_callback_(const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture future);
  rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr
      localization_srv_client_;
  void activate_localization();
  void localization_srv_deactivate_request_callback_(const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture future);
  void localization_srv_activate_request_callback_(const rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedFuture future);
};
};  // namespace aether_navigation

#endif
