import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey, Enum, Index, text
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
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    name = db.Column(String(200), nullable=False, server_default="")
    description = db.Column(Text, server_default="")
    status = db.Column(String(20), default='draft', server_default='draft')
    client_info = db.Column(Text, server_default="")
    due_date = db.Column(DateTime)
    priority = db.Column(String(50), default='medium', server_default='medium')
    created_at = db.Column(DateTime, default=datetime.utcnow, server_default="1970-01-01 00:00:00")
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="1970-01-01 00:00:00")
    sites = relationship('Site', backref='project', lazy=True)


class Site(db.Model):
    __tablename__ = 'sites'
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    name = db.Column(String(200), nullable=False, server_default="Untitled")
    address = db.Column(Text, server_default="")
    latitude = db.Column(Float, server_default="0.0")
    longitude = db.Column(Float, server_default="0.0")
    notes = db.Column(Text, server_default="")
    project_id = db.Column(Integer, ForeignKey('projects.id'), index=True, server_default="1")
    created_at = db.Column(DateTime, default=datetime.utcnow, server_default="1970-01-01 00:00:00")
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="1970-01-01 00:00:00")
    surveys = relationship('Survey', backref='site', lazy=True)

# Indexes for Site table
Index('idx_site_project_id', Site.project_id)


class Survey(db.Model):
    __tablename__ = 'survey'
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    title = db.Column(String(200), nullable=False, server_default="Untitled Survey")
    description = db.Column(Text, server_default="")
    site_id = db.Column(Integer, ForeignKey('sites.id'), nullable=False, server_default="1")
    created_at = db.Column(DateTime, default=datetime.utcnow, server_default="1970-01-01 00:00:00")
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="1970-01-01 00:00:00")
    status = db.Column(String(20), default='draft', server_default='draft')
    template_id = db.Column(Integer, ForeignKey('survey_template.id'), server_default=None)
    template = relationship('SurveyTemplate', backref='surveys')
    responses = relationship('SurveyResponse', backref='survey')

# Indexes for Survey table
Index('idx_survey_site_id', Survey.site_id)
Index('idx_survey_template_id', Survey.template_id)
Index('idx_survey_status', Survey.status)
Index('idx_survey_created_at', Survey.created_at)


class SurveyResponse(db.Model):
    __tablename__ = 'survey_response'
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    survey_id = db.Column(Integer, ForeignKey('survey.id'), nullable=False, index=True, server_default="1")
    question = db.Column(String(500), nullable=False, server_default="")
    answer = db.Column(Text, server_default="")
    response_type = db.Column(String(50), index=True, server_default="")
    latitude = db.Column(Float, server_default="0.0")
    longitude = db.Column(Float, server_default="0.0")
    created_at = db.Column(DateTime, default=datetime.utcnow, server_default="1970-01-01 00:00:00")
    question_id = db.Column(Integer, index=True, server_default="0")
    field_type = db.Column(String(50), server_default="")

# Indexes for SurveyResponse table
Index('idx_response_survey_question', SurveyResponse.survey_id, SurveyResponse.question_id)
Index('idx_response_created_at', SurveyResponse.created_at)


class AppConfig(db.Model):
    __tablename__ = 'app_config'
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    key = db.Column(String(100), unique=True, nullable=False, server_default="")
    value = db.Column(Text, server_default="")
    description = db.Column(String(300), server_default="")
    category = db.Column(String(50), server_default="")
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="1970-01-01 00:00:00")


class SurveyTemplate(db.Model):
    __tablename__ = 'survey_template'
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    name = db.Column(String(200), nullable=False, server_default="Untitled Template")
    description = db.Column(Text, server_default="")
    category = db.Column(String(50), server_default="")
    is_default = db.Column(Boolean, default=False, server_default='0')
    created_at = db.Column(DateTime, default=datetime.utcnow, server_default="1970-01-01 00:00:00")
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="1970-01-01 00:00:00")
    fields = relationship('TemplateField', backref='template', cascade='all, delete-orphan', lazy=True)


class TemplateField(db.Model):
    __tablename__ = 'template_field'
    id = db.Column(Integer, primary_key=True, nullable=False, server_default="0")
    template_id = db.Column(Integer, ForeignKey('survey_template.id'), nullable=False, index=True, server_default="1")
    field_type = db.Column(String(50), server_default="")
    question = db.Column(String(500), nullable=False, server_default="")
    description = db.Column(Text, server_default="")
    required = db.Column(Boolean, default=False, server_default='0')
    options = db.Column(Text, server_default="")
    order_index = db.Column(Integer, default=0, server_default="0")
    section = db.Column(String(100), server_default="")
    conditions = db.Column(Text, server_default="")
    photo_requirements = db.Column(Text, server_default="")
    section_weight = db.Column(Integer, default=1, server_default="1")

# Indexes for TemplateField table
Index('idx_template_field_template_id', TemplateField.template_id)
Index('idx_template_field_order', TemplateField.template_id, TemplateField.order_index)


class Photo(db.Model):
    __tablename__ = 'photo'
    id = db.Column(String, primary_key=True, nullable=False, server_default="")
    survey_id = db.Column(String, ForeignKey('survey.id'), index=True, server_default="")
    site_id = db.Column(Integer, ForeignKey('sites.id'), index=True, server_default="1")
    image_data = db.Column(LargeBinary)
    latitude = db.Column(Float, server_default="0.0")
    longitude = db.Column(Float, server_default="0.0")
    description = db.Column(Text, server_default="")
    category = db.Column(String(20), default='general', server_default='general')
    created_at = db.Column(DateTime, default=datetime.utcnow, index=True, server_default="1970-01-01 00:00:00")
    hash_algo = db.Column(String(10), default='sha256', server_default='sha256')
    hash_value = db.Column(String(128), index=True, unique=True, server_default="")
    size_bytes = db.Column(Integer, server_default="0")
    thumbnail_data = db.Column(LargeBinary)
    file_path = db.Column(String(500), server_default="")
    requirement_id = db.Column(String, index=True, server_default="")
    fulfills_requirement = db.Column(Boolean, default=False, server_default='0')

# Indexes for Photo table
Index('idx_photo_survey_site', Photo.survey_id, Photo.site_id)
Index('idx_photo_created_at', Photo.created_at)
Index('idx_photo_requirement', Photo.requirement_id, Photo.fulfills_requirement)


def create_crr_tables(target, connection, **kw):
    """Make tables CRR for cr-sqlite sync."""
    crr_tables = ['projects', 'sites', 'survey', 'survey_response', 'survey_template', 'template_field', 'photo', 'app_config']
    for table_name in crr_tables:
        connection.execute(text(f"SELECT crsql_as_crr('{table_name}');"))


# Note: This event listener should be called after db is initialized in app factory