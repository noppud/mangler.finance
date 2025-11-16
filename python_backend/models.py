from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessageRole(str, Enum):
  user = "user"
  assistant = "assistant"
  tool = "tool"
  system = "system"


class ChatMessageMetadata(BaseModel):
  toolName: Optional[str] = None
  payload: Optional[Any] = None
  plan: Optional[str] = None
  error: Optional[str] = None
  timestamp: Optional[str] = None


class ChatMessage(BaseModel):
  id: str
  role: ChatMessageRole
  content: str
  metadata: Optional[ChatMessageMetadata] = None


class SheetContext(BaseModel):
  spreadsheetId: Optional[str] = None
  sheetTitle: Optional[str] = None


class ChatRequest(BaseModel):
  messages: List[ChatMessage]
  sheetContext: SheetContext = Field(default_factory=SheetContext)
  sessionId: Optional[str] = None


class ChatResponse(BaseModel):
  messages: List[ChatMessage]
  sessionId: Optional[str] = None


def chat_request_to_dict(request: ChatRequest) -> Dict[str, Any]:
  """
  Serialize ChatRequest to a plain dict compatible with the
  existing TypeScript /api/chat endpoint.
  """
  return request.model_dump(exclude_none=True)


def chat_response_from_dict(data: Dict[str, Any]) -> ChatResponse:
  """
  Parse a dict (from JSON) into ChatResponse.
  """
  return ChatResponse.model_validate(data)


