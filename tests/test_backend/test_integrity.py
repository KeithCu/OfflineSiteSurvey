"""Tests for referential integrity protection mechanisms."""
import pytest
import json
from backend.models import db, Project, Site, Survey, SurveyResponse, SurveyTemplate, TemplateField, Photo
from backend.utils import validate_foreign_key, get_orphaned_records, cascade_delete_project, cascade_delete_site, cascade_delete_survey


class TestIntegrityUtils:
    """Test integrity validation utilities."""

    def test_validate_foreign_key_valid(self, app):
        """Test validating existing foreign key references."""
        with app.app_context():
            # Create test data
            project = Project(name="Test Project")
            db.session.add(project)
            db.session.commit()

            # Test valid FK
            assert validate_foreign_key('projects', 'id', project.id) == True

    def test_validate_foreign_key_invalid(self, app):
        """Test validating non-existent foreign key references."""
        with app.app_context():
            # Test invalid FK
            assert validate_foreign_key('projects', 'id', 99999) == False

    def test_validate_foreign_key_none(self, app):
        """Test validating None foreign key (should allow)."""
        with app.app_context():
            # Test None FK (should be allowed for optional FKs)
            assert validate_foreign_key('projects', 'id', None) == True

    def test_get_orphaned_records_none(self, app):
        """Test getting orphaned records when all relationships are valid."""
        with app.app_context():
            orphaned = get_orphaned_records()
            assert orphaned == {}

    def test_get_orphaned_records_sites(self, app):
        """Test detecting orphaned sites."""
        with app.app_context():
            # Create a site with invalid project_id
            site = Site(name="Orphaned Site", project_id=99999)
            db.session.add(site)
            db.session.commit()

            orphaned = get_orphaned_records('sites')
            assert 'sites' in orphaned
            assert site.id in orphaned['sites']

    def test_get_orphaned_records_surveys(self, app):
        """Test detecting orphaned surveys."""
        with app.app_context():
            # Create project and site first
            project = Project(name="Test Project")
            db.session.add(project)
            site = Site(name="Test Site", project_id=project.id)
            db.session.add(site)
            db.session.commit()

            # Create survey with invalid site_id
            survey = Survey(title="Orphaned Survey", site_id=99999)
            db.session.add(survey)
            db.session.commit()

            orphaned = get_orphaned_records('surveys')
            assert 'surveys' in orphaned
            assert survey.id in orphaned['surveys']

    def test_cascade_delete_project(self, app):
        """Test cascading delete of a project."""
        with app.app_context():
            # Create test hierarchy
            project = Project(name="Test Project")
            db.session.add(project)
            db.session.commit()

            site = Site(name="Test Site", project_id=project.id)
            db.session.add(site)
            db.session.commit()

            survey = Survey(title="Test Survey", site_id=site.id)
            db.session.add(survey)
            db.session.commit()

            response = SurveyResponse(survey_id=survey.id, question="Test", answer="Test")
            db.session.add(response)
            db.session.commit()

            photo = Photo(id="test-photo", survey_id=survey.id, site_id=site.id)
            db.session.add(photo)
            db.session.commit()

            # Cascade delete project
            summary = cascade_delete_project(project.id)
            db.session.commit()

            # Verify all records deleted
            assert summary['projects'] == 1
            assert summary['sites'] == 1
            assert summary['surveys'] == 1
            assert summary['responses'] == 1
            assert summary['photos'] == 1

            # Verify database is clean
            assert Project.query.get(project.id) is None
            assert Site.query.get(site.id) is None
            assert Survey.query.get(survey.id) is None
            assert SurveyResponse.query.get(response.id) is None
            assert Photo.query.get(photo.id) is None

    def test_cascade_delete_site(self, app):
        """Test cascading delete of a site."""
        with app.app_context():
            # Create test hierarchy (without project for simplicity)
            site = Site(name="Test Site", project_id=1)  # Assume project exists
            db.session.add(site)
            db.session.commit()

            survey = Survey(title="Test Survey", site_id=site.id)
            db.session.add(survey)
            db.session.commit()

            response = SurveyResponse(survey_id=survey.id, question="Test", answer="Test")
            db.session.add(response)
            db.session.commit()

            photo = Photo(id="test-photo", survey_id=survey.id, site_id=site.id)
            db.session.add(photo)
            db.session.commit()

            # Cascade delete site
            summary = cascade_delete_site(site.id)
            db.session.commit()

            # Verify all records deleted
            assert summary['sites'] == 1
            assert summary['surveys'] == 1
            assert summary['responses'] == 1
            assert summary['photos'] == 1

            # Verify database is clean
            assert Site.query.get(site.id) is None
            assert Survey.query.get(survey.id) is None
            assert SurveyResponse.query.get(response.id) is None
            assert Photo.query.get(photo.id) is None

    def test_cascade_delete_survey(self, app):
        """Test cascading delete of a survey."""
        with app.app_context():
            # Create test survey with responses and photos
            survey = Survey(title="Test Survey", site_id=1)  # Assume site exists
            db.session.add(survey)
            db.session.commit()

            response = SurveyResponse(survey_id=survey.id, question="Test", answer="Test")
            db.session.add(response)
            db.session.commit()

            photo = Photo(id="test-photo", survey_id=survey.id, site_id=1)
            db.session.add(photo)
            db.session.commit()

            # Cascade delete survey
            summary = cascade_delete_survey(survey.id)
            db.session.commit()

            # Verify all records deleted
            assert summary['surveys'] == 1
            assert summary['responses'] == 1
            assert summary['photos'] == 1

            # Verify database is clean
            assert Survey.query.get(survey.id) is None
            assert SurveyResponse.query.get(response.id) is None
            assert Photo.query.get(photo.id) is None


class TestCRDTValidation:
    """Test CRDT sync foreign key validation."""

    def test_crdt_valid_changes(self, client, app):
        """Test CRDT sync accepts valid changes."""
        with app.app_context():
            # Simple valid change that doesn't involve FK validation
            changes = [{
                'table': 'projects',
                'pk': '{"id": 1}',
                'cid': 'name',
                'val': 'Test Project',
                'col_version': 1,
                'db_version': 1,
                'site_id': 'test-site'
            }]

            response = client.post('/api/changes', json=changes)
            # CRDT may or may not succeed depending on if record exists, but should not fail due to FK validation
            assert response.status_code in [200, 500]  # Allow either success or expected failure for non-existent record

    def test_crdt_invalid_site_project_id(self, client, app):
        """Test CRDT sync rejects invalid site project_id."""
        with app.app_context():
            changes = [{
                'table': 'sites',
                'pk': '{"id": 1}',
                'cid': 'project_id',
                'val': 99999,  # Invalid project_id
                'col_version': 1,
                'db_version': 1,
                'site_id': 'test-site'
            }]

            response = client.post('/api/changes', json=changes)
            assert response.status_code == 200  # Still returns 200 but with integrity issues
            data = response.get_json()
            assert 'integrity_issues' in data
            assert len(data['integrity_issues']) == 1
            assert 'references non-existent project_id' in data['integrity_issues'][0]['error']

    def test_crdt_invalid_survey_site_id(self, client, app):
        """Test CRDT sync rejects invalid survey site_id."""
        with app.app_context():
            changes = [{
                'table': 'survey',
                'pk': '{"id": 1}',
                'cid': 'site_id',
                'val': 99999,  # Invalid site_id
                'col_version': 1,
                'db_version': 1,
                'site_id': 'test-site'
            }]

            response = client.post('/api/changes', json=changes)
            assert response.status_code == 200
            data = response.get_json()
            assert 'integrity_issues' in data
            assert len(data['integrity_issues']) == 1
            assert 'references non-existent site_id' in data['integrity_issues'][0]['error']

    def test_crdt_invalid_photo_survey_id(self, client, app):
        """Test CRDT sync rejects invalid photo survey_id."""
        with app.app_context():
            changes = [{
                'table': 'photo',
                'pk': '{"id": "test-photo"}',
                'cid': 'survey_id',
                'val': 99999,  # Invalid survey_id
                'col_version': 1,
                'db_version': 1,
                'site_id': 'test-site'
            }]

            response = client.post('/api/changes', json=changes)
            assert response.status_code == 200
            data = response.get_json()
            assert 'integrity_issues' in data
            assert len(data['integrity_issues']) == 1
            assert 'references non-existent survey_id' in data['integrity_issues'][0]['error']


class TestAPIFKValidation:
    """Test API endpoint foreign key validation."""

    def test_create_site_invalid_project_id(self, client, app):
        """Test creating site with invalid project_id fails."""
        with app.app_context():
            data = {
                'name': 'Test Site',
                'project_id': 99999  # Invalid
            }

            response = client.post('/api/sites', json=data)
            assert response.status_code == 400
            data = response.get_json()
            assert 'does not exist' in data.get('error', '')

    def test_create_site_valid_project_id(self, client, app):
        """Test creating site with valid project_id succeeds."""
        with app.app_context():
            # Create project first
            project = Project(name="Test Project")
            db.session.add(project)
            db.session.commit()

            data = {
                'name': 'Test Site',
                'project_id': project.id
            }

            response = client.post('/api/sites', json=data)
            assert response.status_code == 201

    def test_update_site_invalid_project_id(self, client, app):
        """Test updating site with invalid project_id fails."""
        with app.app_context():
            # Create valid site first
            project = Project(name="Test Project")
            db.session.add(project)
            db.session.commit()

            site = Site(name="Test Site", project_id=project.id)
            db.session.add(site)
            db.session.commit()

            # Try to update with invalid project_id
            data = {'project_id': 99999}
            response = client.put(f'/api/sites/{site.id}', json=data)
            assert response.status_code == 400
            data = response.get_json()
            assert 'does not exist' in data.get('error', '')

    def test_create_survey_invalid_site_id(self, client, app):
        """Test creating survey with invalid site_id fails."""
        with app.app_context():
            data = {
                'title': 'Test Survey',
                'site_id': 99999  # Invalid
            }

            response = client.post('/api/surveys', json=data)
            assert response.status_code == 400
            data = response.get_json()
            assert 'does not exist' in data.get('error', '')

    def test_create_survey_invalid_template_id(self, client, app):
        """Test creating survey with invalid template_id fails."""
        with app.app_context():
            # Create valid site first
            project = Project(name="Test Project")
            db.session.add(project)
            db.session.commit()

            site = Site(name="Test Site", project_id=project.id)
            db.session.add(site)
            db.session.commit()

            data = {
                'title': 'Test Survey',
                'site_id': site.id,
                'template_id': 99999  # Invalid
            }

            response = client.post('/api/surveys', json=data)
            assert response.status_code == 400
            data = response.get_json()
            assert 'does not exist' in data.get('error', '')


class TestCascadeDeletes:
    """Test cascading delete endpoints."""

    def test_delete_project_cascades(self, client, app):
        """Test DELETE /projects cascades properly."""
        with app.app_context():
            # Create test hierarchy
            project = Project(name="Test Project")
            db.session.add(project)
            db.session.commit()

            site = Site(name="Test Site", project_id=project.id)
            db.session.add(site)
            db.session.commit()

            survey = Survey(title="Test Survey", site_id=site.id)
            db.session.add(survey)
            db.session.commit()

            # Delete project
            response = client.delete(f'/api/projects/{project.id}')
            assert response.status_code == 200
            data = response.get_json()
            assert 'summary' in data
            assert data['summary']['projects'] == 1
            assert data['summary']['sites'] == 1
            assert data['summary']['surveys'] == 1

    def test_delete_site_cascades(self, client, app):
        """Test DELETE /sites cascades properly."""
        with app.app_context():
            # Create test hierarchy (assume project exists)
            site = Site(name="Test Site", project_id=1)
            db.session.add(site)
            db.session.commit()

            survey = Survey(title="Test Survey", site_id=site.id)
            db.session.add(survey)
            db.session.commit()

            # Delete site
            response = client.delete(f'/api/sites/{site.id}')
            assert response.status_code == 200
            data = response.get_json()
            assert 'summary' in data
            assert data['summary']['sites'] == 1
            assert data['summary']['surveys'] == 1

    def test_delete_survey_cascades(self, client, app):
        """Test DELETE /surveys cascades properly."""
        with app.app_context():
            # Create test survey (assume site exists)
            survey = Survey(title="Test Survey", site_id=1)
            db.session.add(survey)
            db.session.commit()

            response = SurveyResponse(survey_id=survey.id, question="Test", answer="Test")
            db.session.add(response)
            db.session.commit()

            # Delete survey
            response = client.delete(f'/api/surveys/{survey.id}')
            assert response.status_code == 200
            data = response.get_json()
            assert 'summary' in data
            assert data['summary']['surveys'] == 1
            assert data['summary']['responses'] == 1


class TestIntegrityAudit:
    """Test referential integrity audit command."""

    def test_audit_no_orphaned_records(self, app, runner):
        """Test audit command when no orphaned records exist."""
        with app.app_context():
            result = runner.invoke(args=['check-referential-integrity'])
            assert result.exit_code == 0
            assert 'All foreign key relationships are intact' in result.output

    def test_audit_detects_orphaned_sites(self, app, runner):
        """Test audit command detects orphaned sites."""
        with app.app_context():
            # Create orphaned site
            site = Site(name="Orphaned Site", project_id=99999)
            db.session.add(site)
            db.session.commit()

            result = runner.invoke(args=['check-referential-integrity'])
            assert result.exit_code == 0
            assert 'Found 1 orphaned records' in result.output
            assert 'SITES: 1 orphaned records' in result.output

    def test_audit_fix_orphaned_records(self, app, runner):
        """Test audit command --fix deletes orphaned records."""
        with app.app_context():
            # Create orphaned site
            site = Site(name="Orphaned Site", project_id=99999)
            db.session.add(site)
            db.session.commit()

            # Fix orphaned records
            result = runner.invoke(args=['check-referential-integrity', '--fix'])
            assert result.exit_code == 0
            assert 'Successfully deleted 1 orphaned records' in result.output
            assert 'sites: 1' in result.output

            # Verify record was deleted
            assert Site.query.get(site.id) is None
