from typing import Annotated, Literal

from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.clock import Clock
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.publisher import Publisher
from rclpy.time import Time
from semantic_kernel.functions import kernel_function
from tf2_ros.buffer import Buffer


class NavigationPlugin:
    def __init__(
        self,
        clock: Clock,
        logger: RcutilsLogger,
        publisher: Publisher,
        goal_pose_publisher: Publisher,
        tf_buffer: Buffer,
    ) -> None:
        self.__logger = logger
        self.__clock = clock
        self.__publisher = publisher
        self.__goal_pose_publisher = goal_pose_publisher
        self.__tf_buffer = tf_buffer
        self.__points: dict[str, tuple[float, float, float]] = {
            'starting_point': (0.0, 0.0, 0.0),
        }

    def get_current_pose(self) -> tuple[float, float, float]:
        trans = self.__tf_buffer.lookup_transform('map', 'base_footprint', Time())
        return ( # pyright: ignore
            trans.transform.translation.x,
            trans.transform.translation.y,
            trans.transform.translation.z,
        )

    @kernel_function(name='save_point')
    def save_point(self, name: str) -> None:
        """Save the current position as name."""
        pose = self.get_current_pose()
        self.__points[name] = pose
        self.__logger.info(f'Point {name} saved at: {{x: {pose[0]}, y: {pose[1]}, z: {pose[2]}}}')

    @kernel_function(name='navigate_to')
    def navigate_to(self, name: str) -> bool:
        """Navigate to a saved point.

        Args:
            name (str): name of the destination point.

        Returns:
            bool: true if the goal command is sent,
                false if the destination doesn't exist or other errors.
        """
        if name not in self.__points:
            self.__logger.info(f"destination {name} doesn't exist")
            return False
        dest_point = self.__points[name]
        self.__logger.info(f'Moving to {name} at: {{x: {dest_point[0]}, y: {dest_point[1]}, z: {dest_point[2]}}}')

        dest_pose = PoseStamped()
        dest_pose.header.frame_id = 'map'
        dest_pose.header.stamp = self.__clock.now().to_msg()

        dest_pose.pose.position.x = dest_point[0]
        dest_pose.pose.position.y = dest_point[1]
        dest_pose.pose.position.z = dest_point[2]

        self.__goal_pose_publisher.publish(dest_pose)
        return True

    @kernel_function(name='move')
    def move(
        self,
        direction: Annotated[str, Literal['l', 'r', 'f', 'b']],
        speed: Annotated[float, 'values between 0.0 and 1.0'] = 0.5,
    ) -> bool:
        """Move the robot in a specified direction.

        Args:
            direction (str): direction to move
                left (l), right (r), f (forward), b (backward)
            speed (float): speed to move, must be a float between (0.0 and 1.0). (Defaut: 0.5)

        Returns:
            boolean - whether the command is sent to robot driver
        """
        if isinstance(speed, str):
            try:
                speed = int(speed)
            except:
                self.__logger.info(f'Invalid speed: {speed}')
                return False
        if speed < 0.0 or speed > 1.0:
            self.__logger.info(f'Invalid speed: {speed}')
            return False
        msg_to_pub = TwistStamped()
        msg_to_pub.header.stamp = self.__clock.now().to_msg()
        if direction == 'f':
            msg_to_pub.twist.linear.x = speed
        elif direction ==  'b':
            msg_to_pub.twist.linear.x = -speed
        elif direction == 'l':
            msg_to_pub.twist.angular.z = speed
        elif direction == 'r':
            msg_to_pub.twist.angular.z = -speed
        else:
            self.__logger.info(f'Invalid direction: {direction}')
            return False

        self.__publisher.publish(msg_to_pub)
        return True
