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
    pkg_share = get_package_share_directory(PKG_NAME)
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    aether_bringup_share = get_package_share_directory('aether_bringup')
    bridge_config_path = os.path.join(pkg_share, 'config', 'bridge.yaml')
    gz_spawn_model_launch_source = os.path.join(
        ros_gz_sim_share,
        'launch',
        'gz_spawn_model.launch.py',
    )
    world_description_default = os.path.join(pkg_share, 'worlds', 'house.world')

    # use_sim_time = LaunchConfiguration('use_sim_time')
    world_sdf_file = LaunchConfiguration('world_sdf_file')
    slam = LaunchConfiguration('slam')




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
            'world_sdf_file': world_sdf_file,
            'create_own_container': 'True',
            'container_name': 'ros_gz_sim_container',
            'use_composition': 'True',
            'bridge_name': 'ros_gz_bridge',
            'config_file': bridge_config_path,
        }.items(),
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
                    'slam': slam,
                }.items(),
            ),
        ],
    )

    return LaunchDescription(
        [
            # DeclareLaunchArgument(
            #     name='use_sim_time',
            #     default_value='True',
            #     description='Flag to enable use_sim_time',
            # ),
            DeclareLaunchArgument(
                name='world_sdf_file',
                default_value=world_description_default,
                description='Gazebo world sdf file',
            ),

            DeclareLaunchArgument(
                name='slam',
                default_value='False',
                description='Use SLAM mode',
                choices=['False', 'True'],
            ),

            gz_client_cmd,
            gz_sim,
            spawn_entity,
            aether_bringup_launch,
        ],
    )
