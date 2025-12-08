from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare

PKG_NAME = 'aether_webserver'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for web servers."""
    # pkg_share = get_package_share_directory(PKG_NAME)
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_composition = LaunchConfiguration('use_composition')
    cam_container_name = LaunchConfiguration('cam_container_name')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='False',
        description='Use simulation (Gazebo) clock if True',
    )
    declare_use_composition_cmd = DeclareLaunchArgument(
        'use_composition',
        default_value='True',
        description='Whether to use composed bringup',
        choices=['True', 'False'],
    )
    declare_cam_container_name_cmd = DeclareLaunchArgument(
        'cam_container_name',
        default_value='cam_container',
        description='Container name that contains camera',
    )
    # foxglove_bridge_share_dir = get_package_share_directory('foxglove_bridge')
    rosbridge_server_share_dir = FindPackageShare('rosbridge_server')

    # websocket_node = Node(
    #     package='rosbridge_server',
    #     executable='rosbridge_websocket',
    # )

    rosbridge_launch = IncludeLaunchDescription(
        FrontendLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    rosbridge_server_share_dir,
                    'launch',
                    # 'foxglove_bridge_launch.xml',
                    'rosbridge_websocket_launch.xml',
                ]
            ),
        ),
        launch_arguments={
            # 'port': '8765',
            'use_sim_time': use_sim_time,
            'delay_between_messages': '0.0',
            # 'include_hidden': 'True',
        }.items(),
    )

    run_web_video_server = Node(
        package='web_video_server',
        executable='web_video_server',
        condition=UnlessCondition(use_composition),
    )

    load_composable_web_video_server = LoadComposableNodes(
        condition=IfCondition(use_composition),
        target_container=cam_container_name,
        composable_node_descriptions=[
            ComposableNode(
                package='web_video_server',
                plugin='web_video_server::WebVideoServer',
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
    )

    service_advertiser_node = Node(
        package=PKG_NAME,
        executable='service_advertiser',
        output='screen',
    )
    ld = LaunchDescription()

    # Arguments
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_use_composition_cmd)
    ld.add_action(declare_cam_container_name_cmd)

    ld.add_action(rosbridge_launch)
    ld.add_action(run_web_video_server)
    ld.add_action(load_composable_web_video_server)
    ld.add_action(service_advertiser_node)

    return ld
