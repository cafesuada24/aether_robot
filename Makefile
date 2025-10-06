SHELL := /usr/bin/zsh
ROS_DISTRO := jazzy
# BASE_CLANG := --build-base build_clang --install-base install_clang
PYTHON3_EXECUTABLE := $(shell which python3)
BUILD_ARGS := --symlink-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

SIM_PKG := aether_gazebo

PACKAGES_TO_BUILD := ${SIM_PKG} aether_navigation object_tracker aether_bringup aether_agent aether_interfaces aether_driver aether_webserver



.PHONY: build build_clean launch_rsp launch_sim run_rviz
# run_bumpgo run_gz run_bridge build_bumpgo set_mode_auto set_mode_hard_control

build:
	echo "Building using python3: $(which python3)" && \
	colcon build $(BUILD_ARGS) --packages-select $(PACKAGES_TO_BUILD)
	# [[ -f "./build/compile_commands.json" ]] &&\
	# ([[-f "./compile_commands.json" ]] && rm ./compile_commands.json ||\
	# [[ !-f "./compile_commands.json" ]]) &&\
	# ln -s ./build/compile_commands.json compile_commands.json &&\
	# echo "compile_commands.json linked"
	
build_clean:
	rm -rf build/ install/ log/ && \
	colcon build $(BUILD_ARGS) --packages-select $(PACKAGES_TO_BUILD)

launch_rsp:
	ros2 launch $(SIM_PKG) rsp.launch.py use_sim_time:=true

launch_sim:
	ros2 launch $(SIM_PKG) launch_sim.launch.py

run_rviz:
	ros2 run rviz2 rviz2 -d src/$(SIM_PKG)/rviz/view_bot.rviz --ros-args -p use_sim_time:=true

build_docker_container: Dockerfile
	docker build --platform='linux/arm64/v8' -t aether-bot-armv8 .

run_docker_container:
	docker run -it --rm --name aether_bot_cont \
		--network=host \
		--gpus all \
		aether-bot:latest \
		# --device=/dev/ttyUSB0 \
		# -v ~/ros_workspaces/articulated_bot:/ros2_ws
shell_attach_docker:
	docker exec -it aether_bot_cont bash
#
# build_bumpgo:
# 	colcon build $(BUILD_ARGS) \
# 		--packages-select fsm_bumpgo_cpp
#
# set_mode_auto:
# 	ros2 param set /bump_go control_mode 1
#
# set_mode_hard_control:
# 	ros2 param set /bump_go control_mode 2
#
# run_gz:
# 	# gz sim building_robot.sdf
# 	ros2 launch sim_demo world.launch.py
#
# run_rviz:
# 	# rviz2 -d urdf.rviz
# 	ros2 launch urdf_tutorial display.launch.py model:=$$(pwd)/model.v2.urdf.xacro.xml
#
# run_bumpgo:
# 	ros2 run fsm_bumpgo_cpp bumpgo --ros-args -r \
# 		input_scan:=/lidar -r output_vel:=/cmd_vel \
# 		-p use_sim_time:=true --log-level info
#
# run_vff_avoidance:
# 	ros2 run vff_avoidance avoidance_vff --ros-args \
# 		-r output_vel:=/cmd_vel -r input_scan:=/sonar_1 \
# 		-p use_sim_time:=true \
# 		--log-level info
#
# run_bridge:
# 	ros2 launch ros_gz_bridge ros_gz_bridge.launch.py bridge_name:=ros_gz_bridge \
# 		config_file:=bridge.yaml
#
#
open_teleop:
	ros2 run teleop_twist_keyboard teleop_twist_keyboard\
		--ros-args -r /cmd_vel:=/key_cmd_vel\
		-p stamped:=true
