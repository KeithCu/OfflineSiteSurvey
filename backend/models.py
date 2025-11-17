from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from shared.models import (
    Base, Project, Site, Survey, SurveyResponse, AppConfig,
    SurveyTemplate, TemplateField, Photo, SurveyStatus, ProjectStatus
)

db = SQLAlchemy(model_class=Base)

def create_crr_tables(target, connection, **kw):
    """Make tables CRR for cr-sqlite sync."""
    connection.execute(text("PRAGMA foreign_keys = OFF;"))
    crr_tables = [
        'projects', 'sites', 'survey', 'survey_response',
        'survey_template', 'template_field', 'photo', 'app_config'
    ]
    for table_name in crr_tables:
        try:
            connection.execute(text(f"SELECT crsql_as_crr('{table_name}');"))
        except Exception as e:
            print(f"Warning: Failed to make {table_name} CRR: {e}")
            # Continue with other tables
