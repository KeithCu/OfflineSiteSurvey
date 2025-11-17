"""Pytest configuration and fixtures for Site Survey tests."""
import pytest
import tempfile
import os
from flask import Flask
from backend.app import create_app
from backend.models import db


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    # Create temporary database for testing
    db_fd, db_path = tempfile.mkstemp()

    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
    }

    app = create_app(test_config)

    with app.app_context():
        db.create_all()

    yield app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def test_db():
    """Create a temporary test database for frontend tests."""
    from src.survey_app.local_db import LocalDatabase

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Initialize database
    test_db = LocalDatabase(db_path)

    yield test_db

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    os.close(db_fd)
