#!/usr/bin/env python3
import os
import re
import uuid
from typing import Any

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from aether_interfaces.srv import (
    AddWaypoint,
    DeleteWaypoints,
    GetWaypoints,
    SemanticQueryWaypoints,
    UpdateWaypoint,
)

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
except ImportError as e:
    raise RuntimeError(
        "chromadb is required for waypoints_node. Install with: pip install chromadb"
    ) from e


def sanitize_collection_name(raw: str) -> str:
    """Make a map_id safe as a Chroma collection name.

    Chroma requires ASCII, no spaces, etc.
    """
    if not raw:
        return "map_default"
    # Replace non-alphanumeric characters with underscore.
    name = re.sub(r"[^0-9A-Za-z]+", "_", raw)
    # Avoid empty string
    if not name:
        name = "map_default"
    return f"map_{name}"


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
        super().__init__("waypoints_node")

        # Parameters
        self.declare_parameters_()

        chroma_path = self.get_parameter("chroma_path").get_parameter_value().string_value
        if not chroma_path:
            chroma_path = os.path.expanduser("~/chroma_waypoints")

        os.makedirs(chroma_path, exist_ok=True)
        self.get_logger().info(f"Using ChromaDB persistent path: {chroma_path}")

        # Initialize Chroma persistent client
        self._client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # Service servers under /waypoints namespace
        self._add_srv = self.create_service(
            AddWaypoint,
            "/waypoints/add",
            self.handle_add_waypoint,
        )
        self._get_srv = self.create_service(
            GetWaypoints,
            "/waypoints/get",
            self.handle_get_waypoints,
        )
        self._update_name_srv = self.create_service(
            UpdateWaypoint,
            "/waypoints/update",
            self.handle_update_waypoint_name,
        )
        self._delete_srv = self.create_service(
            DeleteWaypoints,
            "/waypoints/delete",
            self.handle_delete_waypoints,
        )
        self._semantic_query_srv = self.create_service(
            SemanticQueryWaypoints,
            "/waypoints/semantic_query",
            self.handle_semantic_query,
        )

        self.get_logger().info("WaypointsNode is up and running.")

    # =============================
    # Helpers
    # =============================

    def declare_parameters_(self) -> None:
        self.declare_parameter("chroma_path", os.path.join(os.getcwd(), "data/chroma"))

    def _get_collection_for_map(self, map_id: int) -> chromadb.Collection:
        return self._client.get_or_create_collection(
            name=f"map_{map_id}_waypoints",
            metadata={"map_id": map_id},
        )

    @staticmethod
    def _metadata_to_pose(meta: dict[str, Any]) -> tuple[float, float, float]:
        x = float(meta.get("x", 0.0))
        y = float(meta.get("y", 0.0))
        yaw = float(meta.get("yaw", 0.0))
        return x, y, yaw

    # =============================
    # Service handlers
    # =============================

    def handle_add_waypoint(
        self,
        request: AddWaypoint.Request,
        response: AddWaypoint.Response,
    ) -> AddWaypoint.Response:
        map_id = request.map_id
        name = request.name.strip()

        if not name:
            response.success = False
            response.message = "Waypoint name cannot be empty."
            return response

        waypoint_id = str(uuid.uuid4())
        collection = self._get_collection_for_map(map_id)

        metadata = {
            "name": name,
            "map_id": map_id,
            "x": request.x,
            "y": request.y,
            "yaw": request.yaw,
        }
        document = request.description if request.description else name

        collection.add(
            ids=[waypoint_id],
            documents=[document],
            metadatas=[metadata],
        )

        self.get_logger().info(
            f"Added waypoint id={waypoint_id} name='{name}' "
            f"map_id='{map_id}' pose=({request.x:.3f}, {request.y:.3f}, {request.yaw:.3f})",
        )

        response.success = True
        response.message = "Waypoint added."
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
        results = collection.get(include=["metadatas"])
        ids = results.get("ids", [])
        metadatas = results.get("metadatas", []) or []

        # Filter by map_id to be safe (collection metadata may be inconsistent)
        out_ids: list[str] = []
        out_names: list[str] = []
        xs: list[float] = []
        ys: list[float] = []
        yaws: list[float] = []

        for w_id, meta in zip(ids, metadatas, strict=True):
            if not isinstance(meta, dict):
                continue
            if meta.get("map_id") != map_id:
                continue
            x, y, yaw = self._metadata_to_pose(meta)
            out_ids.append(w_id)
            out_names.append(str(meta.get("name", "")))
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
            response.message = "waypoint_id cannot be empty."
            return response

        if not new_name:
            response.success = False
            response.message = "new_name cannot be empty."
            return response

        collection = self._get_collection_for_map(map_id)

        # Retrieve existing waypoint
        try:
            results = collection.get(
                ids=[waypoint_id],
                include=["metadatas", "documents"],
            )
        except Exception as e:
            self.get_logger().error(f"Error getting waypoint {waypoint_id}: {e}")
            response.success = False
            response.message = "Error retrieving waypoint."
            return response

        if not results.get("ids"):
            response.success = False
            response.message = "Waypoint not found."
            return response

        meta = results["metadatas"][0] or {}
        doc = results["documents"][0] or ""

        # Ensure map_id matches
        if meta.get("map_id") != map_id:
            response.success = False
            response.message = "Waypoint does not belong to this map."
            return response

        meta["name"] = new_name
        # Optionally update document as well (semantic text)
        if not doc or doc == meta.get("name", ""):
            doc = new_name

        try:
            collection.update(
                ids=[waypoint_id],
                metadatas=[meta],
                documents=[doc],
            )
        except Exception as e:
            self.get_logger().error(f"Error updating waypoint {waypoint_id}: {e}")
            response.success = False
            response.message = "Failed to update waypoint."
            return response

        self.get_logger().info(
            f"Updated waypoint id={waypoint_id} name='{new_name}' map_id='{map_id}'"
        )

        response.success = True
        response.message = "Waypoint name updated."
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
            self.get_logger().error(f"Error deleting waypoints: {e}")
            response.success = False
            response.message = "Failed to delete waypoints."
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
            response.message = "query cannot be empty."
            return response

        collection = self._get_collection_for_map(map_id)

        try:
            res = collection.query(
                query_texts=[query],
                n_results=k,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            self.get_logger().error(f"Error in semantic query: {e}")
            response.success = False
            response.message = "Semantic query failed."
            return response

        ids = res.get("ids", [[]])[0]
        metadatas = (res.get("metadatas", [[]]) or [[]])[0]
        distances = (res.get("distances", [[]]) or [[]])[0]  # typically smaller = closer

        out_ids: list[str] = []
        out_names: list[str] = []
        xs: list[float] = []
        ys: list[float] = []
        yaws: list[float] = []
        out_distances: list[float] = []

        for w_id, meta, dist in zip(ids, metadatas, distances, strict=True):
            if not isinstance(meta, dict):
                continue
            if meta.get("map_id") != map_id:
                continue
            x, y, yaw = self._metadata_to_pose(meta)
            out_ids.append(w_id)
            out_names.append(str(meta.get("name", "")))
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


if __name__ == "__main__":
    main()
