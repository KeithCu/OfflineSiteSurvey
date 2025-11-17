"""Logging configuration for backend."""
import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(app=None):
    """Setup logging configuration for the backend.

    Args:
        app: Flask app instance for additional setup (optional)
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s'
    )

    # File handler with rotation
    log_file = os.path.join(logs_dir, 'backend.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to root logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Set specific loggers if needed
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask dev server noise
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Reduce SQLAlchemy noise

    return logger
