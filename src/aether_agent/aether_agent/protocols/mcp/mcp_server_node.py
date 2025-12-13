# Copyright (c) 2025 Cafesuada
# All rights reserved.

import asyncio
from abc import ABCMeta, abstractmethod

import chromadb
from mcp.server.fastmcp.server import FastMCP
from nav2_msgs.action import NavigateToPose
from rclpy.action.client import ActionClient
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener

from aether_agent.protocols.mcp.tools.navigation_mixin import (
    NavigationMixin,
)


class MCPServerNode(Node, NavigationMixin, metaclass=ABCMeta):
    def __init__(self, node_name: str) -> None:
        super().__init__(node_name)

        self._declare_parameters()

        self._tf_buffer = Buffer()
        self.__tf_listener = TransformListener(self._tf_buffer, self)

        self.__db_client = chromadb.PersistentClient()
        self._collection = self.__db_client.get_or_create_collection(
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
        self._nav_to_pose_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose',
        )

        self._mcp = self._create_mcp()
        # self.__cmd_vel_publisher = self.create_publisher(TwistStamped, '/cmd_vel', 10)  # pyright: ignore

        self._loop = self._get_event_loop()

        self.__load_tools()

    def __load_tools(self) -> None:
        NavigationMixin._load_tools(self)


    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    @abstractmethod
    def _declare_parameters(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _create_mcp(self) -> FastMCP:
        raise NotImplementedError

    @abstractmethod
    async def run_server(self) -> None:
        """Start mcp server."""
        raise NotImplementedError


