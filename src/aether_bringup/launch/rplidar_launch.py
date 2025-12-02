from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode, ParameterFile
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml

PKG_NAME = 'aether_bringup'


def generate_launch_description() -> LaunchDescription:
    pkg_share_dir = FindPackageShare(PKG_NAME)

    container_name = LaunchConfiguration('container_name')
    use_composition = LaunchConfiguration('use_composition')

    rplidar_params_file = PathJoinSubstitution(
        [pkg_share_dir, 'params', 'rplidar.yaml'],
    )

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=rplidar_params_file,
            root_key='',
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
    )
    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition',
        default_value='True',
        description='Whether to use composed bringup',
        choices=['True', 'False'],
    )

    declare_container_name_cmd = DeclareLaunchArgument(
        'container_name',
        default_value='lidar_pipeline_container',
        description='container name',
    )

    run_lidar_node = Node(
        condition=UnlessCondition(use_composition),
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_node',
        output='screen',
        parameters=[rplidar_params_file],
    )

    load_composable_lidar = LoadComposableNodes(
        condition=IfCondition(use_composition),
        target_container=container_name,
        composable_node_descriptions=[
            ComposableNode(
                package='rplidar_ros',
                plugin='rplidar_ros::rplidar_node',
                name='rplidar_node',
                parameters=[configured_params],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
    )

    ld = LaunchDescription()

    # Declare arguments
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_container_name_cmd)

    # Actions
    ld.add_action(run_lidar_node)
    ld.add_action(load_composable_lidar)

    return ld
