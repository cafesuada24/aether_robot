import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch_ros.actions import Node

PKG_NAME = 'aether'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for aether."""
    cmd_vel_out_topic = LaunchConfiguration('cmd_vel_out_topic')
    sim_mode = LaunchConfiguration('sim_mode')

    pkg_share = get_package_share_directory(PKG_NAME)
    aether_nav_share = get_package_share_directory('aether_navigation')
    # rosbridge_server_share = get_package_share_directory('rosbridge_server')
    twist_mux_params_file = os.path.join(
        pkg_share,
        'params',
        'twist_mux.yaml',
    )
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

    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        remappings=[('/cmd_vel_out', cmd_vel_out_topic)],
        parameters=[twist_mux_params_file],
    )

    slam_online_async_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(aether_nav_share, 'launch', 'slam_online_async_launch.py'),
        ),
        launch_arguments={
            'use_sim_time': sim_mode,
        }.items(),
    )

    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(aether_nav_share, 'launch', 'navigation_launch.py'),
        ),
        launch_arguments={
            'use_sim_time': sim_mode,
        }.items(),
    )

    websocket_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
    )

    web_video_server = Node(
        package='web_video_server',
        executable='web_video_server',
    )

    teleop_twist_joy = Node(
        package='teleop_twist_joy',
        executable='teleop_node',
        parameters=[
            {'publish_stamped_twist': True},
            {'require_enable_button': False},
            {'axis_linear.x': 1},
            {'axis_angular.yaw': 0},
            {'use_sim_time': sim_mode},
        ],
        remappings=[('cmd_vel', 'joy_cmd_vel')],
    )

    # Hardwares launch
    camera = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        parameters=[camera_params_file],
        remappings=[('__ns', '/camera')],
        condition=IfCondition(EqualsSubstitution(sim_mode, 'false')),
    )

    rplidar = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        parameters=[rplidar_params_file],
        remappings=[('scan', 'lidar')],
        condition=IfCondition(EqualsSubstitution(sim_mode, 'false')),
    )

    driver_node = Node(
        package='aether_driver',
        executable='driver_node',
        parameters=[driver_params_file],
        condition=IfCondition(EqualsSubstitution(sim_mode, 'false')),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                name='cmd_vel_out_topic',
                default_value='cmd_vel',
                description='Topic that receives twist data',
            ),
            DeclareLaunchArgument(
                name='sim_mode',
                default_value='false',
                description='Flag to enable simulation mode',
                choices=['true', 'false'],
            ),
            driver_node,
            rplidar,
            camera,

            twist_mux_node,
            slam_online_async_launch,
            navigation_launch,
            websocket_node,
            web_video_server,
            teleop_twist_joy,
        ],
    )
