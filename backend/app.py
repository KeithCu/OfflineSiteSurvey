"""Flask application factory for Site Survey backend."""
# Monkey patch sqlite3 to use pysqlite3-binary if available
# This is required for load_extension support on many Linux systems
import sys
try:
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass

from flask import Flask
import os
import logging
import platform
from pathlib import Path
from appdirs import user_data_dir
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from .models import db, create_crr_tables
from .blueprints import config, projects, sites, surveys, templates, photos, crdt, auth, teams
from .cli import init_db_command, check_photo_integrity_command, check_referential_integrity_command
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


def create_app(test_config=None):
    """Flask application factory for the Site Survey backend.

    Creates and configures a Flask application instance with:
    - SQLAlchemy database integration
    - CRDT sqlite extension loading
    - Blueprint registration for API endpoints
    - CLI command registration
    - Logging configuration

    Args:
        test_config (dict, optional): Configuration overrides for testing

    Returns:
        Flask: Configured Flask application instance
    """
    # Setup logging first
    setup_logging()
    logger.info("Starting Flask application initialization")

    app = Flask(__name__, instance_relative_config=True)
    logger.debug(f"Flask app created with instance path: {app.instance_path}")

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        config_loaded = app.config.from_pyfile('config.py', silent=True)
        if config_loaded:
            logger.info("Loaded configuration from instance/config.py")
        else:
            logger.debug("No instance config file found, using defaults")
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)
        logger.info("Loaded test configuration")

    # Ensure the instance folder exists
    try:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created instance directory: {app.instance_path}")
    except OSError:
        logger.debug(f"Instance directory already exists: {app.instance_path}")

    # Database configuration
    # Only set default database URI if not already set (e.g., by tests)
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        DB_NAME = 'backend_main.db'
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite+pysqlite:///{DB_NAME}'
        logger.info(f"Configured database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    else:
        logger.info(f"Using existing database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    logger.debug("SQLAlchemy track modifications disabled")

    db.init_app(app)
    logger.info("SQLAlchemy database initialized")

    # Load the cr-sqlite extension
    @event.listens_for(Engine, "connect")
    def load_crsqlite_extension(db_conn, conn_record):
        # Check environment variable first (for deployment flexibility)
        lib_path = os.getenv('CRSQLITE_LIB_PATH')
        
        if lib_path and Path(lib_path).exists():
            lib_path = Path(lib_path)
            logger.debug(f"Using cr-sqlite extension from CRSQLITE_LIB_PATH: {lib_path}")
        else:
            # Fallback to user data directory
            data_dir = user_data_dir("crsqlite", "vlcn.io")
            # Determine extension based on platform
            system = platform.system()
            ext = '.dll' if system == 'Windows' else '.dylib' if system == 'Darwin' else '.so'
            lib_path = Path(data_dir) / f'crsqlite{ext}'

            if not lib_path.exists():
                # Last resort: relative to backend directory (development only)
                lib_path = Path(__file__).parent / 'lib' / f'crsqlite{ext}'
                logger.debug(f"Using fallback cr-sqlite extension path: {lib_path}")
            else:
                logger.debug(f"Using cr-sqlite extension from user data dir: {lib_path}")

        if not lib_path.exists():
            error_msg = (
                f"cr-sqlite extension not found. "
                f"Set CRSQLITE_LIB_PATH environment variable or install via setup_crsqlite.sh"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            db_conn.enable_load_extension(True)
            db_conn.load_extension(str(lib_path))
            logger.info("Successfully loaded cr-sqlite extension for CRDT support")
        except Exception as e:
            logger.error(f"Failed to load cr-sqlite extension from {lib_path}: {e}", exc_info=True)
            raise

    # Register event listener for CRR table creation on new database creation
    # Note: This only fires when tables are first created. For existing databases,
    # CRR tables must be initialized explicitly (see init_db_command in cli.py)
    event.listen(db.metadata, 'after_create', create_crr_tables)
    logger.info("Registered CRR table creation event listener")

    # Register blueprints
    logger.info("Registering API blueprints")
    app.register_blueprint(auth.bp)
    logger.debug("Registered auth blueprint")
    app.register_blueprint(teams.bp)
    logger.debug("Registered teams blueprint")
    app.register_blueprint(config.bp)
    logger.debug("Registered config blueprint")
    app.register_blueprint(projects.bp)
    logger.debug("Registered projects blueprint")
    app.register_blueprint(sites.bp)
    logger.debug("Registered sites blueprint")
    app.register_blueprint(surveys.bp)
    logger.debug("Registered surveys blueprint")
    app.register_blueprint(templates.bp)
    logger.debug("Registered templates blueprint")
    app.register_blueprint(photos.bp)
    logger.debug("Registered photos blueprint")
    app.register_blueprint(crdt.bp)
    logger.debug("Registered crdt blueprint")
    logger.info("All API blueprints registered successfully")

    # Initialize authentication
    auth.init_auth(app)
    logger.info("Authentication system initialized")

    # Register CLI commands
    app.cli.add_command(init_db_command)
    app.cli.add_command(check_photo_integrity_command)
    app.cli.add_command(check_referential_integrity_command)
    from .cli import run_worker_command
    app.cli.add_command(run_worker_command)
    logger.info("CLI commands registered: init-db, check-photo-integrity, check-referential-integrity, run-worker")

    logger.info("Flask application initialization completed successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)