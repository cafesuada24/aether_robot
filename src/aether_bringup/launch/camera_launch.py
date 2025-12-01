from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

PKG_NAME = 'aether_bringup'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for hardware bringup."""
    pkg_share = FindPackageShare(PKG_NAME)
    camera_params_file = PathJoinSubstitution(
        [pkg_share, 'params', 'camera.yaml'],
    )

    camera = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        parameters=[camera_params_file],
        remappings=[('__ns', '/camera')],
    )

    ld = LaunchDescription()
    ld.add_action(camera)
    return ld
