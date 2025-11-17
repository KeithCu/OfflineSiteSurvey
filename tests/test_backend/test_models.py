"""Tests for backend database models."""
import pytest
from backend.models import db, Project, Site, Survey, SurveyResponse, AppConfig, SurveyTemplate, TemplateField, Photo


def test_project_model_creation(app):
    """Test creating a project model."""
    with app.app_context():
        project = Project(
            name="Test Project",
            description="A test project",
            status="draft",
            client_info="Test Client",
            due_date=None,
            priority="medium"
        )
        db.session.add(project)
        db.session.commit()

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.status == "draft"


def test_site_model_creation(app):
    """Test creating a site model."""
    with app.app_context():
        project = Project(name="Parent Project")
        db.session.add(project)
        db.session.commit()

        site = Site(
            name="Test Site",
            address="123 Test St",
            latitude=40.7128,
            longitude=-74.0060,
            notes="Test notes",
            project_id=project.id
        )
        db.session.add(site)
        db.session.commit()

        assert site.id is not None
        assert site.name == "Test Site"
        assert site.project_id == project.id


def test_survey_model_creation(app):
    """Test creating a survey model."""
    with app.app_context():
        project = Project(name="Parent Project")
        site = Site(name="Parent Site", project_id=project.id)
        db.session.add_all([project, site])
        db.session.commit()

        survey = Survey(
            title="Test Survey",
            description="A test survey",
            site_id=site.id,
            status="draft"
        )
        db.session.add(survey)
        db.session.commit()

        assert survey.id is not None
        assert survey.title == "Test Survey"
        assert survey.site_id == site.id


def test_survey_response_model_creation(app):
    """Test creating a survey response model."""
    with app.app_context():
        project = Project(name="Parent Project")
        site = Site(name="Parent Site", project_id=project.id)
        survey = Survey(title="Parent Survey", site_id=site.id)
        db.session.add_all([project, site, survey])
        db.session.commit()

        response = SurveyResponse(
            survey_id=survey.id,
            question="Test question?",
            answer="Test answer",
            response_type="text",
            question_id=1
        )
        db.session.add(response)
        db.session.commit()

        assert response.id is not None
        assert response.answer == "Test answer"
        assert response.survey_id == survey.id


def test_app_config_model_creation(app):
    """Test creating an app config model."""
    with app.app_context():
        config = AppConfig(
            key="test_key",
            value="test_value",
            description="Test configuration",
            category="test"
        )
        db.session.add(config)
        db.session.commit()

        assert config.id is not None
        assert config.key == "test_key"
        assert config.value == "test_value"


def test_survey_template_model_creation(app):
    """Test creating a survey template model."""
    with app.app_context():
        template = SurveyTemplate(
            name="Test Template",
            description="A test template",
            category="commercial",
            is_default=False
        )
        db.session.add(template)
        db.session.commit()

        assert template.id is not None
        assert template.name == "Test Template"
        assert template.is_default is False


def test_template_field_model_creation(app):
    """Test creating a template field model."""
    with app.app_context():
        template = SurveyTemplate(name="Parent Template")
        db.session.add(template)
        db.session.commit()

        field = TemplateField(
            template_id=template.id,
            question="Test question?",
            field_type="text",
            required=True,
            order_index=1
        )
        db.session.add(field)
        db.session.commit()

        assert field.id is not None
        assert field.question == "Test question?"
        assert field.template_id == template.id


def test_photo_model_creation(app):
    """Test creating a photo model."""
    with app.app_context():
        project = Project(name="Parent Project")
        site = Site(name="Parent Site", project_id=project.id)
        survey = Survey(title="Parent Survey", site_id=site.id)
        db.session.add_all([project, site, survey])
        db.session.commit()

        photo = Photo(
            survey_id=survey.id,
            site_id=site.id,
            image_data=b"fake_image_data",
            latitude=40.7128,
            longitude=-74.0060,
            description="Test photo",
            category="general",
            hash_value="a" * 64,  # 64 character hash
            hash_algo="sha256",
            size_bytes=100
        )
        db.session.add(photo)
        db.session.commit()

        assert photo.id is not None
        assert photo.description == "Test photo"
        assert photo.hash_value == "a" * 64


def test_model_relationships(app):
        """Test model relationships work correctly."""
        with app.app_context():
            # Create hierarchy: Project -> Site -> Survey -> Response/Photo
            project = Project(name="Relationship Test Project")
            site = Site(name="Relationship Test Site", project_id=project.id)
            survey = Survey(title="Relationship Test Survey", site_id=site.id)

            db.session.add_all([project, site, survey])
            db.session.commit()  # Commit parents first to get IDs

            response = SurveyResponse(
                survey_id=survey.id,
                question="Test?",
                answer="Answer",
                response_type="text"
            )
            photo = Photo(
                survey_id=survey.id,
                site_id=site.id,
                image_data=b"test",
                hash_value="b" * 64,
                hash_algo="sha256",
                size_bytes=4,
                category="general"
            )

            db.session.add_all([response, photo])
            db.session.commit()

            # Test relationships
            assert survey in site.surveys
            assert response in survey.responses
            assert photo.survey_id == str(survey.id)
            assert photo.site_id == site.id

            # Test reverse relationships
            assert site.project_id == project.id
            assert survey.site_id == site.id
