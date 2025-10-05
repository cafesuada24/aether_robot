import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch_ros.actions import Node

PKG_NAME = 'aether_bringup'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for web servers."""
    # pkg_share = get_package_share_directory(PKG_NAME)
    foxglove_bridge_share_dir = get_package_share_directory('foxglove_bridge')

    # websocket_node = Node(
    #     package='rosbridge_server',
    #     executable='rosbridge_websocket',
    # )

    foxglove_bridge_launch = IncludeLaunchDescription(
        FrontendLaunchDescriptionSource(
            os.path.join(
                foxglove_bridge_share_dir,
                'launch',
                'foxglove_bridge_launch.xml',
            )
        ),
        launch_arguments={'port': '8765'}.items(),
    )

    web_video_server = Node(
        package='web_video_server',
        executable='web_video_server',
    )
    ld = LaunchDescription()

    ld.add_action(foxglove_bridge_launch)
    ld.add_action(web_video_server)

    return ld
