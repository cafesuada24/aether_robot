#!/bin/bash

set -e

source /home/$(whoami)/ros2_ws/scripts/setup.bash

source /opt/ros/jazzy/setup.bash

echo "Provided arguments: $@"

exec $@

