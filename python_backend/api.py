from __future__ import annotations

from fastapi import FastAPI

from .backend import PythonChatBackend
from .memory import ConversationStore
from .models import ChatRequest, ChatResponse
from .service import ChatService


store = ConversationStore()
backend = PythonChatBackend()
service = ChatService(backend=backend, store=store)

app = FastAPI(title="Sheet Mangler Chat API (Python Frontend)")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
  """
  Single chat endpoint that mirrors the existing /api/chat contract.

  For now this proxies to the Next.js backend while adding conversation
  memory keyed by sessionId.
  """
  # This implementation assumes the client is sending the full message history.
  # If you prefer CLI-style incremental messages, use ChatService.simple_chat
  # directly or adapt this endpoint accordingly.
  return service.chat(request)

