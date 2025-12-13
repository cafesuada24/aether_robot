// Copyright (c) 2025 Cafesuada
// All rights reserved.

#include <rclcpp/executor_options.hpp>
#include <rclcpp/executors/multi_threaded_executor.hpp>
#include <rclcpp/rclcpp.hpp>

#include "aether_navigation/map_manager.hpp"

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  auto node{std::make_shared<aether_navigation::MapManager>()};

  rclcpp::executors::MultiThreadedExecutor executors(rclcpp::ExecutorOptions(),
                                                     2);
  executors.add_node(node);
  executors.spin();
  executors.cancel();
  rclcpp::shutdown();

  return 0;
}
