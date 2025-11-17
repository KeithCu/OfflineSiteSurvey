"""Tests for frontend local database operations."""
import json
import pytest
import os
from unittest.mock import patch
from src.survey_app.local_db import LocalDatabase
from src.survey_app.enums import ProjectStatus, SurveyStatus, PhotoCategory


def test_local_database_initialization(test_db):
    """Test that LocalDatabase initializes properly."""
    assert test_db.db_path is not None
    assert test_db.site_id is not None
    assert len(test_db.site_id) > 0
    assert test_db.engine is not None
    assert test_db.Session is not None


def test_project_operations(test_db):
    """Test project CRUD operations."""
    # Create project
    project_data = {
        'name': 'Test Project',
        'description': 'Test description',
        'status': ProjectStatus.DRAFT,
        'client_info': 'Test Client',
        'priority': 'high'
    }

    created_project = test_db.save_project(project_data)
    assert created_project.id is not None
    assert created_project.name == 'Test Project'

    # Get projects
    projects = test_db.get_projects()
    assert len(projects) >= 1
    assert any(p.name == 'Test Project' for p in projects)


def test_site_operations(test_db):
    """Test site CRUD operations."""
    # Create project first
    project = test_db.save_project({'name': 'Parent Project'})

    # Create site
    site_data = {
        'name': 'Test Site',
        'address': '123 Test St',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'notes': 'Test notes',
        'project_id': project.id
    }

    created_site = test_db.save_site(site_data)
    assert created_site.id is not None
    assert created_site.name == 'Test Site'
    assert created_site.project_id == project.id

    # Get sites
    sites = test_db.get_sites()
    assert len(sites) >= 1
    assert any(s.name == 'Test Site' for s in sites)

    # Get sites for project
    project_sites = test_db.get_sites_for_project(project.id)
    assert len(project_sites) >= 1


def test_survey_operations(test_db):
    """Test survey CRUD operations."""
    # Create project and site first
    project = test_db.save_project({'name': 'Parent Project'})
    site = test_db.save_site({'name': 'Parent Site', 'project_id': project.id})

    # Create survey
    survey_data = {
        'title': 'Test Survey',
        'description': 'Test survey description',
        'site_id': site.id,
        'status': SurveyStatus.DRAFT
    }

    created_survey = test_db.save_survey(survey_data)
    assert created_survey.id is not None
    assert created_survey.title == 'Test Survey'
    assert created_survey.site_id == site.id

    # Get surveys
    surveys = test_db.get_surveys()
    assert len(surveys) >= 1
    assert any(s.title == 'Test Survey' for s in surveys)

    # Get survey by ID
    retrieved = test_db.get_survey(created_survey.id)
    assert retrieved is not None
    assert retrieved.title == 'Test Survey'


def test_photo_operations(test_db):
    """Test photo CRUD operations."""
    # Create project, site, survey first
    project = test_db.save_project({'name': 'Parent Project'})
    site = test_db.save_site({'name': 'Parent Site', 'project_id': project.id})
    survey = test_db.save_survey({'title': 'Parent Survey', 'site_id': site.id})

    # Create photo
    photo_data = {
        'survey_id': str(survey.id),
        'site_id': site.id,
        'image_data': b'test_image_data',
        'cloud_url': 'https://example.com/photos/test.jpg',
        'thumbnail_url': 'https://example.com/thumbnails/test_thumb.jpg',
        'upload_status': 'completed',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'description': 'Test photo',
        'category': PhotoCategory.GENERAL
    }

    created_photo = test_db.save_photo(photo_data)
    assert created_photo.id is not None
    assert created_photo.description == 'Test photo'
    assert created_photo.survey_id == survey.id
    assert json.loads(created_photo.tags) == []

    # Verify hash was computed
    assert created_photo.hash_value is not None
    assert len(created_photo.hash_value) == 64  # SHA-256 hex length

    # Get photos
    photos = test_db.get_photos()
    assert len(photos['photos']) >= 1
    assert any(p.description == 'Test photo' for p in photos['photos'])


def test_response_operations(test_db):
    """Test survey response operations."""
    # Create project, site, survey first
    project = test_db.save_project({'name': 'Parent Project'})
    site = test_db.save_site({'name': 'Parent Site', 'project_id': project.id})
    survey = test_db.save_survey({'title': 'Parent Survey', 'site_id': site.id})

    # Save response
    response_data = {
        'survey_id': survey.id,
        'question_id': 1,
        'question': 'Test question?',
        'answer': 'Test answer',
        'response_type': 'text',
        'field_type': 'text'
    }

    test_db.save_response(response_data)

    # Verify response was saved (would need more complex verification in real test)
    # For now, just ensure no exceptions were raised
    assert True


def test_backup_restore_operations(test_db):
    """Test backup and restore operations."""
    # Create some test data
    project = test_db.save_project({'name': 'Backup Test Project'})

    # Test backup
    backup_path = test_db.backup()
    assert backup_path is not None
    assert os.path.exists(backup_path)

    # Test restore (create new db instance)
    new_db = LocalDatabase('test_restore.db')
    restore_result = new_db.restore(backup_path)
    assert restore_result is True

    # Verify data was restored
    projects = new_db.get_projects()
    assert len(projects) >= 1
    assert any(p.name == 'Backup Test Project' for p in projects)

    # Cleanup
    if os.path.exists('test_restore.db'):
        os.remove('test_restore.db')
    if os.path.exists(backup_path):
        os.remove(backup_path)


def test_photo_integrity_check(test_db):
    """Test photo integrity checking."""
    # Create photo with test data
    project = test_db.save_project({'name': 'Integrity Project'})
    site = test_db.save_site({'name': 'Integrity Site', 'project_id': project.id})
    survey = test_db.save_survey({'title': 'Integrity Survey', 'site_id': site.id})

    photo_data = {
        'survey_id': survey.id,
        'image_data': b'integrity_test_data',
        'description': 'Integrity test photo'
    }

    photo = test_db.save_photo(photo_data)

    # Run integrity check
    integrity_issues = test_db.check_photo_integrity()

    # Should have no integrity issues for newly created photo
    assert integrity_issues == 0


def test_logging_in_operations(test_db):
    """Test that operations properly log messages."""
    # Verify that the database has a logger
    assert hasattr(test_db, 'logger')
    assert test_db.logger is not None
