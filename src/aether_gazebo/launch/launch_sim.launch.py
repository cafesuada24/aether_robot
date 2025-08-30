import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer

PKG_NAME: str = 'aether_gazebo'


def generate_launch_description() -> LaunchDescription:
    model_path = LaunchConfiguration('model')
    use_sim_time = LaunchConfiguration('use_sim_time')

    pkg_share = get_package_share_directory(PKG_NAME)
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    default_model_path = os.path.join(pkg_share, 'description', 'robot.urdf.xacro.xml')
    bridge_config_path = os.path.join(pkg_share, 'config', 'bridge.yaml')
    gz_spawn_model_launch_source = os.path.join(
        ros_gz_sim_share,
        'launch',
        'gz_spawn_model.launch.py',
    )
    world_path = os.path.join(pkg_share, 'worlds', 'obstacle.world')

    robot_description_config = Command(
        [
            'xacro ',
            model_path,
            ' sim_mode:=',
            use_sim_time,
        ],
    )
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {
                'robot_description': robot_description_config,
                'use_sim_time': use_sim_time,
            },
        ],
    )

    gz_server = GzServer(
        world_sdf_file=world_path,
        container_name='ros_gz_container',
        create_own_container='True',
        use_composition='True',
    )

    gz_client_cmd = ExecuteProcess(cmd=['gz', 'sim', '-g', '-r'], output='screen')

    spawn_entity = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_spawn_model_launch_source),
        launch_arguments={
            'world': 'default',
            'topic': '/robot_description',
            'entity_name': 'aether_bot',
            'z': '0.175',
        }.items(),
    )

    ros_gz_bridge = RosGzBridge(
        bridge_name='ros_gz_bridge',
        config_file=bridge_config_path,
        container_name='ros_gz_container',
        create_own_container='False',
        use_composition='True',
    )

    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_node',
        output='screen',
        parameters=[
            os.path.join(pkg_share, 'params', 'ekf.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                name='model',
                default_value=default_model_path,
                description='Absolute path to robot model file',
            ),
            DeclareLaunchArgument(
                name='use_sim_time',
                default_value='True',
                description='Flag to enable use_sim_time',
            ),
            gz_client_cmd,
            robot_state_publisher_node,
            gz_server,
            ros_gz_bridge,
            spawn_entity,
            robot_localization_node,
        ],
    )
