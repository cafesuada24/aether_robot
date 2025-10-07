import math
from typing import Annotated, Literal
from uuid import uuid4

from chromadb.api import ClientAPI
from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.clock import Clock
from rclpy.impl.rcutils_logger import RcutilsLogger
from rclpy.publisher import Publisher
from rclpy.time import Time
from semantic_kernel.functions import kernel_function
from tf2_ros.buffer import Buffer

# @vectorstoremodel
# @dataclass
# class Destination:
#     name: Annotated[str, VectorStoreField('data')]
#     x: Annotated[float, VectorStoreField('data')]
#     y: Annotated[float, VectorStoreField('data')]
#     name_embedding: Annotated[
#         list[float],
#         VectorStoreField(
#             'vector',
#             dimensions=4,
#             distance_function=DistanceFunction.COSINE_DISTANCE,
#             index_kind=IndexKind.HNSW,
#         ),
#     ]
#     dest_id: Annotated[str, VectorStoreField('key')] = field(
#         default_factory=lambda: str(uuid4())
#     )


class NavigationPlugin:
    def __init__(
        self,
        db_client: ClientAPI,
        clock: Clock,
        publisher: Publisher,
        goal_pose_publisher: Publisher,
        tf_buffer: Buffer,
        *,
        logger: RcutilsLogger,
    ) -> None:
        self.__logger = logger
        self.__clock = clock
        self.__publisher = publisher
        self.__goal_pose_publisher = goal_pose_publisher
        self.__tf_buffer = tf_buffer

        self.__db_client = db_client
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

        # self.__destination_collection: ChromaCollection[str, Destination] = ChromaCollection(
        #     record_type=Destination,
        #     collection_name="destinations",
        #     persist_directory="data",
        # )

        # await self.__destination_collection.ensure_collection_exists()

    def get_current_pose(self) -> tuple[float, float]:
        """Returns 2D position from map frame."""
        trans = self.__tf_buffer.lookup_transform('map', 'base_footprint', Time())
        return (  # pyright: ignore
            trans.transform.translation.x,
            trans.transform.translation.y,
        )

    def distance_2d(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def get_locations(self) -> list[str]:
        """Return saved locations."""
        return self.__collection.get()['documents'] or []

    @kernel_function(name='where_am_i')
    def where_am_i(self) -> tuple[float, float] | str:
        """Return the current position of robot the label or 3D position."""
        loc = self.get_current_pose()
        all_points = self.__collection.get()
        if all_points['documents'] is None or all_points['metadatas'] is None:
            return loc
        for doc, meta in zip(
            all_points['documents'],
            all_points['metadatas'],
            strict=True,
        ):
            assert isinstance(meta['x'], float)
            assert isinstance(meta['y'], float)
            if self.distance_2d(loc, (meta['x'], meta['y'])) <= 0.5:
                return doc
        return loc

    @kernel_function(name='save_point')
    def save_point(self, name: str) -> None:
        """Save the current position as name."""
        pose = self.get_current_pose()
        # self.__points[name] = pose
        # await self.__destination_collection.upsert(await self.__create_destination(name, pose[0], pose[1]))
        self.__collection.add(
            ids=[str(uuid4())],
            documents=[name],
            metadatas=[{'x': pose[0], 'y': pose[1]}],
        )
        self.__logger.info(  # pyright: ignore
            f'Point {name} saved at: {{x: {pose[0]}, y: {pose[1]}}}',
        )

    @kernel_function(name='navigate_to')
    def navigate_to(self, name: str) -> bool:
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
            self.__logger.info(f'No destination found for {name}')  # pyright: ignore
            return False

        if query_results['distances'][0][0] > 1.0:
            self.__logger.info(  # pyright: ignore
                f"No destination found that's closed to {name}, closest is: {query_results['distances'][0][0]:.2f}",
            )  # pyright: ignore
            return False

        assert query_results['metadatas'] is not None

        dest_point = (
            query_results['metadatas'][0][0]['x'],
            query_results['metadatas'][0][0]['y'],
        )

        self.__logger.info(  # pyright: ignore
            f'Moving to {name} at: (x: {dest_point[0]}, y: {dest_point[1]})',
        )

        dest_pose = PoseStamped()
        dest_pose.header.frame_id = 'map'
        dest_pose.header.stamp = self.__clock.now().to_msg()

        dest_pose.pose.position.x = dest_point[0]
        dest_pose.pose.position.y = dest_point[1]
        dest_pose.pose.position.z = 0.0

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
            except Exception:
                self.__logger.info(f'Invalid speed: {speed}')
                return False
        if speed < 0.0 or speed > 1.0:
            self.__logger.info(f'Invalid speed: {speed}')
            return False
        msg_to_pub = TwistStamped()
        msg_to_pub.header.stamp = self.__clock.now().to_msg()
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
                self.__logger.info(f'Invalid direction: {direction}')
                return False

        self.__publisher.publish(msg_to_pub)
        return True
