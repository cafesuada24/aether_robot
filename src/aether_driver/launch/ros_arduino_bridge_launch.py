# Copyright (c) 2025 Cafesuada
# All rights reserved.

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

PKG_NAME = 'aether_driver'

def generate_launch_description() -> LaunchDescription:
    pkg_share = FindPackageShare(PKG_NAME)
    ros_arduino_bridge_params_file = PathJoinSubstitution(
        [
            pkg_share,
            'params',
            'ros_arduino_bridge.yaml',
        ],
    )

    ros_arduino_bridge = Node(
        package='aether_driver',
        executable='ros_arduino_bridge',
        parameters=[ros_arduino_bridge_params_file],
    )

    ld = LaunchDescription()
    ld.add_action(ros_arduino_bridge)
    return ld
