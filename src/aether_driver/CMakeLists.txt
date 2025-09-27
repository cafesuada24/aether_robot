cmake_minimum_required(VERSION 3.8)
project(aether_driver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(aether_interfaces)

include_directories(include)

add_library(serial_lib SHARED
  src/lib/serial/serial.cc
  src/lib/serial/impl/unix.cc
  src/lib/serial/impl/win.cc
)
target_include_directories(serial_lib PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)

add_library(arduino_lib SHARED
  src/lib/arduino.cc
)
target_link_libraries(arduino_lib serial_lib)
target_include_directories(arduino_lib PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)

add_executable(driver_node src/nodes/driver_node.cpp)
target_link_libraries(driver_node serial_lib arduino_lib)
ament_target_dependencies(
  driver_node
  "rclcpp"
  "aether_interfaces"
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

install(TARGETS
  driver_node
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

ament_package()
