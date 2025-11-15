from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

try:
    from supabase import Client, create_client
except ImportError:
    # Supabase is optional - if not installed, all functions return None
    Client = None  # type: ignore
    create_client = None  # type: ignore

from .llm import _load_env_from_local_files
from .logging_config import get_logger

logger = get_logger(__name__)


_supabase_client: Optional["Client"] = None


def get_supabase_client() -> Optional["Client"]:
  """
  Lazily create and cache a Supabase client, if configured.

  Configuration is read from environment variables, which are loaded from
  local .env-style files using the same mechanism as the LLM client.
  """
  global _supabase_client

  # If supabase package is not installed, return None
  if create_client is None or Client is None:
    logger.warning("Supabase package not installed - client unavailable")
    return None

  if _supabase_client is not None:
    return _supabase_client

  # Ensure env vars are populated from local config files if present
  _load_env_from_local_files()

  url = os.getenv("SUPABASE_URL")
  key = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
  )

  if not url or not key:
    logger.warning(
        "Supabase client not configured - missing URL or key",
        extra={
            "has_url": bool(url),
            "has_service_role_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "has_service_key": bool(os.getenv("SUPABASE_SERVICE_KEY")),
            "has_anon_key": bool(os.getenv("SUPABASE_ANON_KEY")),
        }
    )
    return None

  try:
    logger.info(f"Creating Supabase client for URL: {url[:30]}...")
    _supabase_client = create_client(url, key)
    logger.info("Supabase client created successfully")
  except Exception as e:
    # If Supabase is misconfigured, fall back to no-op mode.
    logger.error(f"Failed to create Supabase client: {str(e)}", exc_info=True)
    _supabase_client = None

  return _supabase_client

