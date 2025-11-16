"""
MCP Executor: Handles execution of MCP tools with rate limiting
"""

from typing import Dict, Any
from .mcp_registry import MCPRegistry
from .rate_limiter import MCPRateLimiter
from .models import MCPToolCallRequest, MCPToolCallResponse
import logging
import time

logger = logging.getLogger(__name__)


class MCPExecutor:
    """Executes MCP tools with rate limiting and error handling"""

    def __init__(self, registry: MCPRegistry, rate_limiter: MCPRateLimiter):
        self.registry = registry
        self.rate_limiter = rate_limiter

    async def execute(
        self,
        user_id: str,
        request: MCPToolCallRequest
    ) -> MCPToolCallResponse:
        """Execute an MCP tool with rate limiting"""

        # Check rate limit
        allowed, remaining = await self.rate_limiter.check_rate_limit(
            user_id=user_id,
            mcp_config_id=request.mcp_server_id
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for user {user_id}, "
                f"MCP {request.mcp_server_id}"
            )
            return MCPToolCallResponse(
                success=False,
                tool_name=request.tool_name,
                error="Rate limit exceeded (100 calls/hour). Please try again later."
            )

        # Execute tool
        start_time = time.time()
        try:
            result = await self.registry.execute_tool(
                user_id=user_id,
                config_id=request.mcp_server_id,
                tool_name=request.tool_name,
                arguments=request.arguments
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Record successful call
            await self.rate_limiter.record_tool_call(
                user_id=user_id,
                mcp_config_id=request.mcp_server_id,
                tool_name=request.tool_name,
                success=True,
                execution_time_ms=execution_time_ms
            )

            logger.info(
                f"MCP tool {request.tool_name} executed successfully "
                f"in {execution_time_ms}ms"
            )

            return MCPToolCallResponse(
                success=True,
                tool_name=request.tool_name,
                result=result,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)

            # Record failed call
            await self.rate_limiter.record_tool_call(
                user_id=user_id,
                mcp_config_id=request.mcp_server_id,
                tool_name=request.tool_name,
                success=False,
                error_message=error_message,
                execution_time_ms=execution_time_ms
            )

            logger.error(f"MCP tool {request.tool_name} failed: {e}")

            return MCPToolCallResponse(
                success=False,
                tool_name=request.tool_name,
                error=error_message,
                execution_time_ms=execution_time_ms
            )
