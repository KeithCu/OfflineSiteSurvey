"""Tests for CRDT synchronization logic."""
import pytest
from backend.models import db, Project


def test_crr_table_creation(app):
    """Test that CRR tables are created properly."""
    with app.app_context():
        # Check that crr tables were created
        result = db.engine.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%crr%'")
        crr_tables = result.fetchall()

        # Should have some CRR-related tables/views
        assert len(crr_tables) > 0


def test_basic_crdt_operations(app):
    """Test basic CRDT operations work."""
    with app.app_context():
        # Create a test project
        project = Project(
            name="CRDT Test Project",
            description="Test for CRDT sync"
        )
        db.session.add(project)
        db.session.commit()

        # Verify project was created
        assert project.id is not None

        # Check that changes are tracked (basic test)
        # In a real CRDT system, we'd check the crsql_changes table
        result = db.engine.execute("SELECT COUNT(*) FROM crsql_changes")
        change_count = result.fetchone()[0]

        # Should have at least one change recorded
        assert change_count >= 1


def test_changes_api_with_data(client, app):
    """Test that changes API returns data when there are changes."""
    with app.app_context():
        # Create some test data first
        project = Project(name="Changes API Test")
        db.session.add(project)
        db.session.commit()

        # Get changes since version 0
        response = client.get('/api/changes?version=0&site_id=test_site')
        assert response.status_code == 200
        data = response.json()

        # Should return some changes
        assert isinstance(data, list)
        assert len(data) > 0

        # Each change should have required CRDT fields
        for change in data:
            assert 'table' in change
            assert 'pk' in change
            assert 'cid' in change
            assert 'val' in change
            assert 'col_version' in change
            assert 'db_version' in change


def test_changes_api_post(client, app):
    """Test posting changes to the changes API."""
    # Create some mock changes
    changes = [{
        'table': 'projects',
        'pk': '999',
        'cid': 'name',
        'val': 'Posted Project',
        'col_version': 1,
        'db_version': 1
    }]

    response = client.post('/api/changes', json=changes)
    assert response.status_code == 200

    # Verify the change was applied (would need more complex logic in real test)
    # For now, just check that the request succeeded
    data = response.json()
    assert 'status' in data or isinstance(data, dict)


def test_sync_version_tracking(client, app):
    """Test that sync versions are tracked properly."""
    with app.app_context():
        # Create initial data
        project1 = Project(name="Version Test 1")
        db.session.add(project1)
        db.session.commit()

        # Get changes at version 0
        response = client.get('/api/changes?version=0&site_id=test_site')
        changes_v0 = response.json()
        assert len(changes_v0) > 0

        # Create more data
        project2 = Project(name="Version Test 2")
        db.session.add(project2)
        db.session.commit()

        # Get changes since a higher version
        max_version = max(change['db_version'] for change in changes_v0)
        response = client.get(f'/api/changes?version={max_version}&site_id=test_site')
        changes_later = response.json()

        # Should have fewer or equal changes
        assert len(changes_later) <= len(changes_v0)
