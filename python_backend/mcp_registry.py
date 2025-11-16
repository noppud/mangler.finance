"""
MCP Registry: Manages MCP server lifecycle for users
- Loads user's MCP configurations from database
- Starts/stops MCP server processes
- Caches running servers per user session
- Provides unified tool discovery
"""

from typing import Dict, List, Optional, Set, Any
from .mcp_client import MCPClient, MCPServer
from .models import MCPConfiguration, MCPTool
from .supabase_client import get_supabase_client
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


class MCPRegistry:
    """
    Registry for managing MCP server instances.
    Maintains per-user server pools with lifecycle management.
    """

    def __init__(self):
        # user_id -> {config_id -> MCPServer}
        self._user_servers: Dict[str, Dict[str, MCPServer]] = {}
        self._lock = asyncio.Lock()
        self._loaded_users: Set[str] = set()  # Track which users are loaded

    async def load_user_mcps(self, user_id: str, force_reload: bool = False) -> List[MCPServer]:
        """
        Load and start all enabled MCPs for a user.
        Caches servers to avoid repeated starts.
        """
        async with self._lock:
            # Check if already loaded
            if user_id in self._loaded_users and not force_reload:
                logger.debug(f"MCPs already loaded for user {user_id}")
                return list(self._user_servers.get(user_id, {}).values())

        logger.info(f"Loading MCPs for user {user_id}")

        # Fetch configurations from database
        configs = await self._fetch_user_configs(user_id)
        logger.info(f"Found {len(configs)} MCP configurations for user {user_id}")

        servers = []
        async with self._lock:
            # Initialize user server dict if needed
            if user_id not in self._user_servers:
                self._user_servers[user_id] = {}

            for config in configs:
                if not config.enabled:
                    logger.debug(f"Skipping disabled MCP: {config.name}")
                    continue

                # Check if already running
                if config.id in self._user_servers[user_id]:
                    logger.debug(f"MCP {config.name} already running")
                    servers.append(self._user_servers[user_id][config.id])
                    continue

                # Start new server
                server = await self._start_mcp_server(config)
                if server:
                    self._user_servers[user_id][config.id] = server
                    servers.append(server)

            self._loaded_users.add(user_id)

        return servers

    async def _fetch_user_configs(self, user_id: str) -> List[MCPConfiguration]:
        """Fetch MCP configurations from database"""
        supabase = get_supabase_client()
        if not supabase:
            logger.warning("Supabase not configured, no MCPs available")
            return []

        try:
            result = supabase.table("mcp_configurations")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=False)\
                .execute()

            configs = [MCPConfiguration(**row) for row in result.data]
            return configs

        except Exception as e:
            logger.error(f"Failed to fetch MCP configs for user {user_id}: {e}")
            return []

    async def _start_mcp_server(self, config: MCPConfiguration) -> Optional[MCPServer]:
        """Start an MCP server from configuration"""
        logger.info(f"Starting MCP server: {config.name}")

        try:
            client = MCPClient(
                command=config.command,
                args=config.args,
                env=config.env,
                name=config.name
            )

            await client.start()
            await client.initialize()
            tools = await client.list_tools()

            server = MCPServer(
                id=str(uuid.uuid4()),
                config_id=config.id,
                name=config.name,
                process=client.process,
                tools=tools,
                _client=client
            )

            logger.info(f"Started MCP server: {config.name} with {len(tools)} tools")
            return server

        except Exception as e:
            logger.error(f"Failed to start MCP {config.name}: {e}", exc_info=True)
            return None

    async def get_user_tools(self, user_id: str) -> List[MCPTool]:
        """
        Get all tools from all running MCP servers for a user.
        Automatically loads MCPs if not already loaded.
        """
        # Ensure MCPs are loaded
        await self.load_user_mcps(user_id)

        tools = []
        async with self._lock:
            user_servers = self._user_servers.get(user_id, {})

            for config_id, server in user_servers.items():
                for tool_def in server.tools:
                    tools.append(MCPTool(
                        name=tool_def["name"],
                        description=tool_def.get("description", "No description"),
                        input_schema=tool_def.get("inputSchema", {}),
                        mcp_server_id=config_id,
                        mcp_server_name=server.name
                    ))

        logger.debug(f"User {user_id} has {len(tools)} MCP tools available")
        return tools

    async def execute_tool(
        self,
        user_id: str,
        config_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Execute a tool on a specific MCP server"""
        async with self._lock:
            user_servers = self._user_servers.get(user_id, {})
            server = user_servers.get(config_id)

            if not server:
                raise ValueError(
                    f"MCP server {config_id} not found for user {user_id}"
                )

        # Execute via client
        client: MCPClient = server._client
        result = await client.call_tool(tool_name, arguments)
        return result

    async def shutdown_user_mcps(self, user_id: str) -> None:
        """Shutdown all MCP servers for a user"""
        logger.info(f"Shutting down all MCPs for user {user_id}")

        async with self._lock:
            user_servers = self._user_servers.pop(user_id, {})
            self._loaded_users.discard(user_id)

        for server in user_servers.values():
            try:
                client: MCPClient = server._client
                await client.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down MCP {server.name}: {e}")

        logger.info(f"Shut down {len(user_servers)} MCPs for user {user_id}")

    async def shutdown_all(self) -> None:
        """Shutdown all MCP servers (for graceful app shutdown)"""
        logger.info("Shutting down all MCP servers")

        user_ids = list(self._user_servers.keys())
        for user_id in user_ids:
            await self.shutdown_user_mcps(user_id)

        logger.info("All MCP servers shut down")


# Global registry instance
_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    """Get or create the global MCP registry"""
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry
