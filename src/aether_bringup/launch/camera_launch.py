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
    """Generate launch description for hardware bringup."""
    pkg_share = FindPackageShare(PKG_NAME)
    camera_params_file = PathJoinSubstitution(
        [pkg_share, 'params', 'camera.yaml'],
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

    container_name = LaunchConfiguration('container_name')
    use_composition = LaunchConfiguration('use_composition')

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=camera_params_file,
            root_key='',
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
    )

    remappings = [('__ns', '/camera')]

    run_camera = Node(
        condition=UnlessCondition(use_composition),
        package='v4l2_camera',
        executable='v4l2_camera_node',
        parameters=[camera_params_file],
        remappings=remappings,
    )

    load_composable_camera = LoadComposableNodes(
        condition=IfCondition(use_composition),
        target_container=container_name,
        composable_node_descriptions=[
            ComposableNode(
                package='v4l2_camera',
                plugin='v4l2_camera::V4L2Camera',
                name='v4l2_camera',
                parameters=[configured_params],
                remappings=remappings,
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
    )
    ld = LaunchDescription()
    # Declare arguments
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_container_name_cmd)

    #Nodes
    ld.add_action(run_camera)
    ld.add_action(load_composable_camera)

    return ld
