from __future__ import annotations

import uuid
from typing import Optional

from .backend import ChatBackend
from .conversation_logger import ConversationLogger
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
    self._logger = ConversationLogger()
    self._loaded_sessions: set = set()  # Track which sessions have been loaded from DB

  def _ensure_history_loaded(self, session_id: str) -> None:
    """
    Ensure that the conversation history for a session is loaded from Supabase
    into the in-memory store. Only loads once per session.
    """
    if session_id in self._loaded_sessions:
      return

    # Check if we already have history in memory
    existing_history = self.store.get_history(session_id)
    if existing_history:
      # Already have messages in memory, mark as loaded
      self._loaded_sessions.add(session_id)
      return

    # Try to load from Supabase if logger is enabled
    if self._logger.enabled:
      messages = self._logger.load_messages(session_id)
      if messages:
        self.store.set_history(session_id, messages)

    # Mark as loaded even if no messages were found (prevents repeated DB queries)
    self._loaded_sessions.add(session_id)

  def chat(self, request: ChatRequest) -> ChatResponse:
    """
    Handle a ChatRequest that may contain partial or full message history.

    This method loads any historical messages from Supabase on first access,
    merges them with incoming messages, forwards the complete history to the backend,
    and records the returned messages.
    """
    # Load historical context from Supabase if this is the first time we're seeing this session
    if request.sessionId:
      self._ensure_history_loaded(request.sessionId)

    # Get the stored history (includes loaded Supabase messages)
    history = self.store.get_history(request.sessionId) if request.sessionId else []

    # Merge stored history with incoming messages (avoiding duplicates)
    seen_ids = {msg.id for msg in history}
    new_request_messages = [m for m in request.messages if m.id not in seen_ids]

    # Create the complete message history: stored history + new messages
    full_history = history + new_request_messages

    # Create a new request with the complete history
    full_request = ChatRequest(
      messages=full_history,
      sheetContext=request.sheetContext,
      sessionId=request.sessionId,
    )

    # Send the complete history to the backend
    response = self.backend.send_chat(full_request)

    if request.sessionId:
      session_id = request.sessionId

      # Store the complete conversation: full history + new responses
      combined = full_history + response.messages
      self.store.set_history(session_id, combined)

      if self._logger.enabled:
        # Persist only newly seen request messages plus this turn's responses
        self._logger.log_messages(
          session_id,
          list(new_request_messages) + list(response.messages),
          sheet_context=request.sheetContext,
        )

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

    # Load historical context from Supabase if this is the first time we're seeing this session
    self._ensure_history_loaded(session_id)

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

    # The current backend returns only the new messages; append them
    combined = full_history + response.messages
    self.store.set_history(session_id, combined)

    if self._logger.enabled:
      # For CLI-style usage we know exactly which messages are new.
      self._logger.log_messages(
        session_id,
        [user_message] + list(response.messages),
        sheet_context=sheet_ctx,
      )

    return response
