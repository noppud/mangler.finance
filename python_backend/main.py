from __future__ import annotations

import os

import uvicorn

from .api import app
from .logging_config import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":
  port = int(os.getenv("PORT", "8000"))

  # Log startup configuration
  logger.info("=" * 60)
  logger.info("Starting FastAPI application")
  logger.info("=" * 60)
  logger.info(f"Port: {port}")
  logger.info(f"Host: 0.0.0.0")
  logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
  logger.info(f"Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
  logger.info(f"Log Format: {os.getenv('LOG_FORMAT', 'json (auto-detected)')}")

  # Log feature availability
  has_supabase = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
  has_credentials = os.path.exists(os.getenv("DEFAULT_CREDENTIALS_PATH", "")) if os.getenv("DEFAULT_CREDENTIALS_PATH") else False
  has_spreadsheet = bool(os.getenv("DEFAULT_SPREADSHEET_URL"))

  logger.info("Feature availability:")
  logger.info(f"  - Supabase: {'✓' if has_supabase else '✗'} (Conversation logging & snapshots)")
  logger.info(f"  - Google Sheets credentials: {'✓' if has_credentials else '✗'} (Sheet tools)")
  logger.info(f"  - Default spreadsheet: {'✓' if has_spreadsheet else '✗'}")

  if not has_credentials:
    logger.warning("⚠️  Google Sheets credentials not configured - /tools/* endpoints will return 503")
    logger.warning(f"   DEFAULT_CREDENTIALS_PATH env var: {os.getenv('DEFAULT_CREDENTIALS_PATH', '(not set)')}")

  if not has_supabase:
    logger.warning("⚠️  Supabase not configured - conversation logging and snapshots disabled")

  logger.info("=" * 60)

  uvicorn.run("main:app", host="0.0.0.0", port=port)
