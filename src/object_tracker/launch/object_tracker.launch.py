import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

PKG_NAME = 'object_tracker'

def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory(PKG_NAME)

    params = os.path.join(pkg_share, 'params', 'params.yaml')


    
    object_detector_node = ComposableNode(
        package='object_tracker',
        plugin='object_tracker::node::ObjectDetector',
        name='object_detector',
        parameters=[params],
        remappings=[('/image_in', '/camera/image_raw')]
    ) 

    object_follow_node = ComposableNode(
        package='object_tracker',
        plugin='object_tracker::node::ObjectFollow',
        name='object_follow',
        parameters=[params],
        # remappings=[('/out_vel', '/cmd_vel')]
    )

    container = ComposableNodeContainer(
        name='object_tracker',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[
            object_detector_node,
            object_follow_node,
        ],
        output='screen',
    )


    return LaunchDescription([container])
