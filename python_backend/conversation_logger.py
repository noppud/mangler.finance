from __future__ import annotations

import uuid
from typing import Iterable, List, Optional

from .logging_config import get_logger
from .models import ChatMessage, ChatMessageRole, ChatMessageMetadata, SheetContext
from .supabase_client import get_supabase_client

logger = get_logger(__name__)


class ConversationLogger:
  """
  Lightweight logger that persists chat messages to Supabase when configured.

  If Supabase configuration is missing or invalid, all methods become no-ops
  and the application continues to function with in-memory-only conversations.
  """

  def __init__(self) -> None:
    self._client = get_supabase_client()
    if self._client:
      logger.info("ConversationLogger enabled with Supabase client")
    else:
      logger.warning("ConversationLogger disabled: Supabase client not available")

  @property
  def enabled(self) -> bool:
    return self._client is not None

  def load_messages(self, session_id: str) -> List[ChatMessage]:
    """
    Load all messages for a given session from Supabase, ordered by creation time.

    Returns an empty list if Supabase is not configured or if the session has no messages.
    """
    if not self._client:
      logger.debug("Cannot load messages: Supabase client not available")
      return []

    try:
      logger.debug(f"Loading messages from Supabase for session {session_id}")
      result = (
        self._client.table("conversation_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
      )

      data = getattr(result, "data", None)
      if not isinstance(data, list):
        logger.warning(f"Unexpected response format when loading messages for session {session_id}")
        return []

      messages: List[ChatMessage] = []
      for row in data:
        try:
          # Parse metadata if present
          metadata = None
          if row.get("metadata"):
            metadata = ChatMessageMetadata(**row["metadata"])

          # Create ChatMessage from database row
          message = ChatMessage(
            id=row["message_id"],
            role=ChatMessageRole(row["role"]),
            content=row["content"],
            metadata=metadata,
          )
          messages.append(message)
        except Exception as e:
          logger.warning(
            f"Failed to parse message {row.get('message_id', 'unknown')}: {str(e)}",
            extra={"session_id": session_id}
          )
          continue

      logger.info(f"Loaded {len(messages)} message(s) from Supabase for session {session_id}")
      return messages

    except Exception as e:
      logger.warning(
        f"Failed to load messages from Supabase for session {session_id}: {str(e)}",
        extra={"session_id": session_id}
      )
      return []

  def log_messages(
    self,
    session_id: str,
    messages: Iterable[ChatMessage],
    sheet_context: Optional[SheetContext] = None,
  ) -> None:
    """
    Persist a batch of messages for a given session.

    Each ChatMessage becomes a row in the conversation_messages table with a
    simple, flat structure.
    """
    if not self._client:
      return

    sheet_tab_id = self._get_or_create_sheet_tab(sheet_context) if sheet_context else None

    rows: List[dict] = []
    for msg in messages:
      rows.append(
        {
          "session_id": session_id,
          "message_id": msg.id,
          "role": msg.role.value,
          "content": msg.content,
          "metadata": msg.metadata.model_dump(exclude_none=True)
          if msg.metadata is not None
          else None,
          "sheet_tab_id": sheet_tab_id,
        }
      )

    if not rows:
      logger.debug("No messages to log")
      return

    try:
      logger.debug(f"Logging {len(rows)} message(s) to Supabase for session {session_id}")
      self._client.table("conversation_messages").insert(rows).execute()
      logger.debug(f"Successfully logged {len(rows)} message(s)")
    except Exception as e:
      # Persistence failures should not break the chat experience.
      logger.warning(
          f"Failed to persist {len(rows)} message(s) to Supabase: {str(e)}",
          extra={"session_id": session_id, "message_count": len(rows)}
      )
      return

  def _get_or_create_sheet_tab(self, ctx: SheetContext) -> Optional[str]:
    """
    Ensure there is a sheet_tabs row for the given SheetContext and return its id.

    If spreadsheetId or sheetTitle is missing, no relation is stored.
    """
    if not self._client:
      return None

    spreadsheet_raw = ctx.spreadsheetId or ""
    sheet_title = ctx.sheetTitle or ""
    if not spreadsheet_raw or not sheet_title:
      return None

    spreadsheet_id = self._extract_spreadsheet_id(spreadsheet_raw)
    if not spreadsheet_id:
      return None

    if spreadsheet_raw.startswith("http://") or spreadsheet_raw.startswith("https://"):
      spreadsheet_url = spreadsheet_raw
    else:
      spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    try:
      # Look up existing tab first
      existing = (
        self._client.table("sheet_tabs")
        .select("id")
        .eq("spreadsheet_id", spreadsheet_id)
        .eq("sheet_title", sheet_title)
        .limit(1)
        .execute()
      )
      data = getattr(existing, "data", None)
      if isinstance(data, list) and data:
        return data[0].get("id")

      # Insert new row
      created = (
        self._client.table("sheet_tabs")
        .insert(
          {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": spreadsheet_url,
            "sheet_title": sheet_title,
          }
        )
        .execute()
      )
      cdata = getattr(created, "data", None)
      if isinstance(cdata, list) and cdata:
        return cdata[0].get("id")
    except Exception:
      return None

    return None

  @staticmethod
  def _extract_spreadsheet_id(value: str) -> Optional[str]:
    """
    Extract a Google Sheets spreadsheet ID from either a raw ID or a full URL.
    """
    if not value:
      return None
    if value.startswith("http://") or value.startswith("https://"):
      marker = "/d/"
      try:
        start = value.index(marker) + len(marker)
        rest = value[start:]
        end = rest.find("/")
        if end == -1:
          return rest
        return rest[: end]
      except ValueError:
        return None
    return value
