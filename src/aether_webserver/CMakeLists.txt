cmake_minimum_required(VERSION 3.8)
project(aether_webserver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(PkgConfig REQUIRED)
find_package(rosbridge_suite REQUIRED)
# find_package(foxglove_bridge REQUIRED)
find_package(web_video_server REQUIRED)
# find_package(rosbridge_suite REQUIRED)
pkg_check_modules(AVAHI_CLIENT REQUIRED avahi-client)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

add_executable(service_advertiser src/service_advertiser.cpp)
target_link_libraries(service_advertiser
    ${AVAHI_CLIENT_LIBRARIES}
)
ament_target_dependencies(service_advertiser
    "rclcpp"
)


install(TARGETS
    service_advertiser
    DESTINATION lib/${PROJECT_NAME}
)

install(
    DIRECTORY launch
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
