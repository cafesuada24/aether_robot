cmake_minimum_required(VERSION 3.8)
project(object_tracker)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(image_transport REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)

include_directories(include)

add_library(object_tracker_lib SHARED
  src/object_tracker/object_tracker.cc)
target_include_directories(object_tracker_lib PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>)
ament_target_dependencies(object_tracker_lib
  "rclcpp"
  "OpenCV"
)

add_library(object_follow_component SHARED
  src/object_tracker/object_follow.cc)
# target_include_directories(object_follow_component PRIVATE
#   $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
#   $<INSTALL_INTERFACE:include>)
ament_target_dependencies(object_follow_component
  "rclcpp"
  "rclcpp_components"
  "geometry_msgs"
)
rclcpp_components_register_node(object_follow_component
  PLUGIN "object_tracker::node::ObjectFollow"
  EXECUTABLE object_follow)

add_library(object_detector_component SHARED
  src/object_tracker/object_detector.cc)
target_link_libraries(object_detector_component object_tracker_lib)
# target_include_directories(object_detector_component PRIVATE
#   $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
#   $<INSTALL_INTERFACE:include>)
ament_target_dependencies(object_detector_component
  "rclcpp"
  "rclcpp_components"
  "image_transport"
  "cv_bridge"
  "sensor_msgs"
)
rclcpp_components_register_node(object_detector_component
  PLUGIN "object_tracker::node::ObjectDetector"
  EXECUTABLE object_detector)

install(TARGETS
  object_tracker_lib
  object_follow_component
  object_detector_component
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
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
  DIRECTORY params launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
