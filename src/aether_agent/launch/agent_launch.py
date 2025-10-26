import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description import DeclareLaunchArgument
from launch.substitutions import (
    EqualsSubstitution,
    LaunchConfiguration,
)
from launch_ros.actions import Node

PKG_NAME: str = 'aether_agent'


def generate_launch_description() -> LaunchDescription:
    """Generate launch description that will launch agent."""
    pkg_share_dir = get_package_share_directory(PKG_NAME)
    transport_protocol = LaunchConfiguration('mcp_transport_protocol')
    params_file = LaunchConfiguration('params_file')

    declare_transport_protocol_cmd = DeclareLaunchArgument(
        'mcp_transport_protocol',
        default_value='stdio',
        description='MCP connection transport protocol. Choose None to turn MCP off.',
        choices=['stdio', 'streamable_http', 'none'],
    )
    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        description='agent launch parameters',
        default_value=os.path.join(pkg_share_dir, 'params', 'agent.yaml'),
    )
    use_streamablehttp = EqualsSubstitution(transport_protocol, 'streamable_http')
    start_server = GroupAction(
        actions=[
            Node(
                package=PKG_NAME,
                executable='llm_client',
                parameters=[
                    params_file,
                    {
                        'transport_protocol': transport_protocol,
                    },
                ],
                condition=UnlessCondition(use_streamablehttp),
            ),
            Node(
                package=PKG_NAME,
                executable='streamable_http_mcp_server',
                parameters=[params_file],
                condition=IfCondition(use_streamablehttp),
            ),
            TimerAction(
                actions=[
                    Node(
                        package=PKG_NAME,
                        executable='llm_client',
                        parameters=[
                            params_file,
                            {
                                'transport_protocol': transport_protocol,
                            },
                        ],
                    ),
                ],
                period=3.0,
                condition=IfCondition(use_streamablehttp),
            ),
        ],
    )
    ld = LaunchDescription()

    ld.add_action(declare_transport_protocol_cmd)
    ld.add_action(declare_params_file_cmd)

    ld.add_action(start_server)

    return ld
