import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PKG_NAME = 'aether_bringup'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for aether."""
    pkg_share = get_package_share_directory(PKG_NAME)
    aether_nav_share = get_package_share_directory('aether_navigation')
    aether_webserver_share = get_package_share_directory('aether_webserver')

    sim_mode = LaunchConfiguration('sim_mode')

    slam = LaunchConfiguration('slam')
    use_localization = LaunchConfiguration('use_localization')
    map_yaml = LaunchConfiguration('map')
    webserver = LaunchConfiguration('webserver')

    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_share, 'map', 'my_map.yaml'),
        description='Full path to map yaml file to load',
    )
    declare_sim_mode_cmd = DeclareLaunchArgument(
        name='sim_mode',
        default_value='False',
        description='Flag to enable simulation mode',
        choices=['True', 'False'],
    )
    declare_slam_cmd = DeclareLaunchArgument(
        'slam',
        default_value='False',
        description='Whether run a SLAM',
        choices=['True', 'False'],
    )

    declare_use_localization_cmd = DeclareLaunchArgument(
        'use_localization',
        default_value='True',
        description='Whether to enable localization or not',
        choices=['True', 'False'],
    )

    declare_webserver_cmd = DeclareLaunchArgument(
        'webserver',
        default_value='True',
        description='Whether to enable web server or not',
        choices=['True', 'False'],
    )

    nav_bringup_launch_file = os.path.join(
        aether_nav_share,
        'launch',
        'bringup_launch.py',
    )

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

    # Websocket launch
    webserver_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(aether_webserver_share, 'launch', 'webserver_bringup_launch.py'),
        ),
        launch_arguments={
            'use_sim_time': sim_mode,
        }.items(),
        condition=IfCondition(webserver),
    )

    # Hardwares launch
    driver_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'hardware_bringup_launch.py'),
        ),
        condition=UnlessCondition(sim_mode),
    )

    nav_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav_bringup_launch_file),
        launch_arguments={
            'use_sim_time': sim_mode,
            'slam': slam,
            'use_localization': use_localization,
            'map': map_yaml,
            'container_name': 'aether_nav_container',
        }.items(),
    )

    return LaunchDescription(
        [
            # Parameters declaration
            declare_sim_mode_cmd,
            declare_slam_cmd,
            declare_use_localization_cmd,
            declare_map_yaml_cmd,
            declare_webserver_cmd,
            # Launch nodes
            driver_bringup_launch,
            teleop_twist_joy,
            twist_mux_node,
            nav_bringup_launch,
            webserver_bringup_launch,
        ],
    )
