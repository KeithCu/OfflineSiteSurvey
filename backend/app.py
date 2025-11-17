"""Flask application factory for Site Survey backend."""
from flask import Flask
import os
from appdirs import user_data_dir
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from .models import db, create_crr_tables
from .blueprints import projects, sites, surveys, templates, photos, crdt
from .cli import init_db_command, check_photo_integrity_command
from .logging_config import setup_logging


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

    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Database configuration
    DB_NAME = 'backend_main.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Load the cr-sqlite extension
    @event.listens_for(Engine, "connect")
    def load_crsqlite_extension(db_conn, conn_record):
        data_dir = user_data_dir("crsqlite", "vlcn.io")
        lib_path = os.path.join(data_dir, 'crsqlite.so')

        if not os.path.exists(lib_path):
            lib_path = os.path.join(os.path.dirname(__file__), 'lib', 'crsqlite.so')

        db_conn.enable_load_extension(True)
        db_conn.load_extension(lib_path)

    # Create CRR tables after creation
    event.listen(db.metadata, 'after_create', create_crr_tables)

    # Register blueprints
    app.register_blueprint(projects.bp)
    app.register_blueprint(sites.bp)
    app.register_blueprint(surveys.bp)
    app.register_blueprint(templates.bp)
    app.register_blueprint(photos.bp)
    app.register_blueprint(crdt.bp)

    # Register CLI commands
    app.cli.add_command(init_db_command)
    app.cli.add_command(check_photo_integrity_command)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)