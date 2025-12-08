#!/usr/bin/env python3
import math
import os
import re
import time
import uuid
from typing import Any, cast

import rclpy
import rclpy.duration
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import (
    Buffer,
    ConnectivityException,
    ExtrapolationException,
    LookupException,
    TransformListener,
)

from aether_interfaces.srv import (
    # AddWaypoint,
    DeleteWaypoints,
    GetWaypoints,
    MoveToWaypoint,
    SaveCurrentPoseWaypoint,
    SemanticQueryWaypoints,
    UpdateWaypoint,
)

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
except ImportError as e:
    raise RuntimeError(
        'chromadb is required for waypoints_node. Install with: pip install chromadb'
    ) from e


def sanitize_collection_name(raw: str) -> str:
    """Make a map_id safe as a Chroma collection name.

    Chroma requires ASCII, no spaces, etc.
    """
    if not raw:
        return 'map_default'
    # Replace non-alphanumeric characters with underscore.
    name = re.sub(r'[^0-9A-Za-z]+', '_', raw)
    # Avoid empty string
    if not name:
        name = 'map_default'
    return f'map_{name}'


class WaypointsNode(Node):
    """Node to manage waypoints stored in ChromaDB.

    - One Chroma collection per map_id (sanitized).
    - Each waypoint stored as:
        id:   waypoint_id (string)
        doc:  description (string)
        metadata: {
            "name": <string>,
            "map_id": <string>,
            "x": <float>,
            "y": <float>,
            "yaw": <float>,
        }
    """

    def __init__(self) -> None:
        super().__init__('/waypoints_manager')

        # Parameters
        self.declare_parameters_()

        self._global_frame: str = (
            self.get_parameter('global_frame').get_parameter_value().string_value
        )

        self._nav2_action_name: str = (
            self.get_parameter('nav2_action_name').get_parameter_value().string_value
        )
        self._nav2_server_timeout_sec: float = (
            self.get_parameter('nav2_server_timeout_sec')
            .get_parameter_value()
            .double_value
        )
        self._nav2_goal_response_timeout_sec: float = (
            self.get_parameter('nav2_goal_response_timeout_sec')
            .get_parameter_value()
            .double_value
        )
        self._robot_base_frame: str = (
            self.get_parameter('robot_base_frame').get_parameter_value().string_value
        )
        chroma_path: str = (
            self.get_parameter('chroma_path').get_parameter_value().string_value
        )
        if not chroma_path:
            chroma_path = os.path.join(os.getcwd(), 'data/chroma')

        os.makedirs(chroma_path, exist_ok=True)
        self.get_logger().info(f'Using ChromaDB persistent path: {chroma_path}')

        # Initialize Chroma persistent client
        self._client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )

        self._nav_cb_group = ReentrantCallbackGroup()
        self._nav_action_client = ActionClient(
            self,
            NavigateToPose,
            self._nav2_action_name,
            callback_group=self._nav_cb_group,
        )

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self, spin_thread=True)

        self._srv_cb_group_ = MutuallyExclusiveCallbackGroup()
        self._get_srv = self.create_service(
            GetWaypoints,
            '/waypoints/get',
            self.handle_get_waypoints,
        )
        self._update_name_srv = self.create_service(
            UpdateWaypoint,
            '/waypoints/update',
            self.handle_update_waypoint_name,
        )
        self._delete_srv = self.create_service(
            DeleteWaypoints,
            '/waypoints/delete',
            self.handle_delete_waypoints,
        )
        self._semantic_query_srv = self.create_service(
            SemanticQueryWaypoints,
            '/waypoints/semantic_query',
            self.handle_semantic_query,
        )

        self._send_to_nav_srv = self.create_service(
            MoveToWaypoint,
            '/waypoints/move_to_waypoint',
            self.handle_move_to_waypoint,
            callback_group=self._srv_cb_group_,
        )

        self._save_current_pose_srv = self.create_service(
            SaveCurrentPoseWaypoint,
            '/waypoints/save_current_pose',
            self.handle_save_current_pose_waypoint,
        )

        self.get_logger().info('WaypointsNode is up and running.')

    # =============================
    # Helpers
    # =============================

    def declare_parameters_(self) -> None:
        self.declare_parameter('chroma_path', os.path.join(os.getcwd(), 'data/chroma'))
        self.declare_parameter('global_frame', 'map')
        self.declare_parameter('nav2_action_name', 'navigate_to_pose')
        self.declare_parameter('nav2_server_timeout_sec', 5.0)
        self.declare_parameter('nav2_goal_response_timeout_sec', 5.0)
        self.declare_parameter('robot_base_frame', 'base_link')

    def _get_collection_for_map(self, map_id: int) -> chromadb.Collection:
        return self._client.get_or_create_collection(
            name=f'map_{map_id}_waypoints',
            metadata={'map_id': map_id},
        )

    @staticmethod
    def _metadata_to_pose(meta: dict[str, Any]) -> tuple[float, float, float]:
        x = float(meta.get('x', 0.0))
        y = float(meta.get('y', 0.0))
        yaw = float(meta.get('yaw', 0.0))
        return x, y, yaw

    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
        """Convert yaw (in rad) into quaternion (x, y, z, w) in 2D (z-up)."""
        half = yaw * 0.5
        qz = math.sin(half)
        qw = math.cos(half)
        return 0.0, 0.0, qz, qw

    # =============================
    # Service handlers
    # =============================

    # def handle_add_waypoint(
    #     self,
    #     request: AddWaypoint.Request,
    #     response: AddWaypoint.Response,
    # ) -> AddWaypoint.Response:
    #     map_id = request.map_id
    #     name = request.name.strip()
    #
    #     if not name:
    #         response.success = False
    #         response.message = 'Waypoint name cannot be empty.'
    #         return response
    #
    #     waypoint_id = str(uuid.uuid4())
    #     collection = self._get_collection_for_map(map_id)
    #
    #     metadata = {
    #         'name': name,
    #         'map_id': map_id,
    #         'x': request.x,
    #         'y': request.y,
    #         'yaw': request.yaw,
    #     }
    #     document = request.description if request.description else name
    #
    #     collection.add(
    #         ids=[waypoint_id],
    #         documents=[document],
    #         metadatas=[metadata],
    #     )
    #
    #     self.get_logger().info(
    #         f"Added waypoint id={waypoint_id} name='{name}' "
    #         f"map_id='{map_id}' pose=({request.x:.3f}, {request.y:.3f}, {request.yaw:.3f})",
    #     )
    #
    #     response.success = True
    #     response.message = 'Waypoint added.'
    #     response.waypoint_id = waypoint_id
    #     return response

    def handle_save_current_pose_waypoint(
        self,
        request: SaveCurrentPoseWaypoint.Request,
        response: SaveCurrentPoseWaypoint.Response,
    ) -> SaveCurrentPoseWaypoint.Response:
        map_id = cast('int', request.map_id)
        name = cast('str', request.name.strip())

        if not name:
            response.success = False
            response.message = 'Waypoint name cannot be empty.'
            response.waypoint_id = ''
            return response

        try:
            # Time() with no args means "latest available" in ROS 2 Python
            transform = self._tf_buffer.lookup_transform(
                self._global_frame,
                self._robot_base_frame,
                Time(),
                timeout=rclpy.duration.Duration(seconds=0.5),
            )
        except (LookupException, ConnectivityException, ExtrapolationException) as ex:
            self.get_logger().warn(f'TF lookup failed: {ex}')
            response.success = False
            response.message = (
                f'Failed to get transform {self._global_frame} -> '
                f'{self._robot_base_frame}: {ex}'
            )
            response.waypoint_id = ''
            return response

        t = transform.transform.translation
        q = transform.transform.rotation

        x = float(t.x)
        y = float(t.y)

        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        collection = self._get_collection_for_map(map_id)

        waypoint_id = str(uuid.uuid4())
        metadata = {
            'name': name,
            'map_id': map_id,
            'x': x,
            'y': y,
            'yaw': yaw,
        }
        document = request.description if request.description else name

        collection.add(
            ids=[waypoint_id],
            documents=[document],
            metadatas=[metadata],
        )

        self.get_logger().info(
            f"Saved current pose as waypoint id={waypoint_id} name='{name}' "
            f"map_id='{map_id}' pose=({x:.3f}, {y:.3f}, {yaw:.3f})",
        )

        response.success = True
        response.message = 'Current pose saved as waypoint.'
        response.waypoint_id = waypoint_id
        return response

    def handle_get_waypoints(
        self,
        request: GetWaypoints.Request,
        response: GetWaypoints.Response,
    ) -> GetWaypoints.Response:
        map_id = request.map_id

        collection = self._get_collection_for_map(map_id)

        # Get all waypoints in collection
        # NOTE: include=['metadatas'] to avoid retrieving embeddings
        results = collection.get(include=['metadatas'])
        ids = results.get('ids', [])
        metadatas = results.get('metadatas', []) or []

        # Filter by map_id to be safe (collection metadata may be inconsistent)
        out_ids: list[str] = []
        out_names: list[str] = []
        xs: list[float] = []
        ys: list[float] = []
        yaws: list[float] = []

        for w_id, meta in zip(ids, metadatas, strict=True):
            if not isinstance(meta, dict):
                continue
            if meta.get('map_id') != map_id:
                continue
            x, y, yaw = self._metadata_to_pose(meta)
            out_ids.append(w_id)
            out_names.append(str(meta.get('name', '')))
            xs.append(x)
            ys.append(y)
            yaws.append(yaw)

        response.ids = out_ids
        response.names = out_names
        response.xs = xs
        response.ys = ys
        response.yaws = yaws

        response.success = True
        response.message = f"Found {len(out_ids)} waypoint(s) for map_id='{map_id}'."
        return response

    def handle_update_waypoint_name(
        self,
        request: UpdateWaypoint.Request,
        response: UpdateWaypoint.Response,
    ) -> UpdateWaypoint.Response:
        map_id = request.map_id
        waypoint_id = request.waypoint_id.strip()
        new_name = request.name.strip()

        if not waypoint_id:
            response.success = False
            response.message = 'waypoint_id cannot be empty.'
            return response

        if not new_name:
            response.success = False
            response.message = 'new_name cannot be empty.'
            return response

        collection = self._get_collection_for_map(map_id)

        # Retrieve existing waypoint
        try:
            results = collection.get(
                ids=[waypoint_id],
                include=['metadatas', 'documents'],
            )
        except Exception as e:
            self.get_logger().error(f'Error getting waypoint {waypoint_id}: {e}')
            response.success = False
            response.message = 'Error retrieving waypoint.'
            return response

        if not results.get('ids'):
            response.success = False
            response.message = 'Waypoint not found.'
            return response

        meta = results['metadatas'][0] or {}
        doc = results['documents'][0] or ''

        # Ensure map_id matches
        if meta.get('map_id') != map_id:
            response.success = False
            response.message = 'Waypoint does not belong to this map.'
            return response

        meta['name'] = new_name
        # Optionally update document as well (semantic text)
        if not doc or doc == meta.get('name', ''):
            doc = new_name

        try:
            collection.update(
                ids=[waypoint_id],
                metadatas=[meta],
                documents=[doc],
            )
        except Exception as e:
            self.get_logger().error(f'Error updating waypoint {waypoint_id}: {e}')
            response.success = False
            response.message = 'Failed to update waypoint.'
            return response

        self.get_logger().info(
            f"Updated waypoint id={waypoint_id} name='{new_name}' map_id='{map_id}'"
        )

        response.success = True
        response.message = 'Waypoint name updated.'
        return response

    def handle_delete_waypoints(
        self,
        request: DeleteWaypoints.Request,
        response: DeleteWaypoints.Response,
    ) -> DeleteWaypoints.Response:
        map_id = request.map_id
        ids_to_delete = [w_id.strip() for w_id in request.waypoint_ids if w_id.strip()]

        collection = self._get_collection_for_map(map_id)

        deleted_count = 0

        try:
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                deleted_count = len(ids_to_delete)
            else:
                # delete all waypoints in this map collection
                collection.delete(where={})  # delete everything in collection
                # Note: we cannot accurately know number deleted without an extra get.
                deleted_count = -1  # indicate "all"
        except Exception as e:
            self.get_logger().error(f'Error deleting waypoints: {e}')
            response.success = False
            response.message = 'Failed to delete waypoints.'
            response.deleted_count = 0
            return response

        if deleted_count == -1:
            msg = f"Deleted all waypoints for map_id='{map_id}'."
        else:
            msg = f"Deleted {deleted_count} waypoint(s) for map_id='{map_id}'."

        self.get_logger().info(msg)
        response.success = True
        response.message = msg
        response.deleted_count = deleted_count
        return response

    def handle_semantic_query(
        self,
        request: SemanticQueryWaypoints.Request,
        response: SemanticQueryWaypoints.Response,
    ) -> SemanticQueryWaypoints.Response:
        map_id = request.map_id
        query = request.query.strip()
        k = request.k if request.k > 0 else 5

        if not query:
            response.success = False
            response.message = 'query cannot be empty.'
            return response

        collection = self._get_collection_for_map(map_id)

        try:
            res = collection.query(
                query_texts=[query],
                n_results=k,
                include=['metadatas', 'distances'],
            )
        except Exception as e:
            self.get_logger().error(f'Error in semantic query: {e}')
            response.success = False
            response.message = 'Semantic query failed.'
            return response

        ids = res.get('ids', [[]])[0]
        metadatas = (res.get('metadatas', [[]]) or [[]])[0]
        distances = (res.get('distances', [[]]) or [[]])[
            0
        ]  # typically smaller = closer

        out_ids: list[str] = []
        out_names: list[str] = []
        xs: list[float] = []
        ys: list[float] = []
        yaws: list[float] = []
        out_distances: list[float] = []

        for w_id, meta, dist in zip(ids, metadatas, distances, strict=True):
            if not isinstance(meta, dict):
                continue
            if meta.get('map_id') != map_id:
                continue
            x, y, yaw = self._metadata_to_pose(meta)
            out_ids.append(w_id)
            out_names.append(str(meta.get('name', '')))
            xs.append(x)
            ys.append(y)
            yaws.append(yaw)
            out_distances.append(float(dist))

        response.ids = out_ids
        response.names = out_names
        response.xs = xs
        response.ys = ys
        response.yaws = yaws
        response.distances = out_distances

        response.success = True
        response.message = f"Found {len(out_ids)} result(s) for query='{query}'."
        return response

    def handle_move_to_waypoint(
        self,
        request: MoveToWaypoint.Request,
        response: MoveToWaypoint.Response,
    ) -> MoveToWaypoint.Response:
        map_id = cast('int', request.map_id)
        waypoint_id = cast('str', request.waypoint_id.strip())

        if not waypoint_id:
            response.success = False
            response.message = 'waypoint_id cannot be empty.'
            response.action_id = ''
            return response

        # Look up waypoint in Chroma
        collection = self._get_collection_for_map(map_id)
        try:
            results = collection.get(
                ids=[waypoint_id],
                include=['metadatas'],
            )
        except Exception as e:
            self.get_logger().error(f'Error getting waypoint {waypoint_id}: {e}')
            response.success = False
            response.message = 'Error retrieving waypoint.'
            response.action_id = ''
            return response

        if not results.get('ids'):
            response.success = False
            response.message = 'Waypoint not found.'
            response.action_id = ''
            return response

        meta = (results.get('metadatas') or [None])[0]
        if not isinstance(meta, dict):
            response.success = False
            response.message = 'Waypoint metadata invalid.'
            response.action_id = ''
            return response

        if meta.get('map_id') != map_id:
            response.success = False
            response.message = 'Waypoint does not belong to this map.'
            response.action_id = ''
            return response

        x, y, yaw = self._metadata_to_pose(meta)
        name = str(meta.get('name', ''))

        # Ensure Nav2 server is available
        self.get_logger().info(
            f"Waiting for Nav2 action server '{self._nav2_action_name}'..."
        )
        if not self._nav_action_client.wait_for_server(
            timeout_sec=self._nav2_server_timeout_sec
        ):
            response.success = False
            response.message = 'Nav2 action server not available.'
            response.action_id = ''
            self.get_logger().error('Nav2 action server not available.')
            return response

        # Build goal
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = self._global_frame
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.position.z = 0.0

        qx, qy, qz, qw = self._yaw_to_quaternion(yaw)
        goal.pose.pose.orientation.x = qx
        goal.pose.pose.orientation.y = qy
        goal.pose.pose.orientation.z = qz
        goal.pose.pose.orientation.w = qw

        self.get_logger().info(
            f'Sending Nav2 goal from waypoint id={waypoint_id}, '
            f"name='{name}', pose=({x:.3f}, {y:.3f}, {yaw:.3f}) "
            f"in frame '{self._global_frame}'."
        )

        # Send goal asynchronously, then block locally on the goal response ONLY
        send_future = self._nav_action_client.send_goal_async(goal)

        deadline = Time() + rclpy.duration.Duration(
            seconds=self._nav2_goal_response_timeout_sec
        )
        while not send_future.done() and Time() < deadline and rclpy.ok():
            time.sleep(0.01)

        if not send_future.done():
            response.success = False
            response.message = 'Timeout waiting for Nav2 to accept goal.'
            response.action_id = ''
            self.get_logger().error('Timeout waiting for Nav2 goal response.')
            return response

        goal_handle = send_future.result()
        if not goal_handle.accepted:
            response.success = False
            response.message = 'Nav2 rejected the goal.'
            response.action_id = ''
            self.get_logger().warn('Nav2 goal rejected.')
            return response

        # Extract action/goal id (UUID) and convert to hex string
        uuid_bytes = goal_handle.goal_id.uuid  # sequence of 16 bytes
        action_id = ''.join(f'{b:02x}' for b in uuid_bytes)

        self.get_logger().info(f'Nav2 goal accepted. action_id={action_id}')

        response.success = True
        response.message = 'Goal sent to Nav2.'
        response.action_id = action_id
        return response


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = WaypointsNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
