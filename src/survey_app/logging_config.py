"""Logging configuration for frontend."""
import logging
import sys


def setup_logging():
    """Setup logging configuration for the frontend.

    Uses console-only logging suitable for Toga applications.
    """
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )

    # Console handler (only for frontend - Toga apps typically don't write to files)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handler to root logger
    logger.addHandler(console_handler)

    return logger
