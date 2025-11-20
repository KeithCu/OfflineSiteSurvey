"""UI Manager for Survey App - handles all UI creation and management."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from shared.enums import QuestionType
from .ui.ui_builder import (
    create_label, create_text_input, create_button, create_selection,
    SurveyQuestionWidget, SurveyProgressWidget
)


class UIManager:
    """Manages UI creation and state for the Survey App."""

    def __init__(self, app):
        self.app = app
        self.main_window = None
        self._init_ui_components()

    def _init_ui_components(self):
        """Initialize UI component references."""
        # Main UI components
        self.survey_selection = None
        self.status_label = None
        
        # Composite widgets
        self.question_widget = None
        self.progress_widget = None

    def create_main_ui(self):
        """Create the main user interface."""
        # Header
        header_label = create_label(
            'Site Survey App',
            style_overrides={'font_size': 24, 'padding': (10, 10, 20, 10)}
        )

        # Survey selection
        survey_label = create_label('Select Survey:')

        self.survey_selection = create_selection(
            items=['Select a site first...']
        )

        select_survey_button = create_button(
            'Start Survey',
            on_press=self.app.start_survey
        )

        # Navigation buttons
        projects_button = create_button(
            'Projects',
            on_press=self.app.show_projects_ui
        )

        sites_button = create_button(
            'Sites',
            on_press=self.app.show_sites_ui
        )

        templates_button = create_button(
            'Templates',
            on_press=self.app.show_templates_ui
        )

        photos_button = create_button(
            'Photos',
            on_press=self.app.show_photos_ui
        )

        sync_button = create_button(
            'Sync Now',
            on_press=self.app.sync_with_server
        )

        manage_tags_button = create_button(
            'Manage Tags',
            on_press=self.app.tag_management_handler.show_tag_management_ui
        )

        config_button = create_button(
            'Settings',
            on_press=self.app.show_config_ui
        )

        # Enhanced survey form components
        self.survey_title_label = create_label(
            '',
            style_overrides={'font_size': 18, 'padding': (20, 10, 10, 10), 'font_weight': 'bold'}
        )

        # Use composite widgets
        self.progress_widget = SurveyProgressWidget()
        self.question_widget = SurveyQuestionWidget()
        
        # Wire up question widget handlers
        self.question_widget.answer_input.on_change = self.app.on_answer_input_change
        self.question_widget.yes_button.on_press = lambda w: self.app.submit_yesno_answer('Yes')
        self.question_widget.no_button.on_press = lambda w: self.app.submit_yesno_answer('No')
        self.question_widget.photo_button.on_press = self.app.take_photo_enhanced

        submit_answer_button = create_button(
            'Submit Answer',
            on_press=self.app.submit_answer
        )

        next_question_button = create_button(
            'Next Question',
            on_press=self.app.next_question
        )

        finish_survey_button = create_button(
            'Finish Survey',
            on_press=self.app.finish_survey
        )

        # Status label
        self.status_label = create_label(
            'Ready',
            style_overrides={'padding': (10, 10, 10, 10), 'color': '#666666'}
        )

        # Initially hide enhanced survey form
        self._hide_enhanced_survey_ui()

        # Create main box
        main_box = toga.Box(
            children=[
                header_label,
                survey_label,
                self.survey_selection,
                select_survey_button,
                projects_button,
                sites_button,
                templates_button,
                photos_button,
                config_button,
                sync_button,
                manage_tags_button,
                self.survey_title_label,
                self.progress_widget,
                self.question_widget,
                submit_answer_button,
                next_question_button,
                finish_survey_button,
                self.status_label
            ],
            style=Pack(direction=COLUMN, padding=10)
        )

        self.main_window.content = main_box

    def _hide_enhanced_survey_ui(self):
        """Hide all enhanced survey UI elements."""
        if self.survey_title_label:
            self.survey_title_label.style.visibility = 'hidden'
        if self.progress_widget:
            self.progress_widget.set_visible(False)
        if self.question_widget:
            self.question_widget.set_visible(False)

    def show_enhanced_survey_ui(self):
        """Show enhanced survey UI elements."""
        if self.survey_title_label:
            self.survey_title_label.style.visibility = 'visible'
        if self.progress_widget:
            self.progress_widget.set_visible(True)
        if self.question_widget:
            self.question_widget.set_visible(True)

    def hide_enhanced_survey_ui(self):
        """Hide enhanced survey UI elements."""
        self._hide_enhanced_survey_ui()

    def show_question_ui(self, field_type, options=None, description=None):
        """Show appropriate UI elements for a question field type."""
        if not self.question_widget:
            return
        
        # Show appropriate input based on field type
        if field_type == QuestionType.YESNO.value:
            self.question_widget.show_yesno_buttons(
                on_yes=lambda w: self.app.submit_yesno_answer('Yes'),
                on_no=lambda w: self.app.submit_yesno_answer('No')
            )
        elif field_type == QuestionType.PHOTO.value:
            self.question_widget.show_photo_button(on_press=self.app.take_photo_enhanced)
        elif options:
            self.question_widget.show_selection(items=options)
        else:
            self.question_widget.show_text_input(
                placeholder=description or 'Enter your answer',
                value='',
                on_change=self.app.on_answer_input_change
            )
    
    # Backward compatibility properties
    @property
    def question_label(self):
        """Backward compatibility: access question label."""
        return self.question_widget.question_label if self.question_widget else None
    
    @property
    def answer_input(self):
        """Backward compatibility: access answer input."""
        return self.question_widget.answer_input if self.question_widget else None
    
    @property
    def yes_button(self):
        """Backward compatibility: access yes button."""
        return self.question_widget.yes_button if self.question_widget else None
    
    @property
    def no_button(self):
        """Backward compatibility: access no button."""
        return self.question_widget.no_button if self.question_widget else None
    
    @property
    def options_selection(self):
        """Backward compatibility: access options selection."""
        return self.question_widget.options_selection if self.question_widget else None
    
    @property
    def enhanced_photo_button(self):
        """Backward compatibility: access photo button."""
        return self.question_widget.photo_button if self.question_widget else None
    
    @property
    def progress_label(self):
        """Backward compatibility: access progress label."""
        return self.progress_widget.progress_label if self.progress_widget else None
