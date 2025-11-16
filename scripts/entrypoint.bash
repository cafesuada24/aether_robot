#!/bin/bash

set -e

# source /home/ros/ros2_ws/scripts/setup.bash

source /opt/ros/jazzy/setup.bash

echo "Provided arguments: $@"

exec $@

