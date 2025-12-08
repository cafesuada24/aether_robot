from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

# --- Configuration Constants (Best Practice: Use consistent, readable names) ---
PKG_NAME = 'aether_bringup'
NAV2_CONTAINER_NAME = 'nav2_container'
LAM_CONTAINER_NAME = 'lam_container'
CAM_PIPELINE_CONTAINER_NAME = 'cam_container'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for aether with optimized path handling."""
    # 1. Package Share Lookups (Use FindPackageShare for launch-time evaluation)
    pkg_share = FindPackageShare(PKG_NAME)
    aether_description_share = FindPackageShare('aether_description')
    aether_nav_share = FindPackageShare('aether_navigation')
    aether_webserver_share = FindPackageShare('aether_webserver')
    aether_agent_share = FindPackageShare('aether_agent')
    aether_driver_share = FindPackageShare('aether_driver')

    # 2. File Path Definitions (Use PathJoinSubstitution for robustness)

    # EKF Config
    ekf_config_path = PathJoinSubstitution([pkg_share, 'params', 'ekf.yaml'])

    # Robot Model (SDF/XACRO)
    default_robot_description_path = PathJoinSubstitution(
        [
            aether_description_share,
            'sdf',
            'robot.sdf',
        ],
    )

    # Controller Config
    robot_controllers = PathJoinSubstitution(
        [
            pkg_share,
            'params',
            'controllers.yaml',
        ],
    )

    # Twist Mux Config
    twist_mux_params_file = PathJoinSubstitution(
        [
            pkg_share,
            'params',
            'twist_mux.yaml',
        ],
    )

    # Navigation Bringup Launch File
    nav_bringup_launch_file = PathJoinSubstitution(
        [
            aether_nav_share,
            'launch',
            'bringup_launch.py',
        ],
    )

    # Agent Launch File
    agent_launch_file = PathJoinSubstitution(
        [
            aether_agent_share,
            'launch',
            'agent_launch.py',
        ],
    )

    # Webserver Bringup Launch File
    webserver_bringup_launch_path = PathJoinSubstitution(
        [
            aether_webserver_share,
            'launch',
            'webserver_bringup_launch.py',
        ],
    )

    # --- 3. Launch Configurations ---
    model_path = LaunchConfiguration('model')
    sim_mode = LaunchConfiguration('sim_mode')
    # slam = LaunchConfiguration('slam')
    use_localization = LaunchConfiguration('use_localization')
    # map_yaml = LaunchConfiguration('map')
    webserver = LaunchConfiguration('webserver')
    agent = LaunchConfiguration('agent')
    use_composition = LaunchConfiguration('use_composition')
    log_level = LaunchConfiguration('log_level')

    # --- 4. Declare Launch Arguments (Using PathJoinSubstitution for defaults) ---
    declare_model_path_cmd = DeclareLaunchArgument(
        name='model',
        default_value=default_robot_description_path,
        description='Absolute path to robot model file (SDF/XACRO)',
    )
    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=PathJoinSubstitution([pkg_share, 'map', 'house_map.yaml']),
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

    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition',
        default_value='True',
        description='Whether to use composed bringup',
        choices=['True', 'False'],
    )

    declare_log_level_cmd = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='log level',
    )

    # --- 5. Nodes and Actions ---

    # Twist Mux Node (Manages multiple velocity commands)
    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        remappings=[('/cmd_vel_out', '/wheel_controller/cmd_vel')],
        parameters=[twist_mux_params_file],
    )

    # Teleop Twist Joy Node (Joystick/Game Controller Input)
    teleop_twist_joy = Node(
        package='teleop_twist_joy',
        executable='teleop_node',
        parameters=[
            {'publish_stamped_twist': True},
            {'require_enable_button': False},
            {'axis_linear.x': 1},
            {'axis_angular.yaw': 0},
            # Use LaunchConfiguration for dynamic parameter
            {'use_sim_time': sim_mode},
        ],
        remappings=[('cmd_vel', 'joy_cmd_vel')],
    )

    # LiDAR/Hardware Component Container (Crucial for IPC optimization)
    # Using Multi-Threaded Executor for concurrency benefits

    # Hardware Drivers Group (Only run if NOT in simulation mode)
    # Camera Launch
    create_cam_container_cmd = Node(
        condition=IfCondition(use_composition),
        name=CAM_PIPELINE_CONTAINER_NAME,
        package='rclcpp_components',
        executable='component_container_mt',
        arguments=['--ros-args', '--log-level', log_level],
        output='screen',
    )

    hardware_group = GroupAction(
        condition=UnlessCondition(sim_mode),
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([pkg_share, 'launch', 'camera_launch.py']),
                ),
                launch_arguments=[
                    ('use_composition', use_composition),
                    ('container_name', CAM_PIPELINE_CONTAINER_NAME),
                ],
            ),
            # Arduino Bridge Launch (Assuming this handles motor controllers/base I/O)
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [
                            aether_driver_share,
                            'launch',
                            'ros_arduino_bridge_launch.py',
                        ],
                    ),
                ),
            ),
            # RPLIDAR Driver Launch (Uses composition into the container)
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([pkg_share, 'launch', 'rplidar_launch.py']),
                ),
                launch_arguments=[
                    ('use_composition', use_composition),
                    ('container_name', LAM_CONTAINER_NAME),
                ],
            ),
        ],
    )

    # EKF Localization Node (Typically not composable, runs standalone)
    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_path, {'use_sim_time': sim_mode}],
        condition=IfCondition(use_localization),
    )

    # Navigation Bringup (SLAM/AMCL, planners, etc.)
    nav_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav_bringup_launch_file),
        launch_arguments=[
            ('use_sim_time', sim_mode),
            # ('slam', slam),
            ('use_localization', use_localization),
            # ('map', map_yaml),
            ('use_composition', use_composition),
            ('nav_container_name', NAV2_CONTAINER_NAME),
            # IMPORTANT: Passing the LiDAR container name so SLAM/Mapper can share IPC with the LiDAR driver
            ('lam_container_name', LAM_CONTAINER_NAME),
        ],
    )

    # Agent System Launch
    agent_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(agent_launch_file),
        launch_arguments=[('use_sim_time', sim_mode)],
        condition=IfCondition(agent),
    )

    # Webserver Launch
    webserver_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(webserver_bringup_launch_path),
        launch_arguments=[
            ('use_sim_time', sim_mode),
            ('use_composition', use_composition),
            ('cam_container_name', CAM_PIPELINE_CONTAINER_NAME),
        ],
        condition=IfCondition(webserver),
    )

    # XACRO processing (Generate robot description string)
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

    # Robot State Publisher Node
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

    # ROS 2 Control Hardware Interface (Only runs when NOT in simulation)
    controller_manager_spawner = Node(
        condition=UnlessCondition(sim_mode),
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_controllers],
    )

    # Delay controller manager until Robot State Publisher is started
    delayed_controller_manager_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=robot_state_publisher_node,
            on_start=[controller_manager_spawner],
        ),
        condition=UnlessCondition(sim_mode),
    )

    # Spawner for Joint State Broadcaster
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )

    # Spawner for the main wheel controller
    robot_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['wheel_controller', '--param-file', robot_controllers],
    )

    # Delayed launch of Joint State Broadcaster, ensuring the main controller is up first
    delayed_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_controller_spawner,
            on_exit=[joint_state_broadcaster_spawner],
        ),
    )

    # --- 6. Build the Launch Description ---
    return LaunchDescription(
        [
            # Declare Arguments
            declare_model_path_cmd,
            declare_map_yaml_cmd,
            declare_sim_mode_cmd,
            declare_slam_cmd,
            declare_use_localization_cmd,
            declare_webserver_cmd,
            declare_agent_cmd,
            declare_use_composition_cmd,
            declare_log_level_cmd,
            # Core Robot State & Control
            create_cam_container_cmd,
            robot_state_publisher_node,
            delayed_controller_manager_spawner,
            robot_controller_spawner,
            delayed_joint_state_broadcaster,
            # Teleop & Muxing
            twist_mux_node,
            teleop_twist_joy,
            # Sensor/Hardware Composition Setup
            hardware_group,
            # Core Systems
            robot_localization_node,
            nav_bringup_launch,
            # Auxiliary Systems (Conditional)
            webserver_bringup_launch,
            agent_launch,
        ],
    )
