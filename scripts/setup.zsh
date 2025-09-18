ROS_DISTRO='jazzy'

export RMW_IMPLEMENTATION='rmw_cyclonedds_cpp'
export GZ_SIM_SYSTEM_PLUGIN_PATH="/opt/ros/${ROS_DISTRO}/lib/"
export GAZEBO_MODEL_PATH="$GAZEBO_MODEL_PATH:/opt/ros/jazzy/share/turtlebot3_gazebo/models"

VENV_DIR=./venv

new_env=0
if ! [[ -d "$VENV_DIR" ]]; then
    echo 'virtual env not found, creating...'
    python3 -m virtualenv -p python3 "$VENV_DIR" && echo 'Done.'
    new_env=1
fi

echo 'Activating python environment...'
source "$VENV_DIR/bin/activate"
touch "$VENV_DIR/COLCON_IGNORE"
echo 'Done.'

if [[ new_env -eq 1 ]]; then
    python3 -m pip install -r requirements.txt
fi

echo "Sourcing ROS $ROS_DISTRO underlay environment..."
source "/opt/ros/$ROS_DISTRO/setup.zsh" && echo 'Done.'

echo 'Sourcing workspace overlay environment...'
source ./install/setup.zsh && echo "Done."

eval "$(register-python-argcomplete ros2)"
eval "$(register-python-argcomplete colcon)"

export PYTHONPATH="$VENV_DIR/lib/python3.12/site-packages":$PYTHONPATH
