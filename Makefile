SHELL := /usr/bin/bash
ROS_DISTRO := jazzy
PYTHON3_EXECUTABLE := $(shell which python3)
BUILD_ARGS := --symlink-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

PACKAGES_TO_BUILD := aether_gazebo aether_navigation aether_bringup aether_agent aether_interfaces aether_driver aether_webserver aether_description



.PHONY: build build_clean launch_rsp launch_sim run_rviz

build:
	([ "$(clean)" == 'True' ] && rm -rf build/ install/ log/); \
	colcon build $(BUILD_ARGS) --packages-select $(PACKAGES_TO_BUILD)

launch_sim:
	ros2 launch aether_gazebo launch_sim.py slam:=$(or $(use_sim_time), 'False')

run_rviz:
	ros2 run rviz2 rviz2 -d src/aether_gazebo/rviz/view_bot.rviz --ros-args -p use_sim_time:=$(or $(use_sim_time), 'False')

build_docker_cont: Dockerfile
	docker build --platform='linux/arm64/v8' -t aether-bot-armv8 .

run_docker_cont:
	docker run -it --rm --name aether_bot_cont \
		--network=host \
		--runtime=nvidia \
		-e DISPLAY=:0 \
		-v ~/ros2_ws:/ros2_ws \
		-v "/tmp/.X11-unix:/tmp/.X11-unix:rw" \
		--group-add video \
		--device=/dev/serial/by-id/usb-1a86_USB2.0-Serial-if00-port0:/dev/ttyUSB0 \
		--device=/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0:/dev/ttyUSB1 \
		aether-bot-armv8:latest

		# --device=/dev/ttyUSB0 \
		# -v ~/ros_workspaces/articulated_bot:/ros2_ws
new_docker_shell:
	docker exec -it $(or $cont_name, 'aether_bot_cont') bash

open_teleop:
	ros2 run teleop_twist_keyboard teleop_twist_keyboard\
		--ros-args -r /cmd_vel:=/key_cmd_vel\
		-p stamped:=true -p use_sim_time:=$(or $(use_sim_time), 'False')
