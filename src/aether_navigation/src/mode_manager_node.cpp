/* Author: cafesuada */

#include <exception>
#include <memory>
#include <rclcpp/rclcpp.hpp>

#include "aether_navigation/mode_manager.hpp"

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  rclcpp::NodeOptions options{};
  auto node{std::make_shared<aether_navigation::ModeManager>(options)};
  try {
    rclcpp::spin(node);
  } catch (const std::exception& ex) {
    RCLCPP_ERROR(rclcpp::get_logger("mode_manager"), "%s", ex.what());
  }
  rclcpp::shutdown();
  return 0;
}
