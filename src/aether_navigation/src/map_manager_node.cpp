#include "aether_navigation/map_manager.hpp"

#include <rclcpp/rclcpp.hpp>

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<aether_navigation::MapManager>());
  rclcpp::shutdown();
  return 0;
}
