"""Logging configuration for backend."""
import logging
import os
import json
from logging.handlers import RotatingFileHandler
from shared.models import now


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for better log analysis."""

    def format(self, record):
        # Add structured fields
        log_entry = {
            'timestamp': now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)


def setup_logging(app=None):
    """Setup logging configuration for the backend.

    Args:
        app: Flask app instance for additional setup (optional)
    """
    # Get log level from environment
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create formatters
    structured_formatter = StructuredFormatter()
    simple_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(name)-20s %(message)s'
    )

    # File handler with rotation (structured JSON)
    log_file = os.path.join(logs_dir, 'backend.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(structured_formatter)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handlers to root logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask dev server noise
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Reduce SQLAlchemy noise

    # Set higher level for some noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    logger.info("Logging initialized", extra={
        'extra_fields': {
            'log_level': log_level_str,
            'log_file': log_file,
            'structured_logging': True
        }
    })

    return logger
