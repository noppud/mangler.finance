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

  # Check for missing environment variables
  logger.info("Checking environment variables...")

  missing_critical = []
  missing_optional = []

  # Critical environment variables
  if not os.getenv("OPENROUTER_API_KEY"):
    missing_critical.append("OPENROUTER_API_KEY")

  # Supabase configuration (both required for feature to work)
  has_supabase_url = bool(os.getenv("SUPABASE_URL"))
  has_supabase_key = bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY"))
  has_supabase = has_supabase_url and has_supabase_key

  if not has_supabase_url:
    missing_optional.append("SUPABASE_URL")
  if not has_supabase_key:
    missing_optional.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_KEY")

  # Google Sheets credentials (either JSON or FILE path)
  has_google_creds = bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"))
  if not has_google_creds:
    missing_optional.append("GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE")

  # Default spreadsheet URL
  has_spreadsheet = bool(os.getenv("DEFAULT_SPREADSHEET_URL"))
  if not has_spreadsheet:
    missing_optional.append("DEFAULT_SPREADSHEET_URL")

  # Legacy credentials path check
  has_credentials = os.path.exists(os.getenv("DEFAULT_CREDENTIALS_PATH", "")) if os.getenv("DEFAULT_CREDENTIALS_PATH") else False

  # Log missing critical variables (errors)
  if missing_critical:
    logger.error("=" * 60)
    logger.error("❌ CRITICAL: Missing required environment variables!")
    for var in missing_critical:
      logger.error(f"   - {var}")
    logger.error("=" * 60)
    logger.error("Application may fail to start or function correctly.")
    logger.error("Please set these variables in .env file or environment.")
    logger.error("=" * 60)

  # Log missing optional variables (warnings)
  if missing_optional:
    logger.warning("Missing optional environment variables:")
    for var in missing_optional:
      logger.warning(f"   - {var}")
    logger.warning("Some features may be disabled.")

  # Log feature availability
  logger.info("Feature availability:")
  logger.info(f"  - Supabase: {'✓' if has_supabase else '✗'} (Conversation logging & snapshots)")
  logger.info(f"  - Google Sheets credentials: {'✓' if (has_google_creds or has_credentials) else '✗'} (Sheet tools)")
  logger.info(f"  - Default spreadsheet: {'✓' if has_spreadsheet else '✗'}")

  if not (has_google_creds or has_credentials):
    logger.warning("⚠️  Google Sheets credentials not configured - /tools/* endpoints will return 503")
    logger.warning(f"   DEFAULT_CREDENTIALS_PATH env var: {os.getenv('DEFAULT_CREDENTIALS_PATH', '(not set)')}")

  if not has_supabase:
    logger.warning("⚠️  Supabase not configured - conversation logging and snapshots disabled")

  logger.info("=" * 60)

  uvicorn.run("main:app", host="0.0.0.0", port=port)
