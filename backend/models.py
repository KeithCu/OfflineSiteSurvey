import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class SurveyStatus(enum.Enum):
    DRAFT = 'draft'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'


class ProjectStatus(enum.Enum):
    DRAFT = 'draft'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(200), nullable=False)
    description = db.Column(Text)
    status = db.Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    client_info = db.Column(Text)
    due_date = db.Column(DateTime)
    priority = db.Column(String(50), default='medium')
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sites = relationship('Site', backref='project', lazy=True)


class Site(db.Model):
    __tablename__ = 'site'
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(200), nullable=False, server_default="Untitled")
    address = db.Column(Text)
    latitude = db.Column(Float)
    longitude = db.Column(Float)
    notes = db.Column(Text)
    project_id = db.Column(Integer, ForeignKey('projects.id'))
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Survey(db.Model):
    __tablename__ = 'survey'
    id = db.Column(Integer, primary_key=True)
    title = db.Column(String(200), nullable=False, server_default="Untitled Survey")
    description = db.Column(Text)
    site_id = db.Column(Integer, ForeignKey('site.id'), nullable=False, server_default="1")
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(Enum(SurveyStatus), default=SurveyStatus.DRAFT)
    template_id = db.Column(Integer, ForeignKey('survey_template.id'), nullable=True)
    template = relationship('SurveyTemplate', backref='surveys')
    responses = relationship('SurveyResponse', backref='survey')


class SurveyResponse(db.Model):
    __tablename__ = 'survey_response'
    id = db.Column(Integer, primary_key=True)
    survey_id = db.Column(Integer, ForeignKey('survey.id'), nullable=False)
    question = db.Column(String(500), nullable=False)
    answer = db.Column(Text)
    response_type = db.Column(String(50))
    latitude = db.Column(Float)
    longitude = db.Column(Float)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    question_id = db.Column(Integer)
    field_type = db.Column(String(50))


class AppConfig(db.Model):
    __tablename__ = 'app_config'
    id = db.Column(Integer, primary_key=True)
    key = db.Column(String(100), unique=True, nullable=False)
    value = db.Column(Text)
    description = db.Column(String(300))
    category = db.Column(String(50))
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SurveyTemplate(db.Model):
    __tablename__ = 'survey_template'
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(200), nullable=False, server_default="Untitled Template")
    description = db.Column(Text)
    category = db.Column(String(50))
    is_default = db.Column(Boolean, default=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fields = relationship('TemplateField', backref='template', cascade='all, delete-orphan', lazy=True)


class TemplateField(db.Model):
    __tablename__ = 'template_field'
    id = db.Column(Integer, primary_key=True)
    template_id = db.Column(Integer, ForeignKey('survey_template.id'), nullable=False)
    field_type = db.Column(String(50))
    question = db.Column(String(500), nullable=False)
    description = db.Column(Text)
    required = db.Column(Boolean, default=False)
    options = db.Column(Text)
    order_index = db.Column(Integer, default=0)
    section = db.Column(String(100))
    conditions = db.Column(Text)
    photo_requirements = db.Column(Text)
    section_weight = db.Column(Integer, default=1)


class Photo(db.Model):
    __tablename__ = 'photo'
    id = db.Column(String, primary_key=True)
    survey_id = db.Column(String, ForeignKey('survey.id'))
    site_id = db.Column(Integer, ForeignKey('site.id'))
    image_data = db.Column(LargeBinary)
    latitude = db.Column(Float)
    longitude = db.Column(Float)
    description = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    hash_algo = db.Column(String(10), default='sha256')
    hash_value = db.Column(String(128))
    size_bytes = db.Column(Integer)
    thumbnail_data = db.Column(LargeBinary)
    file_path = db.Column(String(500))
    requirement_id = db.Column(String)
    fulfills_requirement = db.Column(Boolean, default=False)


def create_crr_tables(target, connection, **kw):
    """Make tables CRR for cr-sqlite sync."""
    crr_tables = ['projects', 'site', 'survey', 'survey_response', 'survey_template', 'template_field', 'photo', 'app_config']
    for table_name in crr_tables:
        connection.execute(text(f"SELECT crsql_as_crr('{table_name}');"))


# Note: This event listener should be called after db is initialized in app factory