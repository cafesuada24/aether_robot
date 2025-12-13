# Copyright (c) 2025 Cafesuada
# All rights reserved.

import asyncio
from threading import Thread
from typing import override

import rclpy
from mcp.server.fastmcp.server import FastMCP

from aether_agent.protocols.mcp.mcp_server_node import MCPServerNode


class StreamableHTTPMCPServerNode(MCPServerNode):
    def __init__(self) -> None:
        self.__aio_thread: Thread
        super().__init__('streamablehttp_mcp_server')

        asyncio.run_coroutine_threadsafe(
            self.run_server(),
            self._loop,
        )
    @override
    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        new_event_loop = asyncio.new_event_loop()
        self.__aio_thread = Thread(
            target=new_event_loop.run_forever,
            daemon=True,
        )
        self.__aio_thread.start()
        return new_event_loop


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

    @override
    def destroy_node(self) -> None:
        self.get_logger().info('Stopping event loop...')
        for task in asyncio.all_tasks(self._loop):
            task.cancel()
        if self.__aio_thread.is_alive():
            self._loop.call_soon_threadsafe(self._loop.close)
            self.__aio_thread.join()
        return super().destroy_node()

def main() -> None:
    """Entry point for node."""
    rclpy.init()
    node = StreamableHTTPMCPServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()
    # ros_loop_task = asyncio.create_task(ros_loop())
    # main_loop_task = asyncio.create_task(main_loop())
    # await asyncio.wait([ros_loop_task, main_loop_task])
    # asyncio.run(future)
    # asyncio.get_event_loop().run_until_complete(future)
if __name__ == '__main__':
    main()
