import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    param_file = os.path.join(
        get_package_share_directory('articubot'),
        'param',
        'cam_params.yaml',
    )
    return LaunchDescription(
        [
            # Node(
            #     package='v4l2_camera',
            #     executable='v4l2_camera_node',
            #     output='screen',
            #     namespace='camera',
            #     parameters=[{
            #         'image_size': [1280, 480],
            #         'time_per_frame': [1, 6],
            #         'camera_frame_id': 'camera_optical_link'
            #     }],
            #     remappings=[("__ns", "/camera")],
            # ),
            Node(
                package='usb_cam',
                executable='usb_cam_node_exe',
                arguments=['--ros-args', '--params-file', param_file],
                remappings=[('__ns', '/camera')],
            ),
            Node(
                package='articubot',
                executable='usb_cam_preprocessor',
            ),
        ]
    )
