cmake_minimum_required(VERSION 3.8)
project(aether_driver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(aether_interfaces REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(sensor_msgs REQUIRED)

add_library(serial_lib SHARED
  src/lib/serial/serial.cc
  src/lib/serial/impl/unix.cc
  src/lib/serial/impl/win.cc
)
target_include_directories(serial_lib PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:include/${PROJECT_NAME}>")

add_library(arduino_lib SHARED
  src/lib/arduino.cc)
target_include_directories(arduino_lib PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:include/${PROJECT_NAME}>")
target_link_libraries(arduino_lib serial_lib)

add_library(diffdrive_arduino SHARED src/diffdrive_arduino.cpp src/wheel.cpp)
target_include_directories(diffdrive_arduino
  PRIVATE
  include
)
ament_target_dependencies(diffdrive_arduino
  rclcpp
  rclcpp_lifecycle
  hardware_interface
  pluginlib
  aether_interfaces
)
pluginlib_export_plugin_description_file(hardware_interface robot_hardware.xml)

add_executable(driver_node src/nodes/driver_node.cpp)
target_link_libraries(driver_node
  serial_lib
  arduino_lib
)
ament_target_dependencies(driver_node
  "rclcpp"
  "aether_interfaces"
)

add_executable(ros_arduino_bridge src/nodes/ros_arduino_bridge.cpp)
target_link_libraries(ros_arduino_bridge
  arduino_lib
)
ament_target_dependencies(ros_arduino_bridge
  "rclcpp"
  "sensor_msgs"
  "aether_interfaces"
)


install(TARGETS
  arduino_lib
  serial_lib
  diffdrive_arduino
  DESTINATION lib
)

install(TARGETS
  driver_node
  ros_arduino_bridge
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

ament_export_libraries(
  diffdrive_arduino
)

ament_package()
