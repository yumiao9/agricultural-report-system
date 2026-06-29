"""Structured logging setup."""

import logging
import sys

from backend.config import settings


def setup_logger(name: str) -> logging.Logger:
    """Create a logger with consistent formatting."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger


# Module-level loggers
orchestrator_logger = setup_logger("orchestrator")
search_logger = setup_logger("search")
fetcher_logger = setup_logger("fetcher")
extractor_logger = setup_logger("extractor")
llm_logger = setup_logger("llm")
