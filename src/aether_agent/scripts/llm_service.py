import os

import chromadb
import rclpy
from dotenv import load_dotenv
from geometry_msgs.msg import Point, PoseStamped, TwistStamped
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener

from aether_agent.light_plugins import LightsPlugin
from aether_agent.llm.gemini_model import GeminiModel
from aether_agent.plugins.navigation_plugins import NavigationPlugin
from aether_interfaces.msg._waypoint import Waypoint
from aether_interfaces.srv import GetWaypoints, LLMPrompt


class LLMService(Node):
    def __init__(self) -> None:
        super().__init__('llm_service')

        load_dotenv()

        self.__tf_buffer = Buffer()
        self.__tf_listener = TransformListener(self.__tf_buffer, self)
        self.__cmd_vel_publisher = self.create_publisher(TwistStamped, '/cmd_vel', 10)  # pyright: ignore
        self.__goal_pose_publisher = self.create_publisher(  # pyright: ignore
            PoseStamped, '/goal_pose', 10
        )  # pyright: ignore
        self.__srv_callback_group = MutuallyExclusiveCallbackGroup()
        self.__prompt_service = self.create_service(  # pyright: ignore
            LLMPrompt,
            'prompt',
            self.prompt_callback,
            callback_group=self.__srv_callback_group,
        )
        self.__dest_service = self.create_service(  # pyright: ignore
            GetWaypoints,
            'get_waypoints',
            self.__get_waypoints_callback,
            callback_group=self.__srv_callback_group,
        )

        # self.__queue = Queue[]
        # self.__executor = executor
        self.__llm = GeminiModel(
            api_key=os.environ['GOOGLE_API_KEY'],
            gemini_model_id='gemini-2.5-flash',
            logger=self.get_logger(),
        )

        self.__llm.kernel.add_plugin(
            LightsPlugin(),
            plugin_name='Lights',
        )

        self.__db_client = chromadb.PersistentClient()
        self.__nav_plugin = NavigationPlugin(
            self.__db_client,
            self.get_clock(),
            self.__cmd_vel_publisher,
            self.__goal_pose_publisher,
            self.__tf_buffer,
            logger=self.get_logger(),
        )
        self.__llm.kernel.add_plugin(
            self.__nav_plugin,
            plugin_name='Navigation',
        )

    def __get_waypoints_callback(
        self, request: GetWaypoints.Request, response: GetWaypoints.Response
    ) -> GetWaypoints.Response:
        locs = self.__nav_plugin.get_locations()
        response.waypoints = [
            Waypoint(name=name, coordinate=Point(x=x, y=y, z=0.0))
            for name, (x, y) in locs
        ]
        return response

    def prompt_callback(
        self,
        request: LLMPrompt.Request,
        response: LLMPrompt.Response,
    ) -> LLMPrompt.Response:
        if not isinstance(request.prompt, str):  # pyright: ignore
            self.get_logger().debug('Invalid user input, expected a non empty string.')  # pyright: ignore
            response.response = 'Prompt can not be empty'
            return response

        response.response = self.__llm.infer(request.prompt)

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
