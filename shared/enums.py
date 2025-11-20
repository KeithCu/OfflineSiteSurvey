import enum


class ProjectStatus(str, enum.Enum):
    """Project status values used throughout the application.
    
    Used in Project model to track project lifecycle stages.
    """
    ARCHIVED = "archived"
    COMPLETED = "completed"
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"


class SurveyStatus(str, enum.Enum):
    """Survey status values used throughout the application.
    
    Used in Survey model to track survey lifecycle stages.
    """
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"
    DRAFT = "draft"


class PhotoCategory(str, enum.Enum):
    """Photo category tags for organizing photos.
    
    Used in Photo model to categorize photos by type or purpose.
    """
    EXTERIOR = "exterior"
    GENERAL = "general"
    INTERIOR = "interior"
    ISSUES = "issues"
    PROGRESS = "progress"


class PriorityLevel(str, enum.Enum):
    """Priority levels for projects and tasks.
    
    Used in Project model and other entities to indicate urgency.
    """
    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"
