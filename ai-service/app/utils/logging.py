"""Logging configuration with PII sanitization and structured format."""

import logging
import re
import sys
from typing import Any, Dict


# Regex patterns for common sensitive personal information
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
BEARER_REGEX = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE)


class PIISanitizingFilter(logging.Filter):
    """Filter that intercepts log records and scrubs potential PII."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)
        return True

    @staticmethod
    def sanitize(text: str) -> str:
        text = EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
        text = PHONE_REGEX.sub("[PHONE_REDACTED]", text)
        text = BEARER_REGEX.sub("Bearer [TOKEN_REDACTED]", text)
        return text


def setup_logger(name: str = "skillbridge_ai", level: str = "INFO") -> logging.Logger:
    """Configures and returns a logger instance with sanitization."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(PIISanitizingFilter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
