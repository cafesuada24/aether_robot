import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

PKG_NAME = 'aether'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for aether."""
    pkg_share = get_package_share_directory(PKG_NAME)

    twist_mux_params_file = os.path.join(
        pkg_share,
        'params',
        'twist_mux.yaml',
    )
    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        remappings=[('/cmd_vel_out', 'cmd_vel')],
        parameters=[twist_mux_params_file],
    )

    twist_stamper_node = Node(
        package='aether',
        executable='twist_stamper_node',
        output='screen',
    )

    return LaunchDescription([twist_mux_node])
