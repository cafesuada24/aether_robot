import asyncio
from collections.abc import Buffer
import os

from geometry_msgs.msg import PoseStamped, TwistStamped
import rclpy
from dotenv import load_dotenv
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import Executor, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.task import Future
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.google.google_ai import (
    GoogleAIChatCompletion,
    GoogleAIPromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions import KernelArguments

from aether_interfaces.srv import LLMPrompt

from .light_plugins import LightsPlugin
from .plugins.navigation_plugins import NavigationPlugin
from tf2_ros import Buffer, TransformListener


class LLMService(Node):
    def __init__(self) -> None:
        super().__init__('func_calling_test')

        load_dotenv()

        self.__tf_buffer = Buffer()
        self.__tf_listener = TransformListener(self.__tf_buffer, self)
        self.__cmd_vel_publisher = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.__goal_pose_publisher = self.create_publisher(PoseStamped, '/goal_pose', 10)

        # self.__queue = Queue[]
        # self.__executor = executor
        self.__kernel = Kernel()

        self.__chat_completion_service = GoogleAIChatCompletion(
            api_key=os.environ['GOOGLE_API_KEY'],
            gemini_model_id='gemini-2.5-flash',
        )

        self.__kernel.add_service(self.__chat_completion_service)

        self.__kernel.add_plugin(
            LightsPlugin(),
            plugin_name='Lights',
        )
        self.__kernel.add_plugin(
            NavigationPlugin(
                self.get_clock(),
                self.get_logger(),
                self.__cmd_vel_publisher,
                self.__goal_pose_publisher,
                self.__tf_buffer,
            ),
            plugin_name='Navigation',
        )

        self.__execution_settings = GoogleAIPromptExecutionSettings()
        self.__execution_settings.function_choice_behavior = (
            FunctionChoiceBehavior.Auto()
        )
        self.__history = ChatHistory()

        self.__srv_callback_group = MutuallyExclusiveCallbackGroup()
        self.__llm_service = self.create_service(
            LLMPrompt,
            'prompt',
            self.prompt_callback,
            callback_group=self.__srv_callback_group,
        )
        # self.__prompt_subscriber = self.create_subscription(String, 'prompt', self.prompt_callback, 10)

    def prompt_callback(
        self,
        request: LLMPrompt.Request,
        response: LLMPrompt.Response,
    ) -> LLMPrompt.Response:
        # response.response = "Result"
        # return response
        if not isinstance(request.prompt, str):  # pyright: ignore
            response.response = 'Prompt can not be empty'
            return response
        self.__history.add_user_message(request.prompt)
        try:
            corou = self.__chat_completion_service.get_chat_message_content(
                chat_history=self.__history,
                settings=self.__execution_settings,
                kernel=self.__kernel,
                arguments=KernelArguments(),
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(corou)
            loop.close()


            if result is None:
                response.response = 'Failed to receive AI response'
            else:
                self.__history.add_message(result)
                response.response = str(result)
        except Exception as e:
            self.get_logger().error(str(e))
            response.response = (
                f'An error occured while processing your request: {str(e)}'
            )

        return response


def main(args: list[str] | None = None) -> None:
    """Main entry."""
    rclpy.init(args=args)

    node = LLMService()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
