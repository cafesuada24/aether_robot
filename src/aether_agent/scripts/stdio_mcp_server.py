# Copyright (c) 2025 Cafesuada
# All rights reserved.

import asyncio
import sys
import threading
from typing import cast, override

import rclpy
import rclpy.executors
from mcp.server.fastmcp.server import FastMCP

from aether_agent.protocols.mcp.mcp_server_node import MCPServerNode


class StdioMCPServerNode(MCPServerNode):
    """An MCP server that use Standard Input/Output as transport protocol."""
    def __init__(
        self,
    ) -> None:
        super().__init__('stdio_mcp_server')

    @override
    def _declare_parameters(self) -> None:
        self.declare_parameter('server_name', 'mcp_server')
        # pass

    @override
    def _create_mcp(self) -> FastMCP:
        server_name = cast('str', self.get_parameter('server_name').get_parameter_value().string_value)
        return FastMCP(
            server_name,
            # self.__server_name,
        )

    @override
    async def run_server(self) -> None:
        assert self._mcp is not None
        await self._mcp.run_stdio_async()


node: StdioMCPServerNode
executor: rclpy.executors.SingleThreadedExecutor
spin_thread: threading.Thread

def setup() -> None:
    """Setup resources."""
    global node, executor, spin_thread
    rclpy.init()

    node = StdioMCPServerNode()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

def cleanup() -> None:
    """Clean up resources."""
    global node, executor, spin_thread
    if node:
        node.get_logger().info("MCP Server shutting down")
        executor.shutdown()
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()



async def main_loop() -> None:
    """Async main loop."""
    setup()

    try:
        await node.run_server()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        sys.stderr.write(f"FATAL MCP LOOP ERROR: {e}\n")
        sys.exit(1)
    finally:
        cleanup()

def main() -> None:
    """Node entry point."""
    asyncio.run(main_loop())

if __name__ == '__main__':
    main()
