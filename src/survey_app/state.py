"""Application state management for SurveyApp."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set


@dataclass
class SessionState:
    """Centralized application state management.
    
    Holds all state variables that were previously stored directly on SurveyApp.
    This provides better separation of concerns and makes state management explicit.
    """
    # Current selection state
    current_project: Optional[object] = None
    current_survey: Optional[dict] = None
    current_site: Optional[object] = None
    
    # Survey response state
    responses: List[dict] = field(default_factory=list)
    current_responses: List[dict] = field(default_factory=list)
    response_lookup: Dict[str, str] = field(default_factory=dict)
    
    # Template and field state
    template_fields: List[dict] = field(default_factory=list)
    total_fields: int = 0
    current_question_index: int = 0
    visible_fields: List[dict] = field(default_factory=list)
    
    # Progress tracking
    section_progress: Dict[str, float] = field(default_factory=dict)
    photo_requirements: Dict[str, dict] = field(default_factory=dict)
    
    # Photo tag state
    section_tags: Dict[str, List[str]] = field(default_factory=dict)
    current_section: str = 'General'
    selected_photo_tags: Set[str] = field(default_factory=set)
    section_tag_switches: Dict[str, object] = field(default_factory=dict)
    
    # Sync state
    last_sync_version: int = 0
    offline_queue: List[dict] = field(default_factory=list)
    
    # Auto-save state
    auto_save_timer: Optional[object] = None
    draft_responses: Dict[str, dict] = field(default_factory=dict)
    
    # Temporary UI state (for windows/dialogs)
    projects_data: Optional[List] = None
    sites_data: Optional[List] = None
    templates_data: Optional[List] = None
    
    def reset_survey_state(self):
        """Reset survey-related state when starting a new survey."""
        self.responses = []
        self.current_responses = []
        self.response_lookup = {}
        self.current_question_index = 0
        self.visible_fields = []
        self.section_progress = {}
        self.photo_requirements = {}
        self.selected_photo_tags.clear()
        self.draft_responses = {}
    
    def clear_photo_tag_selection(self):
        """Reset photo tag selection for current section."""
        self.selected_photo_tags.clear()
        for switch in list(self.section_tag_switches.values()):
            try:
                switch.is_on = False
            except AttributeError:
                pass

