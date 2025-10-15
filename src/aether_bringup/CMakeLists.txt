cmake_minimum_required(VERSION 3.8)
project(aether_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
# find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(twist_mux REQUIRED)
find_package(teleop_twist_joy REQUIRED)
find_package(aether_navigation REQUIRED)
find_package(aether_description REQUIRED)
find_package(aether_driver REQUIRED)
find_package(aether_webserver REQUIRED)
find_package(v4l2_camera REQUIRED)
find_package(rplidar_ros REQUIRED)
find_package(xacro REQUIRED)
find_package(controller_manager REQUIRED)
find_package(robot_state_publisher REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

add_executable(twist_stamper_node src/twist_stamper_node.cpp)
ament_target_dependencies(
  twist_stamper_node 
  "rclcpp"
  "geometry_msgs"
)

ament_python_install_package(${PROJECT_NAME})

install(TARGETS twist_stamper_node
  DESTINATION lib/${PROJECT_NAME}
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

install(
    DIRECTORY params launch map
    DESTINATION share/${PROJECT_NAME}
)
ament_package()
