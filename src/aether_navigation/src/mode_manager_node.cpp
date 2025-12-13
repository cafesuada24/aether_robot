// Copyright (c) 2025 Cafesuada
// All rights reserved.

#include <memory>
#include <rclcpp/executor_options.hpp>
#include <rclcpp/rclcpp.hpp>

#include "aether_navigation/mode_manager.hpp"

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);

  rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),
                                                    2);

  rclcpp::NodeOptions options{};
  auto node{std::make_shared<aether_navigation::ModeManager>(options)};

  executor.add_node(node);

  executor.spin();
  // rclcpp::spin(node);

  rclcpp::shutdown();
  return 0;
}
