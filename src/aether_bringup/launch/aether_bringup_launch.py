import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.actions.execute_local import OnProcessExit
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG_NAME = 'aether_bringup'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for aether."""
    pkg_share = get_package_share_directory(PKG_NAME)
    aether_nav_share = get_package_share_directory('aether_navigation')
    aether_webserver_share = get_package_share_directory('aether_webserver')
    aether_description_share = get_package_share_directory('aether_description')
    aether_agent_share = get_package_share_directory('aether_agent')
    default_robot_description_path = os.path.join(
        aether_description_share,
        'sdf',
        'robot.sdf',
    )
    robot_controllers = os.path.join(
        pkg_share,
        'params',
        'controllers.yaml',
    )

    model_path = LaunchConfiguration('model')
    sim_mode = LaunchConfiguration('sim_mode')
    slam = LaunchConfiguration('slam')
    use_localization = LaunchConfiguration('use_localization')
    map_yaml = LaunchConfiguration('map')
    webserver = LaunchConfiguration('webserver')
    agent = LaunchConfiguration('agent')

    declare_model_path_cmd = DeclareLaunchArgument(
        name='model',
        default_value=default_robot_description_path,
        description='Absolute path to robot model file',
    )
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
    declare_agent_cmd = DeclareLaunchArgument(
        'agent',
        default_value='True',
        description='Whether to enable agent or not',
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
    agent_launch_file = os.path.join(
        aether_agent_share,
        'launch',
        'agent_launch.py',
    )

    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        remappings=[('/cmd_vel_out', '/wheel_controller/cmd_vel')],
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
            os.path.join(
                aether_webserver_share, 'launch', 'webserver_bringup_launch.py'
            ),
        ),
        launch_arguments={
            'use_sim_time': sim_mode,
        }.items(),
        condition=IfCondition(webserver),
    )

    # Hardwares launch
    hardware_bringup_launch = IncludeLaunchDescription(
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

    agent_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(agent_launch_file),
        launch_arguments={
            'use_sim_time': sim_mode,
        }.items(),
        condition=IfCondition(agent),
    )

    robot_urdf_config = ParameterValue(
        Command(
            [
                'xacro ',
                model_path,
                ' sim_mode:=',
                sim_mode,
                ' controller_params_file:=',
                robot_controllers,
            ],
        ),
        value_type=str,
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {
                'robot_description': robot_urdf_config,
                'use_sim_time': sim_mode,
            },
        ],
    )
    controller_manager_spawner = Node(
        condition=UnlessCondition(sim_mode),
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_controllers],
    )
    delayed_controller_manager_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=robot_state_publisher_node,
            on_start=[controller_manager_spawner],
        ),
        condition=UnlessCondition(sim_mode),
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )

    robot_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['wheel_controller', '--param-file', robot_controllers],
    )

    delayed_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_controller_spawner,
            on_exit=[joint_state_broadcaster_spawner],
        ),
    )


    return LaunchDescription(
        [
            # Parameters declaration
            declare_sim_mode_cmd,
            declare_slam_cmd,
            declare_use_localization_cmd,
            declare_map_yaml_cmd,
            declare_webserver_cmd,
            declare_model_path_cmd,
            declare_agent_cmd,
            # Launch nodes
            robot_state_publisher_node,
            hardware_bringup_launch,
            teleop_twist_joy,
            twist_mux_node,
            nav_bringup_launch,
            webserver_bringup_launch,
            delayed_controller_manager_spawner,
            robot_controller_spawner,
            delayed_joint_state_broadcaster,
            agent_launch,
        ],
    )
