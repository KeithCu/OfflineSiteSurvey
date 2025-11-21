"""Pydantic schemas for validation and serialization."""
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import re
import bleach
from shared.enums import ProjectStatus, SurveyStatus, PhotoCategory, PriorityLevel

# Default max section tags (used when config is not available)
DEFAULT_MAX_SECTION_TAGS = 100

def get_max_section_tags_limit():
    """Get the maximum number of section tags allowed from config or default."""
    try:
        # Try to import and use the backend config function
        from backend.utils import get_config_value
        return get_config_value('max_section_tags', DEFAULT_MAX_SECTION_TAGS)
    except ImportError:
        # If backend not available (e.g., in frontend), use default
        return DEFAULT_MAX_SECTION_TAGS


def sanitize_text_or_json(value: str) -> str:
    """Safely sanitize text that might be HTML or JSON.

    For JSON fields, we validate the JSON structure instead of stripping HTML.
    For regular text fields, we sanitize HTML as before.

    Args:
        value: The string value to sanitize

    Returns:
        The sanitized string
    """
    if not value:
        return value

    # Check if this looks like JSON (starts with { or [)
    stripped = value.strip()
    if stripped.startswith(('{', '[')):
        # This appears to be JSON - validate it instead of sanitizing HTML
        try:
            # Parse and re-serialize to ensure valid JSON
            parsed = json.loads(stripped)
            return json.dumps(parsed)  # Return normalized JSON
        except json.JSONDecodeError:
            # Invalid JSON - log warning but don't sanitize HTML as it might be intentional
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid JSON detected but not sanitized: {value[:100]}...")
            return value  # Return as-is to avoid corrupting intentional content

    # Not JSON - apply HTML sanitization
    return sanitize_html(value)
# Note: APP_TIMEZONE and now are available from shared.models if needed


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


# Utility functions for validation (used outside Pydantic models)
def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: Optional[int] = None) -> str:
    """Validate string length constraints."""
    if not isinstance(value, str):
        raise ValidationError(f"Validation failed: {field_name} must be a string")
    value = value.strip()
    if len(value) < min_length:
        raise ValidationError(f"Validation failed: {field_name} must be at least {min_length} characters")
    if max_length and len(value) > max_length:
        raise ValidationError(f"Validation failed: {field_name} must be no more than {max_length} characters")
    return value


def _fallback_sanitize_html(text: str) -> str:
    """Fallback HTML sanitization when bleach is not available.

    This is a basic implementation that strips dangerous tags and attributes.
    It's not as comprehensive as bleach but provides basic protection.
    """
    if not text:
        return text

    # If no HTML-like characters, return as-is
    if '<' not in text and '>' not in text and '&' not in text:
        return text

    # Basic tag stripping - remove script, style, and other dangerous tags
    dangerous_tags = ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'meta']
    result = text

    for tag in dangerous_tags:
        # Remove opening tags
        result = result.replace(f'<{tag}', '<removed')
        result = result.replace(f'<{tag.upper()}', '<REMOVED')
        # Remove closing tags
        result = result.replace(f'</{tag}>', '')
        result = result.replace(f'</{tag.upper()}>', '')

    # Remove event handlers (on* attributes)
    import re
    result = re.sub(r'\s+on\w+="[^"]*"', '', result)
    result = re.sub(r"\s+on\w+='[^']*'", '', result)

    return result


def sanitize_html(text: str) -> str:
    """Secure HTML sanitization using bleach library, with fallback."""
    if not text:
        return text
    if '<' not in text and '>' not in text and '&' not in text:
        return text

    try:
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'blockquote']
        allowed_attributes = {}
        return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    except (NameError, AttributeError):
        # Fallback if bleach is not available at runtime
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Bleach library not available, using fallback HTML sanitization. Install bleach for better security.")
        return _fallback_sanitize_html(text)


def validate_coordinates(lat: Any, lng: Any) -> tuple[float, float]:
    """Validate GPS coordinates with high precision support."""
    # For maximum precision, we could store as strings and validate format
    # But Float provides sufficient precision (15 decimal digits) for GPS needs

    # Validate latitude
    try:
        if isinstance(lat, str):
            lat_stripped = lat.strip()
            if not lat_stripped:
                raise ValidationError("Validation failed: Latitude cannot be empty")
            # Allow up to 10 decimal places (more than GPS precision needs)
            if '.' in lat_stripped:
                decimal_part = lat_stripped.split('.', 1)[1].rstrip('0')
                if len(decimal_part) > 10:
                    raise ValidationError("Validation failed: Latitude must not have more than 10 decimal places")
            lat_val = float(lat_stripped)
        else:
            lat_val = float(lat)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Validation failed: Latitude must be a valid number, got '{lat}' ({type(lat).__name__})")

    # Validate longitude
    try:
        if isinstance(lng, str):
            lng_stripped = lng.strip()
            if not lng_stripped:
                raise ValidationError("Validation failed: Longitude cannot be empty")
            if '.' in lng_stripped:
                decimal_part = lng_stripped.split('.', 1)[1].rstrip('0')
                if len(decimal_part) > 10:
                    raise ValidationError("Validation failed: Longitude must not have more than 10 decimal places")
            lng_val = float(lng_stripped)
        else:
            lng_val = float(lng)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Validation failed: Longitude must be a valid number, got '{lng}' ({type(lng).__name__})")

    # Validate ranges
    if not (-90 <= lat_val <= 90):
        raise ValidationError(f"Validation failed: Latitude must be between -90 and 90, got {lat_val}")
    if not (-180 <= lng_val <= 180):
        raise ValidationError(f"Validation failed: Longitude must be between -180 and 180, got {lng_val}")

    return lat_val, lng_val


def format_coordinate_for_storage(coord: float) -> str:
    """Format coordinate as string for exact storage if needed.

    GPS coordinates typically need 6-8 decimal places for ~10cm precision.
    SQLite REAL provides ~15 decimal digits, so Float is usually sufficient.
    Use this only if Float precision issues are observed in practice.

    Args:
        coord: Coordinate value as float

    Returns:
        String representation with appropriate precision
    """
    return f"{coord:.10f}".rstrip('0').rstrip('.')


def parse_coordinate_from_storage(coord_str: str) -> float:
    """Parse coordinate from string storage.

    Args:
        coord_str: Coordinate as string

    Returns:
        Coordinate as float
    """
    try:
        return float(coord_str)
    except (ValueError, TypeError):
        return 0.0


def validate_choice(value: Any, field_name: str, valid_choices: list) -> Any:
    """Validate that value is in list of valid choices."""
    if value not in valid_choices:
        raise ValidationError(f"Validation failed: {field_name} must be one of: {', '.join(str(c) for c in valid_choices)}")
    return value


# Project Schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=1000)
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT)
    client_info: Optional[str] = Field(default="", max_length=500)
    due_date: Optional[datetime] = None
    priority: PriorityLevel = Field(default=PriorityLevel.MEDIUM)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_string_length(v, 'name', 1, 200)

    @field_validator('description', 'client_info')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v or ""

    model_config = ConfigDict(use_enum_values=True)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ProjectStatus] = None
    client_info: Optional[str] = Field(None, max_length=500)
    due_date: Optional[datetime] = None
    priority: Optional[PriorityLevel] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            return validate_string_length(v, 'name', 1, 200)
        return v

    @field_validator('description', 'client_info')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v

    model_config = ConfigDict(use_enum_values=True)


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# Site Schemas
class SiteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = Field(default="", max_length=500)
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    notes: Optional[str] = Field(default="", max_length=1000)
    project_id: int = Field(..., gt=0)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_string_length(v, 'name', 1, 200)

    @field_validator('address', 'notes')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v or ""

    @model_validator(mode='after')
    def validate_coords(self):
        if self.latitude != 0.0 or self.longitude != 0.0:
            lat, lng = validate_coordinates(self.latitude, self.longitude)
            self.latitude = lat
            self.longitude = lng
        return self


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    notes: Optional[str] = Field(None, max_length=1000)
    project_id: Optional[int] = Field(None, gt=0)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            return validate_string_length(v, 'name', 1, 200)
        return v

    @field_validator('address', 'notes')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v

    @model_validator(mode='after')
    def validate_coords(self):
        if self.latitude is not None and self.longitude is not None:
            lat, lng = validate_coordinates(self.latitude, self.longitude)
            self.latitude = lat
            self.longitude = lng
        return self


class SiteResponse(SiteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Survey Schemas
class SurveyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=1000)
    site_id: int = Field(..., gt=0)
    status: SurveyStatus = Field(default=SurveyStatus.DRAFT)
    template_id: Optional[int] = Field(None, gt=0)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        return validate_string_length(v, 'title', 1, 200)

    @field_validator('description')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v or ""

    model_config = ConfigDict(use_enum_values=True)


class SurveyCreate(SurveyBase):
    pass


class SurveyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    site_id: Optional[int] = Field(None, gt=0)
    status: Optional[SurveyStatus] = None
    template_id: Optional[int] = Field(None, gt=0)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            return validate_string_length(v, 'title', 1, 200)
        return v

    @field_validator('description')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v

    model_config = ConfigDict(use_enum_values=True)


class SurveyResponseSchema(SurveyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# SurveyResponse (answer) Schemas
class SurveyResponseBase(BaseModel):
    survey_id: int = Field(..., gt=0)
    question: str = Field(..., max_length=500)
    answer: str = Field(default="")
    response_type: str = Field(default="", max_length=50)
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    question_id: Optional[int] = Field(None, gt=0)
    field_type: str = Field(default="", max_length=50)

    @field_validator('question', 'answer', 'response_type', 'field_type')
    @classmethod
    def validate_string_fields(cls, v):
        if v:
            return v.strip()
        return v or ""


class SurveyResponseCreate(SurveyResponseBase):
    pass


class SurveyResponseUpdate(BaseModel):
    survey_id: Optional[int] = Field(None, gt=0)
    question: Optional[str] = Field(None, max_length=500)
    answer: Optional[str] = None
    response_type: Optional[str] = Field(None, max_length=50)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    question_id: Optional[int] = Field(None, gt=0)
    field_type: Optional[str] = Field(None, max_length=50)

    @field_validator('question', 'answer', 'response_type', 'field_type')
    @classmethod
    def validate_string_fields(cls, v):
        if v is not None:
            return v.strip()
        return v


class SurveyResponseResponse(SurveyResponseBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Photo Schemas
class PhotoBase(BaseModel):
    survey_id: Optional[int] = Field(None, gt=0)
    site_id: Optional[int] = Field(None, gt=0)
    cloud_url: str = Field(default="", max_length=1000)
    thumbnail_url: str = Field(default="", max_length=1000)
    upload_status: str = Field(default="pending", max_length=20)
    retry_count: int = Field(default=0, ge=0)
    last_retry_at: Optional[datetime] = None
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    description: str = Field(default="")
    category: PhotoCategory = Field(default=PhotoCategory.GENERAL)
    hash_value: str = Field(default="", max_length=64)
    size_bytes: int = Field(default=0, ge=0)
    file_path: str = Field(default="", max_length=500)
    requirement_id: str = Field(default="")
    fulfills_requirement: bool = Field(default=False)
    tags: str = Field(default="[]")
    question_id: Optional[int] = Field(None, gt=0)
    corrupted: bool = Field(default=False)

    @field_validator('hash_value')
    @classmethod
    def validate_hash(cls, v):
        if v and len(v) != 64:
            raise ValueError("Hash value must be exactly 64 characters")
        return v

    model_config = ConfigDict(use_enum_values=True)


class PhotoCreate(PhotoBase):
    id: str  # Photo IDs are strings (UUID-like)

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('id must be a valid UUID')
        return v


class PhotoUpdate(BaseModel):
    survey_id: Optional[int] = Field(None, gt=0)
    site_id: Optional[int] = Field(None, gt=0)
    cloud_url: Optional[str] = Field(None, max_length=1000)
    thumbnail_url: Optional[str] = Field(None, max_length=1000)
    upload_status: Optional[str] = Field(None, max_length=20)
    retry_count: Optional[int] = Field(None, ge=0)
    last_retry_at: Optional[datetime] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    description: Optional[str] = None
    category: Optional[PhotoCategory] = None
    hash_value: Optional[str] = Field(None, max_length=64)
    size_bytes: Optional[int] = Field(None, ge=0)
    file_path: Optional[str] = Field(None, max_length=500)
    requirement_id: Optional[str] = None
    fulfills_requirement: Optional[bool] = None
    tags: Optional[str] = None
    question_id: Optional[int] = Field(None, gt=0)
    corrupted: Optional[bool] = None

    @field_validator('hash_value')
    @classmethod
    def validate_hash(cls, v):
        if v is not None and len(v) != 64:
            raise ValueError("Hash value must be exactly 64 characters")
        return v

    model_config = ConfigDict(use_enum_values=True)


class PhotoResponse(PhotoBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# Template Schemas
class TemplateFieldBase(BaseModel):
    field_type: str = Field(default="", max_length=50)
    question: str = Field(..., max_length=500)
    description: str = Field(default="")
    required: bool = Field(default=False)
    options: str = Field(default="")
    order_index: int = Field(default=0, ge=0)
    section: str = Field(default="", max_length=100)
    conditions: str = Field(default="")
    photo_requirements: str = Field(default="")
    section_weight: int = Field(default=1, ge=1)

    @field_validator('question', 'description', 'field_type', 'section')
    @classmethod
    def validate_string_fields(cls, v):
        if v:
            return v.strip()
        return v or ""

    @field_validator('conditions')
    @classmethod
    def validate_conditions(cls, v):
        """Validate conditions field - should be JSON or empty."""
        if v:
            return sanitize_text_or_json(v)
        return v or ""


class TemplateFieldCreate(TemplateFieldBase):
    template_id: int = Field(..., gt=0)


class TemplateFieldUpdate(BaseModel):
    field_type: Optional[str] = Field(None, max_length=50)
    question: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[str] = None
    order_index: Optional[int] = Field(None, ge=0)
    section: Optional[str] = Field(None, max_length=100)
    conditions: Optional[str] = None
    photo_requirements: Optional[str] = None
    section_weight: Optional[int] = Field(None, ge=1)

    @field_validator('question', 'description', 'field_type', 'section')
    @classmethod
    def validate_string_fields(cls, v):
        if v is not None:
            return v.strip()
        return v


class TemplateFieldResponse(TemplateFieldBase):
    id: int
    template_id: int

    model_config = ConfigDict(from_attributes=True)


class SurveyTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    category: str = Field(default="", max_length=50)
    is_default: bool = Field(default=False)
    section_tags: str = Field(default="{}")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_string_length(v, 'name', 1, 200)

    @field_validator('description', 'category')
    @classmethod
    def validate_string_fields(cls, v):
        if v:
            return v.strip()
        return v or ""

    @field_validator('section_tags')
    @classmethod
    def validate_section_tags_json(cls, v):
        """Validate section_tags field - should be JSON."""
        if v:
            return sanitize_text_or_json(v)
        return v or "{}"


class SurveyTemplateCreate(SurveyTemplateBase):
    fields: List[TemplateFieldBase] = Field(default_factory=list)


class SurveyTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    is_default: Optional[bool] = None
    section_tags: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            return validate_string_length(v, 'name', 1, 200)
        return v

    @field_validator('description', 'category')
    @classmethod
    def validate_string_fields(cls, v):
        if v is not None:
            return v.strip()
        return v


class SurveyTemplateResponse(SurveyTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    fields: List[TemplateFieldResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# AppConfig Schemas
class AppConfigBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(default="")
    description: str = Field(default="", max_length=300)
    category: str = Field(default="", max_length=50)

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        return validate_string_length(v, 'key', 1, 100)

    @field_validator('value', 'description', 'category')
    @classmethod
    def validate_string_fields(cls, v):
        if v:
            return v.strip()
        return v or ""


class AppConfigCreate(AppConfigBase):
    pass


class AppConfigUpdate(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = None
    description: Optional[str] = Field(None, max_length=300)
    category: Optional[str] = Field(None, max_length=50)

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if v is not None:
            return validate_string_length(v, 'key', 1, 100)
        return v

    @field_validator('value', 'description', 'category')
    @classmethod
    def validate_string_fields(cls, v):
        if v is not None:
            return v.strip()
        return v


class AppConfigResponse(AppConfigBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Photo List Response Schema
class PhotoListResponse(BaseModel):
    id: str
    survey_id: Optional[int] = None
    site_id: Optional[int] = None
    cloud_url: str = ""
    thumbnail_url: str = ""
    upload_status: str = "pending"
    latitude: float = 0.0
    longitude: float = 0.0
    description: str = ""
    category: str = "general"
    created_at: datetime
    hash_value: str = ""
    size_bytes: int = 0
    tags: List[str] = Field(default_factory=list)

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    model_config = ConfigDict(from_attributes=True)


# Photo Detail Response Schema (with optional image_data)
class PhotoDetailResponse(PhotoBase):
    id: str
    created_at: datetime
    image_data: Optional[str] = None  # Hex string when include_data=true
    error: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# Photo Integrity Response Schema
class PhotoIntegrityResponse(BaseModel):
    photo_id: str
    stored_hash: str
    current_hash: Optional[str] = None
    hash_matches: bool
    size_bytes: int
    actual_size: int
    size_matches: bool
    upload_status: str
    cloud_url: str
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Photo Requirement Fulfillment Request Schema
class PhotoRequirementFulfillmentRequest(BaseModel):
    photo_id: str = Field(..., min_length=1)
    requirement_id: Optional[str] = Field(None, max_length=200)
    fulfills: bool = Field(default=True)

    @field_validator('photo_id', 'requirement_id')
    @classmethod
    def validate_string_fields(cls, v):
        if v is not None:
            return v.strip()
        return v


# Photo Requirement Fulfillment Response Schema
class PhotoRequirementFulfillmentResponse(BaseModel):
    photo_id: str
    requirement_id: Optional[str] = None
    fulfills: bool
    message: str


# Survey with Responses Schema
class SurveyWithResponsesResponse(SurveyResponseSchema):
    responses: List[SurveyResponseResponse] = Field(default_factory=list)

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# Template List Item Schema
class TemplateListItem(BaseModel):
    id: int
    name: str
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    section_tags: Dict[str, List[str]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


# Template Detail Response Schema (already exists as SurveyTemplateResponse, but add field details)
class TemplateFieldDetailResponse(TemplateFieldResponse):
    conditions: Optional[Dict[str, Any]] = None
    photo_requirements: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# Template Conditional Fields Response Schema
class ConditionalFieldResponse(BaseModel):
    id: int
    field_type: str
    question: str
    description: str
    required: bool
    options: str
    order_index: int
    section: str
    section_weight: int
    conditions: Optional[Dict[str, Any]] = None
    photo_requirements: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class TemplateConditionalFieldsResponse(BaseModel):
    template_id: int
    fields: List[ConditionalFieldResponse] = Field(default_factory=list)
    section_tags: Dict[str, List[str]] = Field(default_factory=dict)


# Section Tags Update Request Schema
class SectionTagsUpdateRequest(BaseModel):
    section_tags: Dict[str, List[str]] = Field(..., min_length=1)

    @field_validator('section_tags')
    @classmethod
    def validate_section_tags(cls, v):
        if not isinstance(v, dict):
            raise ValueError('section_tags must be a dictionary')
        validated = {}
        for section, tags in v.items():
            if not isinstance(section, str):
                raise ValueError('Section names must be strings')
            if not isinstance(tags, list):
                raise ValueError(f'Tags for section {section} must be a list')
            validated_tags = []
            for tag in tags:
                if not isinstance(tag, str):
                    tag = str(tag)
                tag_cleaned = tag.strip()
                if tag_cleaned and tag_cleaned not in validated_tags:
                    validated_tags.append(tag_cleaned)
            max_tags = get_max_section_tags_limit()
            if len(validated_tags) > max_tags:
                validated_tags = validated_tags[:max_tags]
            validated[section.strip()] = validated_tags
        return validated


class SectionTagsUpdateResponse(BaseModel):
    template_id: int
    section_tags: Dict[str, List[str]]


# Survey Condition Evaluation Request Schema
class SurveyConditionEvaluationRequest(BaseModel):
    responses: List[Dict[str, Any]] = Field(default_factory=list, max_length=1000)

    @field_validator('responses')
    @classmethod
    def validate_responses(cls, v):
        if len(v) > 1000:
            raise ValueError('Too many responses (max 1000)')
        for response in v:
            if not isinstance(response, dict):
                raise ValueError('Each response must be a JSON object')
        return v


class SurveyConditionEvaluationResponse(BaseModel):
    survey_id: int
    visible_fields: List[int] = Field(default_factory=list)


# Survey Progress Response Schema
class SectionProgress(BaseModel):
    required: int = 0
    completed: int = 0
    photos_required: int = 0
    photos_taken: int = 0
    weight: int = 1
    progress: float = 0.0


class SurveyProgressResponse(BaseModel):
    overall_progress: float
    sections: Dict[str, SectionProgress] = Field(default_factory=dict)
    total_required: int = 0
    total_completed: int = 0


# Photo Requirements Response Schema
class PhotoRequirementData(BaseModel):
    field_id: int
    field_question: str
    taken: bool


class PhotoRequirementsResponse(BaseModel):
    survey_id: int
    requirements_by_section: Dict[str, List[PhotoRequirementData]] = Field(default_factory=dict)


# Config Response Schemas
class ConfigValueResponse(BaseModel):
    value: str
    description: str
    category: str


class AllConfigResponse(BaseModel):
    config: Dict[str, ConfigValueResponse] = Field(default_factory=dict)


class SingleConfigResponse(AppConfigResponse):
    pass


# Cloud Storage Config Response Schema
class CloudStorageConfigResponse(BaseModel):
    cloud_storage: Dict[str, str] = Field(default_factory=dict)
    message: str


# Cloud Storage Test Response Schema
class CloudStorageTestResponse(BaseModel):
    status: str
    message: str
    containers: Optional[List[str]] = None
    provider: Optional[str] = None


# Cloud Storage Status Response Schema
class CloudStorageStatusResponse(BaseModel):
    upload_queue_running: bool
    pending_uploads: int
    completed_uploads: int
    failed_uploads: int
    local_storage_path: str


# CRDT Change Schema
class CRDTChange(BaseModel):
    table: str = Field(..., min_length=1)
    pk: str = Field(..., min_length=1)
    cid: str = Field(..., min_length=1)
    val: Any
    col_version: int = Field(..., ge=0)
    db_version: int = Field(..., ge=0)
    site_id: str = Field(..., min_length=1)

    @field_validator('table')
    @classmethod
    def validate_table(cls, v):
        valid_tables = ['projects', 'sites', 'survey', 'survey_response', 
                        'survey_template', 'template_field', 'photo']
        if v not in valid_tables:
            raise ValueError(f'table must be one of: {", ".join(valid_tables)}')
        return v


class CRDTChangesRequest(BaseModel):
    changes: List[CRDTChange] = Field(..., min_length=1)


class CRDTChangesResponse(BaseModel):
    message: str
    integrity_issues: Optional[List[Dict[str, Any]]] = None


class CRDTGetChangesResponse(BaseModel):
    changes: List[CRDTChange] = Field(default_factory=list)

