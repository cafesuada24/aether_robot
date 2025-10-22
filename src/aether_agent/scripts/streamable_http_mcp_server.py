# type: ignore
import asyncio
from typing import override

import rclpy
from mcp.server.fastmcp.server import FastMCP
from rclpy.node import Node

from aether_agent.protocols.mcp.mcp_server_node import MCPServerNode


class StreamableHTTPMCPServerNode(MCPServerNode):
    def __init__(self) -> None:
        super().__init__('mcp_server')

    @override
    def _declare_parameters(self) -> None:
        self.declare_parameter('server_name', 'mcp_server')
        self.declare_parameter('host', '127.0.0.1')
        self.declare_parameter('port', 8000)

    @override
    def _create_mcp(self) -> FastMCP:
        return FastMCP(
            self.get_parameter('server_name').get_parameter_value().string_value,
            host=self.get_parameter('host').get_parameter_value().string_value,
            port=self.get_parameter('port').get_parameter_value().integer_value,
        )

    @override
    async def run_server(self) -> None:
        assert self._mcp is not None
        await self._mcp.run_streamable_http_async()


async def ros_loop(node: Node) -> None:
    """Rclpy main loop."""
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0)
        await asyncio.sleep(1e-4)


async def amain() -> None:
    """Main node loop."""
    node = StreamableHTTPMCPServerNode()
    node.get_logger().info('Node started')  # pyright: ignore
    # node.create_subscription(String, 'test', test, 10)

    async with asyncio.TaskGroup() as tg:
        mcp_loop_task = tg.create_task(node.run_server())
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
