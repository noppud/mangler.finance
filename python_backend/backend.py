from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import ChatRequest, ChatResponse
from .orchestrator import AgentOrchestrator
from .llm import create_llm_client
from .sheets_client import ServiceAccountSheetsClient
from .context_builder import ContextBuilder


class ChatBackend(ABC):
  """
  Abstract chat backend. This allows us to later swap out the
  implementation (e.g. to a pure-Python orchestrator) without
  changing the CLI or HTTP API.
  """

  @abstractmethod
  def send_chat(self, request: ChatRequest) -> ChatResponse:  # pragma: no cover - interface
    raise NotImplementedError


class PythonChatBackend(ChatBackend):
  """
  Chat backend that runs the pure-Python AgentOrchestrator and Sheet/LLM stack
  directly (no Next.js dependency).
  """

  def __init__(self) -> None:
    llm_client = create_llm_client()
    sheets_client = ServiceAccountSheetsClient()
    context_builder = ContextBuilder(sheets_client)
    self._orchestrator = AgentOrchestrator(
      llm_client=llm_client,
      sheets_client=sheets_client,
      context_builder=context_builder,
    )

  def send_chat(self, request: ChatRequest) -> ChatResponse:
    new_messages = self._orchestrator.process_chat(
      request.messages,
      request.sheetContext,
    )
    return ChatResponse(messages=new_messages, sessionId=request.sessionId)

