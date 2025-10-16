import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

PKG_NAME = 'aether_bringup'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for hardware bringup."""
    pkg_share = get_package_share_directory(PKG_NAME)
    camera_params_file = os.path.join(
        pkg_share,
        'params',
        'camera.yaml',
    )
    rplidar_params_file = os.path.join(
        pkg_share,
        'params',
        'rplidar.yaml',
    )
    driver_params_file = os.path.join(
        pkg_share,
        'params',
        'driver.yaml',
    )

    camera = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        parameters=[camera_params_file],
        remappings=[('__ns', '/camera')],
    )

    rplidar = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        parameters=[rplidar_params_file],
        remappings=[('scan', 'lidar')],
    )

    driver_node = Node(
        package='aether_driver',
        executable='driver_node',
        parameters=[driver_params_file],
    )

    ld = LaunchDescription()
    ld.add_action(camera)
    ld.add_action(rplidar)
    # ld.add_action(driver_node)
    return ld
