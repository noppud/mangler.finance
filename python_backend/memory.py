from __future__ import annotations

import threading
from typing import Dict, List

from .models import ChatMessage


class ConversationStore:
  """
  Simple in-memory conversation store keyed by sessionId.

  This is process-local and intended for development and CLI use.
  """

  def __init__(self) -> None:
    self._sessions: Dict[str, List[ChatMessage]] = {}
    self._lock = threading.Lock()

  def get_history(self, session_id: str) -> List[ChatMessage]:
    with self._lock:
      return list(self._sessions.get(session_id, []))

  def set_history(self, session_id: str, messages: List[ChatMessage]) -> None:
    with self._lock:
      self._sessions[session_id] = list(messages)

  def append_messages(self, session_id: str, messages: List[ChatMessage]) -> None:
    with self._lock:
      existing = self._sessions.get(session_id, [])
      self._sessions[session_id] = existing + list(messages)


