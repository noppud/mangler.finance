from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import ChatRequest, ChatResponse
from .orchestrator import AgentOrchestrator
from .llm import create_llm_client
from .sheets_client import ServiceAccountSheetsClient
from .context_builder import ContextBuilder
from .mcp_registry import MCPRegistry
from .rate_limiter import MCPRateLimiter


class ChatBackend(ABC):
  """
  Abstract chat backend. This allows us to later swap out the
  implementation (e.g. to a pure-Python orchestrator) without
  changing the CLI or HTTP API.
  """

  @abstractmethod
  async def send_chat(self, request: ChatRequest) -> ChatResponse:  # pragma: no cover - interface
    raise NotImplementedError


class PythonChatBackend(ChatBackend):
  """
  Enhanced chat backend with MCP support.
  """

  def __init__(
    self,
    mcp_registry: Optional[MCPRegistry] = None,
    rate_limiter: Optional[MCPRateLimiter] = None
  ) -> None:
    llm_client = create_llm_client()
    sheets_client = ServiceAccountSheetsClient()
    context_builder = ContextBuilder(sheets_client)
    self._orchestrator = AgentOrchestrator(
      llm_client=llm_client,
      sheets_client=sheets_client,
      context_builder=context_builder,
      mcp_registry=mcp_registry,
      rate_limiter=rate_limiter
    )

  async def send_chat(self, request: ChatRequest) -> ChatResponse:
    # Extract user_id if present in request (added by API layer)
    user_id = getattr(request, 'user_id', None)

    new_messages = await self._orchestrator.process_chat(
      request.messages,
      request.sheetContext,
      user_id=user_id,
      mcp_mentions=request.mcpMentions
    )

    # Track which MCP tools were used
    mcp_tools_used = []
    for msg in new_messages:
      if msg.metadata and msg.metadata.toolName and msg.metadata.toolName.startswith("mcp_"):
        mcp_tools_used.append(msg.metadata.toolName)

    return ChatResponse(
      messages=new_messages,
      sessionId=request.sessionId,
      mcpToolsUsed=mcp_tools_used if mcp_tools_used else None
    )

