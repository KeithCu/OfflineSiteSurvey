"""UI Manager for Survey App - handles all UI creation and management."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .ui.ui_builder import create_label, create_text_input, create_button, create_selection


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
        self.progress_label = None
        self.question_label = None
        self.answer_input = None
        self.yes_button = None
        self.no_button = None
        self.options_selection = None
        self.enhanced_photo_button = None
        self.status_label = None

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

        self.progress_label = create_label(
            '',
            style_overrides={'color': '#666666'}
        )

        self.question_label = create_label(
            '',
            style_overrides={'padding': (10, 10, 5, 10)}
        )

        self.answer_input = create_text_input(
            placeholder='Enter your answer',
            on_change=self.app.on_answer_input_change
        )

        self.yes_button = create_button(
            'Yes',
            on_press=lambda w: self.app.submit_yesno_answer('Yes'),
            style_overrides={'padding': (5, 10, 5, 5)}
        )
        self.no_button = create_button(
            'No',
            on_press=lambda w: self.app.submit_yesno_answer('No'),
            style_overrides={'padding': (5, 10, 10, 5)}
        )

        self.options_selection = create_selection()

        self.enhanced_photo_button = create_button(
            '📷 Take Photo',
            on_press=self.app.take_photo_enhanced
        )

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
                self.progress_label,
                self.question_label,
                self.answer_input,
                self.yes_button,
                self.no_button,
                self.options_selection,
                self.enhanced_photo_button,
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
        if self.progress_label:
            self.progress_label.style.visibility = 'hidden'
        if self.question_label:
            self.question_label.style.visibility = 'hidden'
        if self.answer_input:
            self.answer_input.style.visibility = 'hidden'
        if self.yes_button:
            self.yes_button.style.visibility = 'hidden'
        if self.no_button:
            self.no_button.style.visibility = 'hidden'
        if self.options_selection:
            self.options_selection.style.visibility = 'hidden'
        if self.enhanced_photo_button:
            self.enhanced_photo_button.style.visibility = 'hidden'

    def show_enhanced_survey_ui(self):
        """Show enhanced survey UI elements."""
        if self.survey_title_label:
            self.survey_title_label.style.visibility = 'visible'
        if self.progress_label:
            self.progress_label.style.visibility = 'visible'
        if self.question_label:
            self.question_label.style.visibility = 'visible'

    def hide_enhanced_survey_ui(self):
        """Hide enhanced survey UI elements."""
        self._hide_enhanced_survey_ui()

    def show_question_ui(self, field_type, options=None, description=None):
        """Show appropriate UI elements for a question field type."""
        # Hide all input elements first
        if self.answer_input:
            self.answer_input.style.visibility = 'hidden'
        if self.yes_button:
            self.yes_button.style.visibility = 'hidden'
        if self.no_button:
            self.no_button.style.visibility = 'hidden'
        if self.options_selection:
            self.options_selection.style.visibility = 'hidden'
        if self.enhanced_photo_button:
            self.enhanced_photo_button.style.visibility = 'hidden'

        # Show appropriate input based on field type
        if field_type == 'yesno':
            if self.yes_button:
                self.yes_button.style.visibility = 'visible'
            if self.no_button:
                self.no_button.style.visibility = 'visible'
        elif field_type == 'photo':
            if self.enhanced_photo_button:
                self.enhanced_photo_button.style.visibility = 'visible'
        elif options:
            if self.options_selection:
                self.options_selection.items = options
                self.options_selection.style.visibility = 'visible'
        else:
            if self.answer_input:
                self.answer_input.placeholder = description or 'Enter your answer'
                self.answer_input.value = ''
                self.answer_input.style.visibility = 'visible'
