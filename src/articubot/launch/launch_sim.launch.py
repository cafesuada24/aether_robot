import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer

PKG_NAME: str = 'articubot'


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory(PKG_NAME)

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [os.path.join(pkg_share, 'launch', 'rsp.launch.py')],
        ),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    world_path = os.path.join(pkg_share, 'worlds', 'obstacle.world')
    gz_server = GzServer(
        world_sdf_file=world_path,
        container_name='ros_gz_name',
        create_own_container='True',
        use_composition='True',
    )

    # IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         [
    #             os.path.join(
    #                 get_package_share_directory('ros_gz_sim'),
    #                 'launch',
    #                 'gz_sim.launch.py',
    #             ),
    #         ],
    #     ),
    #     launch_arguments={
    #         'gz_args': ['-r -v2 ', world],
    #         'on_exit_shutdown': 'true',
    #     }.items(),
    # )

    # gzclient_cmd = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         [
    #             os.path.join(
    #                 get_package_share_directory('ros_gz_sim'),
    #                 'launch',
    #                 'gz_sim.launch.py',
    #             ),
    #         ]
    #     ),
    #     launch_arguments={
    #         'gz_args': ['-g -v2 '],
    #         'on_exit_shutdown': 'true',
    #     }.items(),
    # )

    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    gz_spawn_model_launch_source = os.path.join(
        ros_gz_sim_share,
        'launch',
        'gz_spawn_model.launch.py',
    )
    spawn_entity = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_spawn_model_launch_source),
        launch_arguments={
            'world': 'default',
            'topic': '/robot_description',
            'entity_name': 'articubot',
        }.items(),
        # package='ros_gz_sim',
        # executable='create',
        # arguments=[
        #     '-topic',
        #     'robot_description',
        #     '-entity',
        #     'my_bot',
        #     '-x',
        #     '0.0',
        #     '-y',
        #     '0.0',
        #     '-z',
        #     '2',
        # ],
        # output='screen',
    )

    bridge_params = os.path.join(pkg_share, 'config', 'bridge.yaml')
    bridge_cmd = RosGzBridge(
        bridge_name='ros_gz_bridge',
        config_file=bridge_params,
        container_name='ros_gz_container',
        create_own_container='False',
        use_composition='True',
    )

    # Node(
    #     package='ros_gz_bridge',
    #     executable='parameter_bridge',
    #     arguments=[
    #         '--ros-args',
    #         '-p',
    #         f'config_file:={bridge_params}',
    #     ],
    # )

    # robot_controller_spawner = Node(
    #     package='controller_manager',
    #     executable='spawner',
    #     # arguments=['four_wheel_controller', '--param-file', robot_controllers],
    #     arguments=['four_wheel_controller'],
    # )
    # joint_state_broadcaster_spawner = Node(
    #     package='controller_manager',
    #     executable='spawner',
    #     arguments=['joint_state_broadcaster'],
    # )
    #
    # delay_joint_state_broadcaster_after_robot_controller_spawner = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=spawn_entity,
    #         on_exit=[joint_state_broadcaster_spawner],
    #     ),
    # )
    #
    # delay_controller_spawner_after_joint_state_broadcaster = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=joint_state_broadcaster_spawner,
    #         on_exit=[robot_controller_spawner],
    #     ),
    # )

    return LaunchDescription(
        [
            # gzserver_cmd,
            # gzclient_cmd,
            gz_server,
            rsp,
            bridge_cmd,
            spawn_entity,
            # delay_joint_state_broadcaster_after_robot_controller_spawner,
            # delay_controller_spawner_after_joint_state_broadcaster,
        ],
    )
