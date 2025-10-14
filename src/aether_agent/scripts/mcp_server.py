# type: ignore
import asyncio
import math
from functools import partial
from typing import Annotated, Literal, override
from uuid import uuid4

import chromadb
import rclpy
from geometry_msgs.msg import TwistStamped, Vector3
from mcp.server.fastmcp.server import Context
from mcp.types import TextContent
from nav2_msgs.action import NavigateToPose
from rclpy.action.client import ActionClient
from rclpy.node import Node
from rclpy.task import Future
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener

from aether_agent.protocols.mcp import mcp


class MCPServerNode(Node):
    def __init__(self) -> None:
        super().__init__('mcp_node')

        self.__tf_buffer = Buffer()
        self.__tf_listener = TransformListener(self.__tf_buffer, self)

        self.__db_client = chromadb.PersistentClient()
        self.__collection = self.__db_client.get_or_create_collection(
            name='locations',
            metadata={
                'description': 'This collection saves destinations marked by users',
            },  # pyright: ignore
            configuration={
                'hnsw': {
                    'space': 'cosine',
                },
            },
        )
        self.__nav_to_pose_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose',
        )

        self.__cmd_vel_publisher = self.create_publisher(TwistStamped, '/cmd_vel', 10)  # pyright: ignore

        self.__loop = asyncio.get_running_loop()


        mcp.add_tool(self.get_locations)
        mcp.add_tool(self.where_am_i)
        mcp.add_tool(self.save_point)
        mcp.add_tool(self.navigate_to)
        mcp.add_tool(self.move)

    def get_current_pose(self) -> Vector3:
        """Returns 2D position from map frame."""
        trans = self.__tf_buffer.lookup_transform('map', 'base_footprint', Time())
        return trans.transform.translation  # pyright: ignore

    def distance(self, p1: Vector3, p2: Vector3) -> float:
        """Get distance between two 3D vector."""
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2)  # pyright: ignore

    # @mcp.tool()
    def get_locations(self) -> list[tuple[str, tuple[float, float]]]:
        """Get the saved waypoints."""
        get_results = self.__collection.get()
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
        loc = self.get_current_pose()
        all_points = self.__collection.get()
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
        pose = self.get_current_pose()
        # self.__points[name] = pose
        # await self.__destination_collection.upsert(await self.__create_destination(name, pose[0], pose[1]))
        self.__collection.add(
            ids=[str(uuid4())],
            documents=[name],
            metadatas=[{'x': pose.x, 'y': pose.y}],
        )
        self.get_logger().info(  # pyright: ignore
            f'Point {name} saved at: {{x: {pose.x}, y: {pose.y}}}',
        )

    def navigate_to_pose_feedback_callback(
        self,
        ctx: Context,  # pyright: ignore
        feedback_msg: NavigateToPose.Feedback,
    ) -> None:
        asyncio.run_coroutine_threadsafe(ctx.report_progress(feedback_msg.feedback.distance_remaining), self.__loop)

    def navigate_to_pose_result_callback(
        self,
        ctx: Context,  # pyright: ignore
        future: Future,
    ):
        result = future.result().result
        status = future.result().status

        if status == 4: # GoalStatus.STATUS_SUCCEEDED
            asyncio.run_coroutine_threadsafe(ctx.info('Navigation Goal Succeeded!'), self.__loop)
            self.get_logger().info('Navigation Goal Succeeded!')
        else:
            asyncio.run_coroutine_threadsafe(ctx.warning(f'Navigation Goal Failed with status: {status}'), self.__loop)
            self.get_logger().warn(f'Navigation Goal Failed with status: {status}')

    def navigate_to_pose_response_callback(
        self,
        ctx: Context,  # pyright: ignore
        future: Future,
    ) -> None:
        goal_handle = future.result()

        if not goal_handle.accepted:
            asyncio.run_coroutine_threadsafe(ctx.error('Goal rejected by server.'), self.__loop)
            self.get_logger().info('Goal rejected by server.')
            return
        self.get_logger().info('Goal accepted by server. Waiting for result...')
        asyncio.run_coroutine_threadsafe(ctx.info('Goal accepted by server. Waiting for result...'), self.__loop)

        result = goal_handle.get_result_async()

        result_callback = partial(self.navigate_to_pose_result_callback, ctx)
        result.add_done_callback(result_callback)


    # @mcp.tool()
    async def navigate_to(
        self,
        name: str,
        ctx: Context, # pyright: ignore
    ) -> TextContent:
        """Navigate to a saved point.

        Args:
            name (str): name of the destination point.

        Returns:
            bool: true if the goal command is sent,
                false if the destination doesn't exist or other errors.
        """
        query_results = self.__collection.query(
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
        self.__nav_to_pose_client.wait_for_server()

        self.get_logger().info(f'Sending goal to ({dest_point[0]:.2f}, {dest_point[1]:.2f})')

        feedback_callback = partial(self.navigate_to_pose_feedback_callback, ctx)

        future = self.__nav_to_pose_client.send_goal_async(
            goal_pose,
            feedback_callback=feedback_callback,
        )

        response_callback = partial(self.navigate_to_pose_response_callback, ctx)
        future.add_done_callback(response_callback)

        while not future.done():
            await asyncio.sleep(1e-4)

        while not future.result().get_result_async().done():
            await asyncio.sleep(1e-4)

        return TextContent(type='text', text=f'Goal executing: {name}')

    # @mcp.tool()
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
            except Exception:
                self.get_logger().info(f'Invalid speed: {speed}')
                return False
        if speed < 0.0 or speed > 1.0:
            self.get_logger().info(f'Invalid speed: {speed}')
            return False
        msg_to_pub = TwistStamped()
        msg_to_pub.header.stamp = self.get_clock().now().to_msg()
        match direction:
            case 'f':
                msg_to_pub.twist.linear.x = speed
            case 'b':
                msg_to_pub.twist.linear.x = -speed
            case 'l':
                msg_to_pub.twist.angular.z = speed
            case 'r':
                msg_to_pub.twist.angular.z = -speed
            case _:
                self.get_logger().info(f'Invalid direction: {direction}')
                return False

        self.__cmd_vel_publisher.publish(msg_to_pub)
        return True


async def ros_loop(node: Node) -> None:
    """Rclpy main loop."""
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0)
        await asyncio.sleep(1e-4)

async def amain() -> None:
    """Main node loop."""
    node = MCPServerNode()
    node.get_logger().info('Node started')  # pyright: ignore
    # node.create_subscription(String, 'test', test, 10)

    async with asyncio.TaskGroup() as tg:
        mcp_loop_task = tg.create_task(mcp.run_streamable_http_async())
        ros_loop_task = tg.create_task(ros_loop(node))


def main() -> None:
    """Entry point for node."""
    rclpy.init()
    try:
        asyncio.run(amain())
    finally:
        rclpy.shutdown()
    # ros_loop_task = asyncio.create_task(ros_loop())
    # main_loop_task = asyncio.create_task(main_loop())
    # await asyncio.wait([ros_loop_task, main_loop_task])
    # asyncio.run(future)
    # asyncio.get_event_loop().run_until_complete(future)
