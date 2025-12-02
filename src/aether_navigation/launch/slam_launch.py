from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    RegisterEventHandler,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.events import matches_action
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    AndSubstitution,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import LoadComposableNodes, Node, SetParameter, SetRemap
from launch_ros.descriptions import ComposableNode, ParameterFile
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState, matches_node_name
from launch_ros.substitutions import FindPackageShare
from lifecycle_msgs.msg import Transition
from nav2_common.launch import RewrittenYaml

PKG_NAME = 'aether_navigation'


def generate_launch_description() -> LaunchDescription:
    # Input parameters declaration
    namespace = LaunchConfiguration('namespace')
    params_file = LaunchConfiguration('params_file')
    slam_params_file = LaunchConfiguration('slam_params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')
    use_composition = LaunchConfiguration('use_composition')
    container_name = LaunchConfiguration('container_name')

    # Variables
    lifecycle_nodes = ['map_saver', 'slam_toolbox']

    # Getting directories and launch-files
    pkg_share_dir = FindPackageShare(PKG_NAME)
    slam_toolbox_dir = FindPackageShare('slam_toolbox')
    slam_launch_file = PathJoinSubstitution(
        [slam_toolbox_dir, 'launch', 'slam_online_sync_launch.py'],
    )

    # Create our own temporary YAML files that include substitutions
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=slam_params_file,
            root_key=namespace,
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
    )

    # Declare the launch arguments
    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Top-level namespace',
    )

    declare_slam_params_file_cmd = DeclareLaunchArgument(
        'slam_params_file',
        default_value=PathJoinSubstitution(
            [pkg_share_dir, 'params', 'mapper_params_online_sync.yaml'],
        ),
        description='Full path to the ROS2 parameters file to use for slam_toolbox node',
    )

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution(
            [pkg_share_dir, 'params', 'nav2_params.yaml'],
        ),
        description='Full path to the ROS2 parameters file to use for nav2 nodes',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='True',
        description='Use simulation (Gazebo) clock if true',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='True',
        description='Automatically startup the nav2 stack',
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

    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition',
        default_value='True',
        description='Whether to use composed bringup',
    )

    declare_container_name = DeclareLaunchArgument(
        'container_name',
        default_value='lidar_pipeline_container',
        description='container name',
    )

    # Nodes launching commands
    start_map_server = GroupAction(
        actions=[
            SetParameter('use_sim_time', use_sim_time),
            Node(
                package='nav2_map_server',
                executable='map_saver_server',
                output='screen',
                respawn=use_respawn,
                respawn_delay=2.0,
                arguments=['--ros-args', '--log-level', log_level],
                parameters=[configured_params],
            ),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_slam',
                output='screen',
                arguments=['--ros-args', '--log-level', log_level],
                parameters=[{'autostart': autostart}, {'node_names': lifecycle_nodes}],
            ),
        ],
    )

    # If the provided param file doesn't have slam_toolbox params, we must remove the 'params_file'
    # LaunchConfiguration, or it will be passed automatically to slam_toolbox and will not load
    # the default file
    # has_slam_toolbox_params = HasNodeParams(
    #     source_file=params_file, node_name='slam_toolbox',
    # )

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=slam_params_file,
            root_key=namespace,
            param_rewrites={'autostart': autostart},
            convert_types=True,
        ),
        allow_substs=True,
    )

    start_slam_toolbox_cmd = GroupAction(
        actions=[
            # Remapping required to have a slam session subscribe & publish in optional namespaces
            SetRemap(src='/sensor/lidar', dst='sensor/lidar'),
            SetRemap(src='/tf', dst='tf'),
            SetRemap(src='/tf_static', dst='tf_static'),
            SetRemap(src='/map', dst='map'),
            # IncludeLaunchDescription(
            #     PythonLaunchDescriptionSource(slam_launch_file),
            #     launch_arguments={'use_sim_time': use_sim_time}.items(),
            #     condition=UnlessCondition(has_slam_toolbox_params),
            # ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(slam_launch_file),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'slam_params_file': slam_params_file,
                }.items(),
                condition=UnlessCondition(use_composition),
            ),
            LoadComposableNodes(
                condition=IfCondition(use_composition),
                target_container=[namespace, '/', container_name],
                composable_node_descriptions=[
                    ComposableNode(
                        package='slam_toolbox',
                        plugin='slam_toolbox::SynchronousSlamToolbox',
                        name='slam_toolbox',
                        parameters=[
                            configured_params,
                            {'use_lifecycle_manager': True},
                            {'use_sim_time': use_sim_time},
                        ],
                        remappings=[('/sensor/lidar', '/sensor/lidar')],
                        extra_arguments=[{'use_intra_process_comms': True}],
                    ),
                ],
            ),
        ],
    )

    ld = LaunchDescription()

    # Declare the launch options
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_slam_params_file_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_use_respawn_cmd)
    ld.add_action(declare_log_level_cmd)
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_container_name)

    # Running Map Saver Server
    ld.add_action(start_map_server)

    # Running SLAM Toolbox (Only one of them will be run)
    ld.add_action(start_slam_toolbox_cmd)

    return ld
