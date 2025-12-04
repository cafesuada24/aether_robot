cmake_minimum_required(VERSION 3.8)
project(aether_navigation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(aether_interfaces REQUIRED)
find_package(lifecycle_msgs REQUIRED)

include_directories(include)

add_library(mode_manager src/mode_manager.cpp)
ament_target_dependencies(mode_manager
  rclcpp
  rclcpp_action
  aether_interfaces
  lifecycle_msgs
)
add_executable(mode_manager_node src/mode_manager_node.cpp)
target_link_libraries(mode_manager_node mode_manager)
ament_target_dependencies(mode_manager_node
  rclcpp
)


add_library(map_manager src/map_manager.cpp)
ament_target_dependencies(map_manager
  rclcpp
  aether_interfaces
)
add_executable(map_manager_node src/map_manager_node.cpp)
target_link_libraries(map_manager_node map_manager)
ament_target_dependencies(map_manager_node
  rclcpp
)

install(TARGETS 
  mode_manager_node
  map_manager_node
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY params launch
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
