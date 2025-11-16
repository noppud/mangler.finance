"""
MCP (Model Context Protocol) Client Implementation
Supports stdio communication with MCP servers per spec:
https://spec.modelcontextprotocol.io/
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid
import os

logger = logging.getLogger(__name__)

@dataclass
class MCPServer:
    """Represents a running MCP server process"""
    id: str
    config_id: str
    name: str
    process: asyncio.subprocess.Process
    tools: List[Dict[str, Any]]
    _client: 'MCPClient'  # Reference to client for execution


class MCPClient:
    """
    Client for communicating with MCP servers via stdio.
    Implements JSON-RPC 2.0 protocol over stdin/stdout.
    """

    def __init__(
        self,
        command: str,
        args: List[str],
        env: Dict[str, str] = None,
        name: str = "MCP Server"
    ):
        self.command = command
        self.args = args
        self.env = {**os.environ, **(env or {})}
        self.name = name
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def start(self) -> None:
        """Start the MCP server process"""
        logger.info(f"Starting MCP server: {self.name}")
        logger.debug(f"Command: {self.command} {' '.join(self.args)}")

        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env
            )

            # Start background task to read responses
            self._reader_task = asyncio.create_task(self._read_responses())

            logger.info(f"MCP server started: {self.name} (PID: {self.process.pid})")

        except Exception as e:
            logger.error(f"Failed to start MCP server {self.name}: {e}")
            raise

    async def _read_responses(self) -> None:
        """Background task to read JSON-RPC responses from stdout"""
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    logger.warning(f"MCP server {self.name} stdout closed")
                    break

                try:
                    response = json.loads(line.decode().strip())
                    await self._handle_response(response)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from MCP {self.name}: {e}")
                    logger.debug(f"Raw line: {line}")

        except Exception as e:
            logger.error(f"Error reading from MCP {self.name}: {e}")

    async def _handle_response(self, response: Dict[str, Any]) -> None:
        """Handle a JSON-RPC response"""
        if "id" in response:
            # Response to a request
            request_id = str(response["id"])
            future = self.pending_requests.pop(request_id, None)
            if future and not future.done():
                if "error" in response:
                    future.set_exception(
                        Exception(f"MCP error: {response['error']}")
                    )
                else:
                    future.set_result(response.get("result"))
        else:
            # Notification (no response expected)
            logger.debug(f"MCP notification from {self.name}: {response}")

    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Send a JSON-RPC request and wait for response"""
        if not self.process or not self.process.stdin:
            raise RuntimeError(f"MCP server {self.name} not started")

        self.request_id += 1
        request_id = str(self.request_id)

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        logger.debug(f"MCP request to {self.name}: {method}")

        # Wait for response with timeout
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise TimeoutError(f"MCP request {method} timed out after 30s")

    async def initialize(self) -> Dict[str, Any]:
        """Send initialize request to MCP server"""
        logger.info(f"Initializing MCP server: {self.name}")

        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "mangler-finance",
                "version": "1.0.0"
            }
        })

        self._initialized = True
        logger.info(f"MCP server initialized: {self.name}")
        logger.debug(f"Server capabilities: {result}")

        return result

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of tools from MCP server"""
        if not self._initialized:
            raise RuntimeError(f"MCP server {self.name} not initialized")

        logger.debug(f"Listing tools from MCP {self.name}")

        result = await self._send_request("tools/list")
        tools = result.get("tools", [])

        logger.info(f"MCP {self.name} exposed {len(tools)} tools")
        for tool in tools:
            logger.debug(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")

        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Execute a tool on the MCP server"""
        if not self._initialized:
            raise RuntimeError(f"MCP server {self.name} not initialized")

        logger.info(f"Calling tool {tool_name} on MCP {self.name}")
        logger.debug(f"Arguments: {arguments}")

        try:
            result = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            logger.info(f"Tool {tool_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the MCP server"""
        logger.info(f"Shutting down MCP server: {self.name}")

        try:
            # Cancel reader task
            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()

            # Close stdin
            if self.process and self.process.stdin:
                self.process.stdin.close()
                await self.process.stdin.wait_closed()

            # Wait for process to exit (with timeout)
            if self.process:
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"MCP {self.name} did not exit gracefully, terminating")
                    self.process.terminate()
                    await self.process.wait()

            logger.info(f"MCP server shut down: {self.name}")

        except Exception as e:
            logger.error(f"Error shutting down MCP {self.name}: {e}")
