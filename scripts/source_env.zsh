ROS_DISTRO=jazzy

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/${ROS_DISTRO}/lib/

echo "Sourcing ROS $ROS_DISTRO underlay environment..."
source /opt/ros/$ROS_DISTRO/setup.zsh && echo "Done."

echo "Sourcing workspace overlay environment..."
source ./install/setup.zsh && echo "Done."

eval "$(register-python-argcomplete ros2)"
eval "$(register-python-argcomplete colcon)"
