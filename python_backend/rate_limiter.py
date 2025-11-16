"""
Rate limiter for MCP tool calls.
Enforces 100 calls/hour per MCP configuration.
"""

from typing import Optional
from datetime import datetime, timedelta
from .supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class MCPRateLimiter:
    """Rate limiter for MCP tool calls (100 calls/hour)"""

    def __init__(self, calls_per_hour: int = 100):
        self.calls_per_hour = calls_per_hour

    async def check_rate_limit(
        self,
        user_id: str,
        mcp_config_id: str
    ) -> tuple[bool, Optional[int]]:
        """
        Check if user has exceeded rate limit for this MCP.
        Returns (allowed: bool, remaining: int)
        """
        supabase = get_supabase_client()
        if not supabase:
            # If DB unavailable, allow (fail open)
            logger.warning("Supabase unavailable, rate limiting disabled")
            return (True, None)

        try:
            # Count calls in last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            result = supabase.table("mcp_tool_calls")\
                .select("id", count="exact")\
                .eq("mcp_config_id", mcp_config_id)\
                .gte("called_at", one_hour_ago.isoformat())\
                .execute()

            call_count = result.count or 0
            remaining = max(0, self.calls_per_hour - call_count)
            allowed = call_count < self.calls_per_hour

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user_id}, "
                    f"MCP {mcp_config_id}: {call_count}/{self.calls_per_hour}"
                )

            return (allowed, remaining)

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open
            return (True, None)

    async def record_tool_call(
        self,
        user_id: str,
        mcp_config_id: str,
        tool_name: str,
        success: bool,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """Record a tool call for rate limiting and analytics"""
        supabase = get_supabase_client()
        if not supabase:
            return

        try:
            supabase.table("mcp_tool_calls").insert({
                "mcp_config_id": mcp_config_id,
                "user_id": user_id,
                "tool_name": tool_name,
                "success": success,
                "error_message": error_message,
                "execution_time_ms": execution_time_ms
            }).execute()

        except Exception as e:
            logger.error(f"Failed to record tool call: {e}")


# Global rate limiter instance
_rate_limiter: Optional[MCPRateLimiter] = None


def get_rate_limiter() -> MCPRateLimiter:
    """Get or create the global rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = MCPRateLimiter(calls_per_hour=100)
    return _rate_limiter
