import asyncio
import math
from abc import abstractmethod
from uuid import uuid4

from chromadb import Collection
from geometry_msgs.msg import Vector3
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.types import TextContent
from nav2_msgs.action import NavigateToPose
from rclpy.action.client import ActionClient
from rclpy.clock import Clock
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.task import Future
from tf2_ros import Time
from tf2_ros.buffer import Buffer


class NavigationMixin:

    _tf_buffer: Buffer
    _collection: Collection
    _mcp: FastMCP
    _nav_to_pose_client: ActionClient
    _loop: asyncio.AbstractEventLoop
    # def __init__(self) -> None:

    def _load_tools(self) -> None:
        assert self._mcp is not None
        self._mcp.add_tool(self.get_locations)
        self._mcp.add_tool(self.where_am_i)
        self._mcp.add_tool(self.save_point)
        self._mcp.add_tool(self.navigate_to)
        # self.__mcp.add_tool(self.move)

    @abstractmethod
    def get_logger(self) -> RcutilsLogger:
        raise NotImplementedError

    @abstractmethod
    def get_clock(self) -> Clock:
        raise NotImplementedError

    def get_current_pose(self) -> Vector3:
        """Returns 2D position from map frame."""
        assert self._tf_buffer is not None
        trans = self._tf_buffer.lookup_transform('map', 'base_footprint', Time())
        return trans.transform.translation  # pyright: ignore

    def distance(self, p1: Vector3, p2: Vector3) -> float:
        """Get distance between two 3D vector."""
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2)  # pyright: ignore

    # @mcp.tool()
    def get_locations(self) -> list[tuple[str, tuple[float, float]]]:
        """Get the saved waypoints."""
        assert self._collection is not None
        get_results = self._collection.get()
        if not get_results['ids']:
            return []

        return [
            (doc, (meta['x'], meta['y']))
            for doc, meta in zip(
                get_results['documents'] or [],
                get_results['metadatas'] or [],
                strict=True,
            )
            if isinstance(meta['x'], float) and isinstance(meta['y'], float)
        ]

    # @mcp.tool()
    def where_am_i(self) -> tuple[float, float] | str:
        """Return the current position of robot by the location's label or 3D position if not labeled."""
        assert self._collection is not None
        loc = self.get_current_pose()
        all_points = self._collection.get()
        if all_points['documents'] is None or all_points['metadatas'] is None:
            return [loc.x, loc.y]  # pyright: ignore
        for doc, meta in zip(
            all_points['documents'],
            all_points['metadatas'],
            strict=True,
        ):
            assert isinstance(meta['x'], float)
            assert isinstance(meta['y'], float)
            if self.distance(loc, Vector3(x=meta['x'], y=meta['y'], z=0.0)) <= 0.5:
                return doc
        return [loc.x, loc.y]  # pyright: ignore

    # @mcp.tool()
    def save_point(self, name: str) -> None:
        """Save the current position as name."""
        assert self._collection is not None
        pose = self.get_current_pose()
        # self.__points[name] = pose
        # await self.__destination_collection.upsert(await self.__create_destination(name, pose[0], pose[1]))
        self._collection.add(
            ids=[str(uuid4())],
            documents=[name],
            metadatas=[{'x': pose.x, 'y': pose.y}],
        )
        self.get_logger().info(  # pyright: ignore
            f'Point {name} saved at: {{x: {pose.x}, y: {pose.y}}}',
        )

    def navigate_to_pose_feedback_callback(
        self,
        feedback_msg: NavigateToPose.Feedback,
        ctx: Context,  # pyright: ignore
    ) -> None:
        asyncio.run_coroutine_threadsafe(
            ctx.report_progress(feedback_msg.feedback.distance_remaining), self._loop
        )

    def navigate_to_pose_result_callback(
        self,
        future: Future,
        ctx: Context,  # pyright: ignore
    ):
        result = future.result().result
        status = future.result().status

        if status == 4:  # GoalStatus.STATUS_SUCCEEDED
            asyncio.run_coroutine_threadsafe(
                ctx.info('Navigation Goal Succeeded!'), self._loop
            )
            self.get_logger().info('Navigation Goal Succeeded!')
        else:
            asyncio.run_coroutine_threadsafe(
                ctx.warning(f'Navigation Goal Failed with status: {status}'),
                self._loop,
            )
            self.get_logger().warn(f'Navigation Goal Failed with status: {status}')

    def navigate_to_pose_response_callback(
        self,
        future: Future,
        ctx: Context,  # pyright: ignore
    ) -> None:
        goal_handle = future.result()

        if not goal_handle.accepted:
            asyncio.run_coroutine_threadsafe(
                ctx.error('Goal rejected by server.'), self._loop
            )
            self.get_logger().info('Goal rejected by server.')
            return
        self.get_logger().info('Goal accepted by server. Waiting for result...')
        asyncio.run_coroutine_threadsafe(
            ctx.info('Goal accepted by server. Waiting for result...'), self._loop
        )

        result = goal_handle.get_result_async()

        result.add_done_callback(lambda future: self.navigate_to_pose_result_callback(future, ctx))

    # @mcp.tool()
    async def navigate_to(
        self,
        name: str,
        ctx: Context,  # pyright: ignore
    ) -> TextContent:
        """Navigate to a saved point.

        Args:
            name (str): name of the destination point.

        Returns:
            TextContent: a text message containing action result.
        """
        query_results = self._collection.query(
            query_texts=[name],
            n_results=1,
            include=['metadatas', 'distances'],
        )
        if (
            query_results['distances'] is None
            or len(query_results['distances'][0]) == 0
        ):
            self.get_logger().info(f'No destination found for {name}')  # pyright: ignore
            return TextContent(type='text', text='Destination not found')

        if query_results['distances'][0][0] > 1.0:
            self.get_logger().info(  # pyright: ignore
                f"No destination found that's closed to {name}, closest is: {query_results['distances'][0][0]:.2f}",
            )  # pyright: ignore
            return TextContent(type='text', text='Destination not found')

        assert query_results['metadatas'] is not None

        dest_point = (
            query_results['metadatas'][0][0]['x'],
            query_results['metadatas'][0][0]['y'],
        )

        goal_pose = NavigateToPose.Goal()
        goal_pose.pose.header.frame_id = 'map'
        goal_pose.pose.header.stamp = self.get_clock().now().to_msg()

        goal_pose.pose.pose.position.x = dest_point[0]
        goal_pose.pose.pose.position.y = dest_point[1]
        goal_pose.pose.pose.position.z = 0.0

        goal_pose.pose.pose.orientation.x = 0.0
        goal_pose.pose.pose.orientation.y = 0.0
        goal_pose.pose.pose.orientation.z = 0.0
        goal_pose.pose.pose.orientation.w = 1.0  # identity quaternion: no rotation

        self.get_logger().info('Waiting for action server...')
        # Wait for the action server to be available
        self._nav_to_pose_client.wait_for_server()

        self.get_logger().info(
            f'Sending goal to ({dest_point[0]:.2f}, {dest_point[1]:.2f})'
        )


        future = self._nav_to_pose_client.send_goal_async(
            goal_pose,
            feedback_callback=lambda feedback: self.navigate_to_pose_feedback_callback(feedback, ctx),
        )
        future.add_done_callback(lambda fut: self.navigate_to_pose_response_callback(fut, ctx))

        while not future.done() or not future.result().get_result_async().done():
            await asyncio.sleep(1e-4)


        return TextContent(type='text', text=f'Goal executing: {name}')

    # @mcp.tool()
    # def move(
    #     self,
    #     direction: Annotated[str, Literal['l', 'r', 'f', 'b']],
    #     speed: Annotated[float, 'values between 0.0 and 1.0'] = 0.5,
    # ) -> bool:
    #     """Move the robot in a specified direction.
    #
    #     Args:
    #         direction (str): direction to move
    #             left (l), right (r), f (forward), b (backward)
    #         speed (float): speed to move, must be a float between (0.0 and 1.0). (Defaut: 0.5)
    #
    #     Returns:
    #         boolean - whether the command is sent to robot driver
    #     """
    #     if isinstance(speed, str):
    #         try:
    #             speed = int(speed)
    #         except Exception:
    #             self.get_logger().info(f'Invalid speed: {speed}')
    #             return False
    #     if speed < 0.0 or speed > 1.0:
    #         self.get_logger().info(f'Invalid speed: {speed}')
    #         return False
    #     msg_to_pub = TwistStamped()
    #     msg_to_pub.header.stamp = self.get_clock().now().to_msg()
    #     match direction:
    #         case 'f':
    #             msg_to_pub.twist.linear.x = speed
    #         case 'b':
    #             msg_to_pub.twist.linear.x = -speed
    #         case 'l':
    #             msg_to_pub.twist.angular.z = speed
    #         case 'r':
    #             msg_to_pub.twist.angular.z = -speed
    #         case _:
    #             self.get_logger().info(f'Invalid direction: {direction}')
    #             return False
    #
    #     self.__cmd_vel_publisher.publish(msg_to_pub)
    #     return True
