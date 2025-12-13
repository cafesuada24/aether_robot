# Copyright (c) 2025 Cafesuada
# All rights reserved.

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node, PushROSNamespace, SetParameter
from launch_ros.descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import ReplaceString, RewrittenYaml

PKG_NAME = 'aether_navigation'


def generate_launch_description() -> LaunchDescription:
    # Get the launch directory

    pkg_share_dir = FindPackageShare(PKG_NAME)
    launch_dir = PathJoinSubstitution([pkg_share_dir, 'launch'])

    # Create the launch configuration variables
    namespace = LaunchConfiguration('namespace')
    use_namespace = LaunchConfiguration('use_namespace')
    # slam = LaunchConfiguration('slam')
    # map_yaml_file = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    nav2_params_file = LaunchConfiguration('nav2_params_file')
    lam_params_file = LaunchConfiguration('lam_params_file')
    autostart = LaunchConfiguration('autostart')
    use_composition = LaunchConfiguration('use_composition')
    nav_container_name = LaunchConfiguration('nav_container_name')
    lam_container_name = LaunchConfiguration('lam_container_name')
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')
    use_localization = LaunchConfiguration('use_localization')

    # Map fully qualified names to relative ones so the node's namespace can be prepended.
    # In case of the transforms (tf), currently, there doesn't seem to be a better alternative
    # https://github.com/ros/geometry2/issues/32
    # https://github.com/ros/robot_state_publisher/pull/30
    # TODO(orduno) Substitute with `PushNodeRemapping`
    #              https://github.com/ros2/launch_ros/issues/56
    remappings = [
        ('/tf', 'tf'),
        ('/tf_static', 'tf_static'),
    ]

    # Only it applys when `use_namespace` is True.
    # '<robot_namespace>' keyword shall be replaced by 'namespace' launch argument
    # in config file 'nav2_multirobot_params.yaml' as a default & example.
    # User defined config file should contain '<robot_namespace>' keyword for the replacements.
    nav2_params_file = ReplaceString(
        source_file=nav2_params_file,
        replacements={'<robot_namespace>': ('/', namespace)},
        condition=IfCondition(use_namespace),
    )

    nav2_configured_params = ParameterFile(
        RewrittenYaml(
            source_file=nav2_params_file,
            root_key=namespace,
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
    )

    lam_params_file = ReplaceString(
        source_file=lam_params_file,
        replacements={'<robot_namespace>': ('/', namespace)},
        condition=IfCondition(use_namespace),
    )

    lam_cofigured_params = ParameterFile(
        RewrittenYaml(
            source_file=lam_params_file,
            root_key=namespace,
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
    )

    stdout_linebuf_envvar = SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM',
        '1',
    )

    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Top-level namespace',
    )

    declare_use_namespace_cmd = DeclareLaunchArgument(
        'use_namespace',
        default_value='False',
        description='Whether to apply a namespace to the navigation stack',
    )

    # declare_slam_cmd = DeclareLaunchArgument(
    #     'slam',
    #     default_value='False',
    #     description='Whether run a SLAM',
    # )

    # declare_map_yaml_cmd = DeclareLaunchArgument(
    #     'map',
    #     default_value='',
    #     description='Full path to map yaml file to load',
    # )

    declare_use_localization_cmd = DeclareLaunchArgument(
        'use_localization',
        default_value='True',
        description='Whether to enable localization or not',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='False',
        description='Use simulation (Gazebo) clock if True',
    )

    declare_nav2_params_file_cmd = DeclareLaunchArgument(
        'nav2_params_file',
        default_value=PathJoinSubstitution(
            [pkg_share_dir, 'params', 'nav2_params.yaml'],
        ),
        description='Full path to the ROS2 parameters file to use for nav2 nodes',
    )

    declare_lam_params_file_cmd = DeclareLaunchArgument(
        'lam_params_file',
        default_value=PathJoinSubstitution(
            [pkg_share_dir, 'params', 'localization_and_mapping.yaml'],
        ),
        description='Full path to the ROS2 parameters file to use for AMCL and SLAM nodes',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='True',
        description='Automatically startup the nav2 stack',
    )

    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition',
        default_value='True',
        description='Whether to use composed bringup',
    )

    declare_use_respawn_cmd = DeclareLaunchArgument(
        'use_respawn',
        default_value='False',
        description='Whether to respawn if a node crashes. Applied when composition is disabled.',
    )

    declare_log_level_cmd = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='log level',
    )

    declare_container_name = DeclareLaunchArgument(
        'container_name',
        default_value='nav2_container',
        description='container name',
    )

    declare_lam_container_name_cmd = DeclareLaunchArgument(
        'lam_container_name',
        default_value='lam_container',
        description='lam container name',
    )

    run_map_manager_node = Node(
        package=PKG_NAME,
        executable='map_manager_node',
        name='map_manager',
        output='screen',
        arguments=['--ros-args', '--log-level', log_level],
    )
    run_waypoints_manager_node = Node(
        package=PKG_NAME,
        executable='waypoints_node.py',
        name='waypoints_manager',
        output='screen',
        arguments=['--ros-args', '--log-level', log_level],
    )

    # Specify the actions
    bringup_cmd_group = GroupAction(
        [
            PushROSNamespace(condition=IfCondition(use_namespace), namespace=namespace),
            SetParameter('use_sim_time', use_sim_time),
            # Containers
            Node(
                condition=IfCondition(use_composition),
                name=nav_container_name,
                package='rclcpp_components',
                executable='component_container_isolated',
                parameters=[nav2_configured_params, {'autostart': autostart}],
                arguments=['--ros-args', '--log-level', log_level],
                remappings=remappings,
                output='screen',
            ),
            Node(
                condition=IfCondition(use_composition),
                name=lam_container_name,
                package='rclcpp_components',
                executable='component_container_mt',
                parameters=[lam_cofigured_params, {'autostart': autostart}],
                arguments=['--ros-args', '--log-level', log_level],
                remappings=remappings,
                output='screen',
            ),
            # Lifecycle manager
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([launch_dir, 'navigation_launch.py']),
                ),
                launch_arguments={
                    'namespace': namespace,
                    'use_sim_time': use_sim_time,
                    'autostart': autostart,
                    'params_file': nav2_params_file,
                    'use_composition': use_composition,
                    'use_respawn': use_respawn,
                    'container_name': nav_container_name,
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [launch_dir, 'localization_and_mapping_launch.py'],
                    ),
                ),
                condition=IfCondition(use_localization),
                launch_arguments={
                    'namespace': namespace,
                    'use_sim_time': use_sim_time,
                    'autostart': autostart,
                    'params_file': lam_params_file,
                    'use_composition': use_composition,
                    'use_respawn': use_respawn,
                    'container_name': lam_container_name,
                }.items(),
            ),
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource(
            #         PathJoinSubstitution([launch_dir, 'slam_launch.py']),
            #     ),
            #     condition=IfCondition(
            #         PythonExpression([slam, ' and ', use_localization]),
            #     ),
            #     launch_arguments={
            #         'namespace': namespace,
            #         'use_sim_time': use_sim_time,
            #         'autostart': autostart,
            #         'use_respawn': use_respawn,
            #         'params_file': params_file,
            #         'use_composition': use_composition,
            #         'container_name': slam_container_name,
            #     }.items(),
            # ),
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource(
            #         PathJoinSubstitution([launch_dir, 'localization_launch.py']),
            #     ),
            #     condition=IfCondition(
            #         PythonExpression(['not ', slam, ' and ', use_localization]),
            #     ),
            #     launch_arguments={
            #         'namespace': namespace,
            #         'map': map_yaml_file,
            #         'use_sim_time': use_sim_time,
            #         'autostart': autostart,
            #         'params_file': params_file,
            #         'use_composition': use_composition,
            #         'use_respawn': use_respawn,
            #         'container_name': container_name,
            #     }.items(),
            # ),
        ],
    )

    # Create the launch description and populate
    ld = LaunchDescription()

    # Set environment variables
    ld.add_action(stdout_linebuf_envvar)

    # Declare the launch options
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_use_namespace_cmd)
    # ld.add_action(declare_slam_cmd)
    # ld.add_action(declare_map_yaml_cmd)
    ld.add_action(run_map_manager_node)
    ld.add_action(run_waypoints_manager_node)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_nav2_params_file_cmd)
    ld.add_action(declare_lam_params_file_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_use_respawn_cmd)
    ld.add_action(declare_log_level_cmd)
    ld.add_action(declare_use_localization_cmd)
    ld.add_action(declare_container_name)
    ld.add_action(declare_lam_container_name_cmd)

    # Add the actions to launch all of the navigation nodes
    ld.add_action(bringup_cmd_group)

    return ld
