/* author: cafesuada */

#ifndef AETHER_NAVIGATION__MODE_MANAGER_HPP_
#define AETHER_NAVIGATION__MODE_MANAGER_HPP_

#include <aether_interfaces/msg/robot_mode.hpp>
#include <lifecycle_msgs/srv/change_state.hpp>
#include <memory>
#include <mutex>
#include <rclcpp/client.hpp>
#include <rclcpp/publisher.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/service.hpp>
#include <rclcpp_action/rclcpp_action.hpp>

#include "aether_interfaces/action/change_robot_mode.hpp"

namespace aether_navigation {
enum RobotMode {
  NO_MODE,
  MAPPING_MODE,
  LOCALIZATION_MODE,
  NUM_MODES,
};

using namespace std::chrono_literals;

class ModeManager : public rclcpp::Node {
 public:
  using ChangeRobotMode = aether_interfaces::action::ChangeRobotMode;
  using GoalHandleChangeRobotMode =
      rclcpp_action::ServerGoalHandle<ChangeRobotMode>;

  explicit ModeManager(rclcpp::NodeOptions);
  ~ModeManager();

 private:
  void declare_parameters();

  // std::thread change_robot_mode_execution_thread_{};

  aether_interfaces::msg::RobotMode current_mode_{};

  std::mutex current_mode_mutex_ {};
  void update_mode(RobotMode mode);

  template <typename T>
  typename rclcpp::Client<T>::SharedPtr create_srv_client(
      const std::string& srv_name);

  rclcpp::Publisher<aether_interfaces::msg::RobotMode>::SharedPtr
      mode_update_topic_;

  void change_state_(
      const std::shared_ptr<GoalHandleChangeRobotMode> goal_handle);
  void send_robot_change_mode_action_result_(
      const std::shared_ptr<GoalHandleChangeRobotMode> goal_handle,
      const ChangeRobotMode::Result::SharedPtr result);

  rclcpp_action::Server<ChangeRobotMode>::SharedPtr change_mode_server_;

  bool activate_mapping_();
  bool deactivate_mapping_();
  rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr
      mapping_srv_client_;

  bool activate_localization_();
  bool deactivate_localization_();
  rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr
      localization_srv_client_;
  rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr
      map_server_srv_client_;

  bool handling_request_ {false};
  inline bool call_lifecycle_transition_(
      rclcpp::Client<lifecycle_msgs::srv::ChangeState>::SharedPtr client,
      const uint8_t transition_id, const std::string& client_name,
      const std::chrono::seconds timeout = 4s);
};
};  // namespace aether_navigation

#endif
