import contextlib
import sys

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from rclpy.task import Future
from std_msgs.msg import String

from aether_interfaces.srv import LLMPrompt


class LLMServiceClient(Node):
    def __init__(self) -> None:
        super().__init__('func_calling_client')

        srv_callback_group = ReentrantCallbackGroup()
        self.__client = self.create_client(
            LLMPrompt,
            'prompt',
            callback_group=srv_callback_group,
        )

        while not self.__client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')

        self.__subscriber = self.create_subscription(
            String,
            'prompt',
            self.call_service,
            10,
            callback_group=srv_callback_group,
        )

    def call_service(self, msg: str) -> None:
        request = LLMPrompt.Request()
        request.prompt = msg
        future = self.__client.call_async(request)
        future.add_done_callback(self.process_response) # pyright: ignore
        # result: LLMPrompt.Response = await future

    def process_response(self, future: Future) -> None:
        result: LLMPrompt.Response = future.result() # pyright: ignore
        self.get_logger().info(f'Bot > {result.response}')

def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)

    node = LLMServiceClient()

    try:
        rclpy.spin_once(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()



if __name__ == '__main__':
    main()
