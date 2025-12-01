# app/logger.py
import logging
import json
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from pathlib import Path


def setup_logger(app):
    """Setup advanced logging for Flask with JSON format and separate handlers"""

    log_dir = Path(app.config.get("LOG_DIR", "logs"))
    log_dir.mkdir(exist_ok=True)

    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # --- Formatter (JSON for structured logging) ---
    json_format = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp"},
    )

    text_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # --- Console Handler (stdout) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(text_format)

    # --- File Handlers ---
    access_handler = RotatingFileHandler(log_dir / "access.log", maxBytes=5 * 1024 * 1024, backupCount=5)
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(json_format)

    error_handler = RotatingFileHandler(log_dir / "error.log", maxBytes=5 * 1024 * 1024, backupCount=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_format)

    # --- Attach handlers ---
    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)
    app.logger.addHandler(access_handler)
    app.logger.addHandler(error_handler)

    # --- Non propagate (avoid duplicate logs) ---
    app.logger.propagate = False

    app.logger.info("✅ Advanced logger initialized")


def redact_sensitive_data(record: dict) -> dict:
    """Remove sensitive fields from log record before writing"""
    sensitive_keys = {"AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID", "PASSWORD", "TOKEN"}
    return {k: ("***" if any(s in k.upper() for s in sensitive_keys) else v) for k, v in record.items()}

