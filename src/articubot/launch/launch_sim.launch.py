import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

PKG_NAME: str = "articubot"


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory(PKG_NAME)

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [os.path.join(pkg_share, "launch", "rsp.launch.py")]
        ),
        launch_arguments={"use_sim_time": "true"}.items(),
    )

    world = os.path.join(pkg_share, "worlds", "empty.world")
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    get_package_share_directory("ros_gz_sim"),
                    "launch",
                    "gz_sim.launch.py",
                ),
            ]
        ),
        launch_arguments={"gz_args": world}.items(),
    )

    spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic",
            "robot_description",
            "-entity",
            "my_bot",
        ],
        output="screen",
    )

    bridge_params = os.path.join(pkg_share, "config", "bridge.yaml")
    bridge_cmd = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "--ros-args",
            "-p",
            f"config_file:={bridge_params}",
        ],
    )

    lidar_static_tf_publishing = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=[
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "base_footprint",
            "robot/base_footprint/lidar",
        ],
    )

    return LaunchDescription(
        [
            rsp,
            gazebo,
            spawn_entity,
            bridge_cmd,
            lidar_static_tf_publishing,
        ]
    )
