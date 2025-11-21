from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey, Index, text, Enum
from sqlalchemy.orm import relationship, declarative_base
from shared.enums import SurveyStatus, ProjectStatus, PhotoCategory, PriorityLevel, UserRole

Base = declarative_base()

# Global timezone configuration - Eastern Time (US/Eastern)
# Change this variable to use a different timezone if needed
# Uses zoneinfo for proper DST handling (EST/EDT)
from zoneinfo import ZoneInfo
APP_TIMEZONE = ZoneInfo('America/New_York')  # Eastern Time with automatic DST handling

# EPOCH: Timezone-aware datetime representing Unix epoch in Eastern Time
# Used for consistent default timestamps across all models
# When stored in SQLite, timezone info is stripped (SQLite limitation)
EPOCH = datetime(1970, 1, 1, tzinfo=APP_TIMEZONE)  # Timezone-aware epoch in Eastern Time

def now():
    """Return current datetime in application timezone (Eastern Time, timezone-aware).
    
    Note: When stored in SQLite, timezone info is stripped (SQLite limitation).
    All stored datetimes should be treated as Eastern Time, even though they're stored naive.
    """
    return datetime.now(APP_TIMEZONE)

class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, unique=True, server_default="")
    description = Column(Text, server_default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    members = relationship('User', backref='team', lazy='select')


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(80), unique=True, nullable=False, server_default="")
    email = Column(String(120), unique=True, nullable=False, server_default="")
    password_hash = Column(String(128), nullable=False, server_default="")
    role = Column(Enum(UserRole), default=UserRole.SURVEYOR, nullable=False, server_default=text("'surveyor'"))
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, server_default="")
    description = Column(Text, server_default="")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False, server_default=text("'draft'"))
    client_info = Column(Text, server_default="")
    due_date = Column(DateTime)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, nullable=False, server_default=text("'medium'"))
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    sites = relationship('Site', backref='project', lazy='select', cascade="all, delete-orphan")


class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, server_default="Untitled")
    address = Column(Text, server_default="")
    latitude = Column(Float, server_default="0.0")
    longitude = Column(Float, server_default="0.0")
    notes = Column(Text, server_default="")
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    surveys = relationship('Survey', backref='site', lazy='select', cascade="all, delete-orphan")
    photos = relationship('Photo', backref='site', lazy='select', cascade="all, delete-orphan")

Index('idx_site_project_id', Site.project_id)


class Survey(Base):
    __tablename__ = 'survey'
    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String(200), nullable=False, server_default="Untitled Survey")
    description = Column(Text, server_default="")
    site_id = Column(Integer, ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    status = Column(Enum(SurveyStatus), default=SurveyStatus.DRAFT, nullable=False, server_default=text("'draft'"))
    template_id = Column(Integer, ForeignKey('survey_template.id', ondelete='SET NULL'))
    template = relationship('SurveyTemplate', backref='surveys')
    responses = relationship('SurveyResponse', backref='survey', cascade="all, delete-orphan")
    photos = relationship('Photo', backref='survey', lazy='select', cascade="all, delete-orphan")

Index('idx_survey_site_id', Survey.site_id)
Index('idx_survey_template_id', Survey.template_id)


class SurveyResponse(Base):
    __tablename__ = 'survey_response'
    id = Column(Integer, primary_key=True, nullable=False)
    survey_id = Column(Integer, ForeignKey('survey.id', ondelete='CASCADE'), nullable=False, index=True)
    question = Column(String(500), nullable=False, server_default="")
    answer = Column(Text, server_default="")
    response_type = Column(String(50), index=True, server_default="")
    latitude = Column(Float, server_default="0.0")
    longitude = Column(Float, server_default="0.0")
    created_at = Column(DateTime, default=now)
    question_id = Column(Integer, ForeignKey('template_field.id', ondelete='SET NULL'), index=True, nullable=True)
    field_type = Column(String(50), server_default="")

Index('idx_response_survey_question', SurveyResponse.survey_id, SurveyResponse.question_id)
Index('idx_response_created_at', SurveyResponse.created_at)


class AppConfig(Base):
    __tablename__ = 'app_config'
    id = Column(Integer, primary_key=True, nullable=False)
    key = Column(String(100), unique=True, nullable=False, server_default="")
    value = Column(Text, server_default="")
    description = Column(String(300), server_default="")
    category = Column(String(50), server_default="")
    updated_at = Column(DateTime, default=now, onupdate=now)


class SurveyTemplate(Base):
    __tablename__ = 'survey_template'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, server_default="Untitled Template")
    description = Column(Text, server_default="")
    category = Column(String(50), server_default="")
    is_default = Column(Boolean, default=False, server_default='0')
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    fields = relationship('TemplateField', backref='template', cascade='all, delete-orphan', lazy='select')
    section_tags = Column(Text, server_default="{}")


class TemplateField(Base):
    __tablename__ = 'template_field'
    id = Column(Integer, primary_key=True, nullable=False)
    template_id = Column(Integer, ForeignKey('survey_template.id', ondelete='CASCADE'), nullable=False, index=True)
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

Index('idx_template_field_order', TemplateField.template_id, TemplateField.order_index)


class Photo(Base):
    __tablename__ = 'photo'
    id = Column(String, primary_key=True, nullable=False)
    survey_id = Column(Integer, ForeignKey('survey.id', ondelete='CASCADE'), index=True)
    site_id = Column(Integer, ForeignKey('sites.id', ondelete='CASCADE'), index=True)
    cloud_url = Column(String(1000), server_default="")
    thumbnail_url = Column(String(1000), server_default="")
    # Remove image_data and thumbnail_data columns as they are not used in cloud-first architecture
    # image_data = Column(LargeBinary, nullable=True)
    # thumbnail_data = Column(LargeBinary, nullable=True)
    upload_status = Column(String(20), default='pending', server_default='pending')
    retry_count = Column(Integer, default=0, server_default='0')
    last_retry_at = Column(DateTime)
    latitude = Column(Float, server_default="0.0")
    longitude = Column(Float, server_default="0.0")
    description = Column(Text, server_default="")
    category = Column(Enum(PhotoCategory), default=PhotoCategory.GENERAL, nullable=False, server_default=text("'general'"))
    created_at = Column(DateTime, default=EPOCH, index=True)
    hash_value = Column(String(64), index=True, server_default="")
    size_bytes = Column(Integer, server_default="0")
    file_path = Column(String(500), server_default="")
    requirement_id = Column(String, index=True, server_default="")
    fulfills_requirement = Column(Boolean, default=False, server_default='0')
    tags = Column(Text, server_default="[]")
    question_id = Column(Integer, ForeignKey('template_field.id', ondelete='SET NULL'), index=True, nullable=True)
    corrupted = Column(Boolean, default=False, server_default='0', index=True)

Index('idx_photo_survey_site', Photo.survey_id, Photo.site_id)
Index('idx_photo_created_at', Photo.created_at)
Index('idx_photo_requirement', Photo.requirement_id, Photo.fulfills_requirement)
Index('idx_photo_upload_status', Photo.upload_status)
Index('idx_photo_hash_value', Photo.hash_value)
Index('idx_photos_category', Photo.category)
