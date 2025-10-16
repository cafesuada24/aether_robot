from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP(
    'aether_mcp_sever',
    host='localhost',
    port=8000,
)
