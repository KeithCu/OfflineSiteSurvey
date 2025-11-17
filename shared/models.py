import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def utc_now():
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)

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

class PhotoCategory(enum.Enum):
    GENERAL = 'general'
    INTERIOR = 'interior'
    EXTERIOR = 'exterior'
    ISSUES = 'issues'
    PROGRESS = 'progress'

class PriorityLevel(enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    name = Column(String(200), nullable=False, server_default="")
    description = Column(Text, server_default="")
    status = Column(String(20), default='draft', server_default='draft')
    client_info = Column(Text, server_default="")
    due_date = Column(DateTime)
    priority = Column(String(50), default='medium', server_default='medium')
    created_at = Column(DateTime, default=utc_now, server_default="1970-01-01 00:00:00")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, server_default="1970-01-01 00:00:00")
    sites = relationship('Site', backref='project', lazy=True)


class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    name = Column(String(200), nullable=False, server_default="Untitled")
    address = Column(Text, server_default="")
    latitude = Column(Float, server_default="0.0")
    longitude = Column(Float, server_default="0.0")
    notes = Column(Text, server_default="")
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), index=True, server_default="1")
    created_at = Column(DateTime, default=utc_now, server_default="1970-01-01 00:00:00")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, server_default="1970-01-01 00:00:00")
    surveys = relationship('Survey', backref='site', lazy=True)

Index('idx_site_project_id', Site.project_id)


class Survey(Base):
    __tablename__ = 'survey'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    title = Column(String(200), nullable=False, server_default="Untitled Survey")
    description = Column(Text, server_default="")
    site_id = Column(Integer, ForeignKey('sites.id', ondelete='CASCADE'), nullable=False, server_default="1")
    created_at = Column(DateTime, default=utc_now, server_default="1970-01-01 00:00:00")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, server_default="1970-01-01 00:00:00")
    status = Column(String(20), default='draft', server_default='draft')
    template_id = Column(Integer, ForeignKey('survey_template.id', ondelete='SET NULL'), server_default=None)
    template = relationship('SurveyTemplate', backref='surveys')
    responses = relationship('SurveyResponse', backref='survey')

Index('idx_survey_site_id', Survey.site_id)
Index('idx_survey_template_id', Survey.template_id)
Index('idx_survey_status', Survey.status)
Index('idx_survey_created_at', Survey.created_at)


class SurveyResponse(Base):
    __tablename__ = 'survey_response'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    survey_id = Column(Integer, ForeignKey('survey.id', ondelete='CASCADE'), nullable=False, index=True, server_default="1")
    question = Column(String(500), nullable=False, server_default="")
    answer = Column(Text, server_default="")
    response_type = Column(String(50), index=True, server_default="")
    latitude = Column(Float, server_default="0.0")
    longitude = Column(Float, server_default="0.0")
    created_at = Column(DateTime, default=utc_now, server_default="1970-01-01 00:00:00")
    question_id = Column(Integer, index=True, server_default="0")
    field_type = Column(String(50), server_default="")

Index('idx_response_survey_question', SurveyResponse.survey_id, SurveyResponse.question_id)
Index('idx_response_created_at', SurveyResponse.created_at)


class AppConfig(Base):
    __tablename__ = 'app_config'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    key = Column(String(100), unique=True, nullable=False, server_default="")
    value = Column(Text, server_default="")
    description = Column(String(300), server_default="")
    category = Column(String(50), server_default="")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, server_default="1970-01-01 00:00:00")


class SurveyTemplate(Base):
    __tablename__ = 'survey_template'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    name = Column(String(200), nullable=False, server_default="Untitled Template")
    description = Column(Text, server_default="")
    category = Column(String(50), server_default="")
    is_default = Column(Boolean, default=False, server_default='0')
    created_at = Column(DateTime, default=utc_now, server_default="1970-01-01 00:00:00")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, server_default="1970-01-01 00:00:00")
    fields = relationship('TemplateField', backref='template', cascade='all, delete-orphan', lazy=True)


class TemplateField(Base):
    __tablename__ = 'template_field'
    id = Column(Integer, primary_key=True, nullable=False, server_default="0")
    template_id = Column(Integer, ForeignKey('survey_template.id', ondelete='CASCADE'), nullable=False, index=True, server_default="1")
    field_type = Column(String(50), server_default="")
    question = Column(String(500), nullable=False, server_default="")
    description = Column(Text, server_default="")
    required = Column(Boolean, default=False, server_default='0')
    options = Column(Text, server_default="")
    order_index = Column(Integer, default=0, server_default="0")
    section = Column(String(100), server_default="")
    conditions = Column(Text, server_default="")
    photo_requirements = Column(Text, server_default="")
    section_weight = Column(Integer, default=1, server_default="1")

Index('idx_template_field_template_id', TemplateField.template_id)
Index('idx_template_field_order', TemplateField.template_id, TemplateField.order_index)


class Photo(Base):
    __tablename__ = 'photo'
    id = Column(String, primary_key=True, nullable=False, server_default="")
    survey_id = Column(Integer, ForeignKey('survey.id', ondelete='CASCADE'), index=True, server_default="0")
    site_id = Column(Integer, ForeignKey('sites.id', ondelete='CASCADE'), index=True, server_default="1")
    cloud_url = Column(String(1000), server_default="")
    thumbnail_url = Column(String(1000), server_default="")
    cloud_provider = Column(String(50), server_default="")
    cloud_object_name = Column(String(500), server_default="")
    thumbnail_object_name = Column(String(500), server_default="")
    upload_status = Column(String(20), default='pending', server_default='pending')
    latitude = Column(Float, server_default="0.0")
    longitude = Column(Float, server_default="0.0")
    description = Column(Text, server_default="")
    category = Column(String(20), default='general', server_default='general')
    created_at = Column(DateTime, default=utc_now, index=True, server_default="1970-01-01 00:00:00")
    hash_algo = Column(String(10), default='sha256', server_default='sha256')
    hash_value = Column(String(128), index=True, unique=True, server_default="")
    size_bytes = Column(Integer, server_default="0")
    file_path = Column(String(500), server_default="")
    requirement_id = Column(String, index=True, server_default="")
    fulfills_requirement = Column(Boolean, default=False, server_default='0')

Index('idx_photo_survey_site', Photo.survey_id, Photo.site_id)
Index('idx_photo_created_at', Photo.created_at)
Index('idx_photo_requirement', Photo.requirement_id, Photo.fulfills_requirement)
