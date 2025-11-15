"""
Centralized logging configuration for the application.
Provides structured logging with JSON formatting for production environments.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
import os


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing by log aggregation tools.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "spreadsheet_id"):
            log_data["spreadsheet_id"] = record.spreadsheet_id
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method

        # Add any custom extra data
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development environments.
    Makes logs easier to read in the terminal.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, self.RESET)

        # Format the base message
        formatted = f"{log_color}[{record.levelname}]{self.RESET} "
        formatted += f"{record.name} - {record.getMessage()}"

        # Add extra context if available
        extras = []
        if hasattr(record, "request_id"):
            extras.append(f"request_id={record.request_id}")
        if hasattr(record, "session_id"):
            extras.append(f"session_id={record.session_id}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")
        if hasattr(record, "status_code"):
            extras.append(f"status={record.status_code}")

        if extras:
            formatted += f" ({', '.join(extras)})"

        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def setup_logging(
    log_level: str = None,
    use_json: bool = None,
    logger_name: str = None
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Defaults to LOG_LEVEL env var or INFO.
        use_json: Whether to use JSON formatting. Defaults to True in production.
                  Determined by ENVIRONMENT env var or LOG_FORMAT env var.
        logger_name: Name of the logger to configure. If None, configures root logger.

    Returns:
        Configured logger instance.
    """
    # Determine log level from env or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Determine format from env or parameter
    if use_json is None:
        environment = os.getenv("ENVIRONMENT", "production").lower()
        log_format = os.getenv("LOG_FORMAT", "").lower()

        # Use JSON in production or if explicitly set
        use_json = environment == "production" or log_format == "json"

    # Get or create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))

    # Set formatter based on environment
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to avoid duplicate logs
    if logger_name:
        logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the logger (typically __name__ from the calling module).

    Returns:
        Configured logger instance.
    """
    return setup_logging(logger_name=name)


# Configure root logger on import
setup_logging()
