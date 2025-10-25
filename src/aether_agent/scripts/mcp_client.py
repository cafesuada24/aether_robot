import asyncio
import os
import threading
from contextlib import AsyncExitStack
from typing import cast

import rclpy
import rclpy.executors
from dotenv import load_dotenv
from google import genai
from mcp import ClientSession, StdioServerParameters, stdio_client
from rclpy.node import Node

from aether_interfaces.srv import LLMPrompt

load_dotenv()


class MCPClient(Node):
    """A client that combine user prompt and MCP tools to query LLM, gathers results and returns it back to user."""

    def __init__(self) -> None:
        super().__init__('mcp_client')

        self.__declare_parameters()

        self.__session: ClientSession | None = None
        self.__exit_stack = AsyncExitStack()
        self.__genai_client = genai.Client(
            api_key=os.getenv('GOOGLE_GENAI_API_KEY'),
        )
        self.__chat_service = self.create_service(
            LLMPrompt,
            'chat',
            self.__chat_service_callback,
        )

        self.__aio_event_loop = asyncio.new_event_loop()
        self.__aio_thread = threading.Thread(
            target=self.__aio_event_loop.run_forever,
            daemon=True,
        )
        self.__aio_thread.start()
        future = asyncio.run_coroutine_threadsafe(
            self.connect_to_server(), self.__aio_event_loop
        )
        future.result(timeout=10.0)

    async def connect_to_server(self) -> None:
        """Connect to an MCP Server."""
        transport_protocol = (
            self.get_parameter('transport_protocol').get_parameter_value().string_value
        )
        transport_protocol = cast('str', transport_protocol)

        match transport_protocol:
            case 'stdio':
                await self.__connect_to_stdio_mcp_server()
            case _:
                raise ValueError(
                    "transport protocol must be in one of ['stdio', 'streamable_http']",
                )

    def cleanup(self) -> None:
        """Clean up resources."""
        self.get_logger().info('Cleaning up...')
        asyncio.run_coroutine_threadsafe(
            self.__exit_stack.aclose(), self.__aio_event_loop
        )
        self.get_logger().info('Stopping event loop...')
        if self.__aio_thread.is_alive():
            self.__aio_event_loop.call_soon_threadsafe(self.__aio_event_loop.stop)
            self.__aio_thread.join(timeout=5.0)

    def __chat_service_callback(
        self,
        request: LLMPrompt.Request,
        response: LLMPrompt.Response,
    ) -> LLMPrompt.Response:
        user_prompt = cast('str', request.prompt)
        self.get_logger().info(f'Received prompt: {user_prompt}')
        future = asyncio.run_coroutine_threadsafe(
            self.__process_query(user_prompt), self.__aio_event_loop
        )
        try:
            response.response = future.result(timeout=60.0)
        except Exception as e:
            self.get_logger().error(f'Error during query processing: {e}')

        return response

    async def __connect_to_stdio_mcp_server(self) -> None:
        server_script_path = (
            self.get_parameter('stdio.server_script_path')
            .get_parameter_value()
            .string_value
        )
        server_script_path = cast('str', server_script_path)

        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError('Server script must be a .py or.js file')

        server_params = StdioServerParameters(
            command='ros2',
            args=['run', 'aether_agent', 'stdio_mcp_server'],
            env=os.environ,
        )

        # async with (
        #     stdio_client(server_params) as (read_stream, write_stream),
        #     ClientSession(read_stream, write_stream) as session,
        # ):
        #     # self.__session = session
        #     await session.initialize()

        self.__stdio, self.__write = await self.__exit_stack.enter_async_context(
            stdio_client(server_params),
        )
        self.__session = await self.__exit_stack.enter_async_context(
            ClientSession(self.__stdio, self.__write),
        )

        await self.__session.initialize()

        response = await self.__session.list_tools()
        tools = response.tools
        self.get_logger().info(
            'Connected to server with tools: \n'
            + '\n\t - '.join([tool.name for tool in tools]),
        )

    async def __process_query(self, query: str) -> str:
        """Process query using Gemini and available tools."""
        self.get_logger().info('Received request, processing...')
        messages = [
            {
                'role': 'user',
                'content': query,
            },
        ]

        response = await self.__session.list_tools()
        available_tools = [
            {
                'name': tool.name,
                'description': tool.description,
                'input_schema': tool.inputSchema,
            }
            for tool in response.tools
        ]

        gemini_model = (
            self.get_parameter('gemini_model').get_parameter_value().string_value
        )
        gemini_model = cast('str', gemini_model)
        config = self.__session and genai.types.GenerateContentConfig(
            temperature=0,
            tools=[self.__session],
        )

        response = await self.__genai_client.aio.models.generate_content(
            model=gemini_model,
            contents=[
                genai.types.Content(
                    role=message['role'],
                    parts=[genai.types.Part.from_text(text=message['content'])],
                )
                for message in messages
            ],
            config=config,
        )

        self.get_logger().info(f'Done. Return message: {response.text}')

        return response.text or 'No response.'

    def __declare_parameters(self) -> None:
        self.declare_parameter('gemini_model', 'gemini-2.5-flash')
        self.declare_parameter('transport_protocol', 'stdio')
        self.declare_parameter(
            'stdio.server_script_path',
            # 'src/aether_agent/aether_agent/protocols/mcp/stdio_mcp_server.py',
            'src/aether_agent/scripts/stdio_mcp_server.py',
        )


def main() -> None:
    """Node entry point."""
    rclpy.init()
    node = MCPClient()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f'Error: {e}')
    finally:
        node.cleanup()
        if rclpy.ok():
            node.destroy_node()
        executor.shutdown()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
