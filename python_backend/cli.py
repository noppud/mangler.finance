from __future__ import annotations

import argparse
import sys
import uuid

from .backend import PythonChatBackend
from .memory import ConversationStore
from .models import ChatMessageRole, SheetContext
from .service import ChatService


def build_arg_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description="CLI chat client for the Sheet Mangler backend"
  )
  parser.add_argument(
    "--session-id",
    help="Session ID to use for conversation memory (default: random UUID)",
  )
  parser.add_argument(
    "--sheet-id",
    help="Optional Google Sheets spreadsheet ID to include in context",
  )
  parser.add_argument(
    "--sheet-title",
    help="Optional sheet title to include in context",
  )
  return parser


def main(argv: list[str] | None = None) -> int:
  parser = build_arg_parser()
  args = parser.parse_args(argv)

  session_id = args.session_id or str(uuid.uuid4())

  store = ConversationStore()
  backend = PythonChatBackend()
  service = ChatService(backend=backend, store=store)

  sheet_context = SheetContext(
    spreadsheetId=args.sheet_id,
    sheetTitle=args.sheet_title,
  )

  print("Using Python backend (no Next.js dependency)")
  print(f"Session ID: {session_id}")
  print("Type your message and press Enter. Ctrl+C or EOF to exit.\n")

  try:
    while True:
      try:
        user_input = input("You: ")
      except EOFError:
        print()
        break

      if not user_input.strip():
        continue

      try:
        response = service.simple_chat(
          session_id=session_id,
          user_content=user_input,
          sheet_context=sheet_context,
        )
      except Exception as exc:  # pragma: no cover - CLI error surface
        print(f"[error] {exc}")
        continue

      for msg in response.messages:
        prefix = "Assistant"
        if msg.role == ChatMessageRole.tool:
          prefix = "Tool"
        elif msg.role == ChatMessageRole.system:
          prefix = "System"

        print(f"{prefix}: {msg.content}")

  except KeyboardInterrupt:
    print("\nExiting...")

  return 0


if __name__ == "__main__":  # pragma: no cover
  raise SystemExit(main())
