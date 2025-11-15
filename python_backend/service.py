from __future__ import annotations

import uuid
from typing import Optional

from .backend import ChatBackend
from .memory import ConversationStore
from .models import ChatMessage, ChatMessageRole, ChatRequest, ChatResponse, SheetContext


class ChatService:
  """
  High-level chat service that adds conversation memory on top of
  a lower-level chat backend.
  """

  def __init__(self, backend: ChatBackend, store: Optional[ConversationStore] = None) -> None:
    self.backend = backend
    self.store = store or ConversationStore()

  def chat(self, request: ChatRequest) -> ChatResponse:
    """
    Handle a ChatRequest that already contains a full message history.

    This method simply forwards the request to the backend, then records
    the returned messages in the conversation store (if a sessionId is present).
    """
    response = self.backend.send_chat(request)

    if request.sessionId:
      # Store both the request history and the new messages
      history = self.store.get_history(request.sessionId)
      combined = history + request.messages + response.messages
      self.store.set_history(request.sessionId, combined)

    return response

  def simple_chat(
    self,
    session_id: str,
    user_content: str,
    sheet_context: Optional[SheetContext] = None,
  ) -> ChatResponse:
    """
    Convenience method for CLI-style usage where the caller only provides
    the latest user message. The service maintains the full conversation
    history per session and sends that to the underlying backend.
    """
    sheet_ctx = sheet_context or SheetContext()

    history = self.store.get_history(session_id)
    user_message = ChatMessage(
      id=str(uuid.uuid4()),
      role=ChatMessageRole.user,
      content=user_content,
    )
    full_history = history + [user_message]

    request = ChatRequest(
      messages=full_history,
      sheetContext=sheet_ctx,
      sessionId=session_id,
    )

    response = self.backend.send_chat(request)

    # The current Next.js /api/chat returns only the new messages; append them
    self.store.set_history(session_id, full_history + response.messages)

    return response


