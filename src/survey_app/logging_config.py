"""Logging configuration for frontend."""
import logging
import sys
import os
from datetime import datetime


class ColorFormatter(logging.Formatter):
    """Color-coded formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            colored_level = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            record.levelname = colored_level

        return super().format(record)


def setup_logging():
    """Setup logging configuration for the frontend.

    Uses console-only logging suitable for Toga applications.
    Enhanced with colors and configurable levels.
    """
    # Get log level from environment
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create formatters
    color_formatter = ColorFormatter(
        '%(asctime)s %(levelname)s %(name)-25s %(message)s'
    )

    plain_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(name)-25s %(message)s'
    )

    # Determine if colors are supported
    use_colors = os.getenv('LOG_COLORS', 'true').lower() in ('true', '1', 'yes')

    # Console handler (only for frontend - Toga apps typically don't write to files)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if use_colors and sys.stdout.isatty():
        console_handler.setFormatter(color_formatter)
    else:
        console_handler.setFormatter(plain_formatter)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handler to root logger
    logger.addHandler(console_handler)

    # Configure specific loggers to reduce noise
    logging.getLogger('PIL').setLevel(logging.WARNING)  # Reduce PIL noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    logger.info(f"Frontend logging initialized (level: {log_level_str})")

    return logger
