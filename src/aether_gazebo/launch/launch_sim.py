import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    GroupAction,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetRemap

PKG_NAME: str = 'aether_gazebo'


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration('use_sim_time')
    pkg_share = get_package_share_directory(PKG_NAME)
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    aether_bringup_share = get_package_share_directory('aether_bringup')
    bridge_config_path = os.path.join(pkg_share, 'config', 'bridge.yaml')
    gz_spawn_model_launch_source = os.path.join(
        ros_gz_sim_share,
        'launch',
        'gz_spawn_model.launch.py',
    )
    world_path = os.path.join(pkg_share, 'worlds', 'obstacle.world')



    # gz_sim = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(
    #             ros_gz_sim_share,
    #             'launch',
    #             'gz_sim.launch.py',
    #         ),
    #     ),
    #     launch_arguments={
    #         'gz_args': f' -r {world_path}',
    #         'on_exit_shutdown': 'true',
    #     }.items(),
    # )
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'ros_gz_sim.launch.py'),
        ),
        launch_arguments={
            'world_sdf_file': world_path,
            'create_own_container': 'True',
            'container_name': 'ros_gz_sim_container',
            'use_composition': 'True',
            'bridge_name': 'ros_gz_bridge',
            'config_file': bridge_config_path,
        }.items(),
    )
    # GzServer(
    #     world_sdf_file=world_path,
    #     container_name='ros_gz_container',
    #     create_own_container='True',
    #     use_composition='True',
    # )

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

    # ros_gz_bridge = RosGzBridge(
    #     bridge_name='ros_gz_bridge',
    #     config_file=bridge_config_path,
    #     container_name='ros_gz_container',
    #     create_own_container='False',
    #     use_composition='True',
    # )

    aether_bringup_launch = GroupAction(
        [
            SetRemap('/odom', '/wheel_controller/odom'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(
                        aether_bringup_share,
                        'launch',
                        'aether_bringup_launch.py',
                    ),
                ),
                launch_arguments={
                    'sim_mode': 'True',
                }.items(),
            ),
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                name='use_sim_time',
                default_value='True',
                description='Flag to enable use_sim_time',
            ),
            # gz_sim,
            gz_client_cmd,
            # robot_state_publisher_node,
            gz_sim,
            spawn_entity,
            # robot_localization_node,
            # control_node,
            # delay_joint_state_broadcaster_after_robot_controller_spawner,
            aether_bringup_launch,
        ],
    )
