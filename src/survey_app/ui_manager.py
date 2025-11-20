"""UI Manager for Survey App - handles all UI creation and management."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


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

        # Legacy UI components
        self.question_box = None
        self.photo_box = None
        self.progress_bar = None

    def _create_button(self, label, action=None, padding=(5, 10, 10, 10), **style_kwargs):
        """Create a button with consistent styling."""
        style = Pack(padding=padding, **style_kwargs)
        return toga.Button(label, on_press=action, style=style)

    def _create_label(self, text, padding=(5, 10, 5, 10), font_size=None, font_weight=None, color=None, **style_kwargs):
        """Create a label with consistent styling."""
        style_dict = {'padding': padding}
        if font_size:
            style_dict['font_size'] = font_size
        if font_weight:
            style_dict['font_weight'] = font_weight
        if color:
            style_dict['color'] = color
        style_dict.update(style_kwargs)
        return toga.Label(text, style=Pack(**style_dict))

    def _create_text_input(self, placeholder=None, padding=(5, 10, 10, 10), on_change=None, **style_kwargs):
        """Create a text input with consistent styling."""
        widget = toga.TextInput(placeholder=placeholder, style=Pack(padding=padding, **style_kwargs))
        if on_change:
            widget.on_change = on_change
        return widget

    def _create_selection(self, items=None, padding=(5, 10, 10, 10), **style_kwargs):
        """Create a selection widget with consistent styling."""
        return toga.Selection(items=items or [], style=Pack(padding=padding, **style_kwargs))

    def _create_box(self, children=None, direction=COLUMN, padding=10, visibility=None, **style_kwargs):
        """Create a box container with consistent styling."""
        style_dict = {'direction': direction, 'padding': padding}
        if visibility:
            style_dict['visibility'] = visibility
        style_dict.update(style_kwargs)
        return toga.Box(children=children or [], style=Pack(**style_dict))

    def _create_image_view(self, height=200, **style_kwargs):
        """Create an image view with consistent styling."""
        return toga.ImageView(style=Pack(height=height, **style_kwargs))

    def _create_progress_bar(self, max=100, value=0, padding=(10, 10, 10, 10), **style_kwargs):
        """Create a progress bar with consistent styling."""
        return toga.ProgressBar(max=max, value=value, style=Pack(padding=padding, **style_kwargs))

    def create_main_ui(self):
        """Create the main user interface."""
        # Header
        header_label = self._create_label('Site Survey App', padding=(10, 10, 20, 10), font_size=24)

        # Survey selection
        survey_label = self._create_label('Select Survey:')
        self.survey_selection = self._create_selection(items=['Select a site first...'])
        select_survey_button = self._create_button('Start Survey', self.app.start_survey)

        # Navigation buttons
        projects_button = self._create_button('Projects', self.app.show_projects_ui)
        sites_button = self._create_button('Sites', self.app.show_sites_ui)
        templates_button = self._create_button('Templates', self.app.show_templates_ui)
        photos_button = self._create_button('Photos', self.app.show_photos_ui)
        sync_button = self._create_button('Sync Now', self.app.sync_with_server)
        manage_tags_button = self._create_button('Manage Tags', self.app.tag_management_handler.show_tag_management_ui)
        config_button = self._create_button('Settings', self.app.show_config_ui)

        # Enhanced survey form components
        self.survey_title_label = self._create_label('', padding=(20, 10, 10, 10), font_size=18, font_weight='bold')
        self.progress_label = self._create_label('', color='#666666')
        self.question_label = self._create_label('', padding=(10, 10, 5, 10))
        self.answer_input = self._create_text_input('Enter your answer', on_change=self.app.on_answer_input_change)
        self.yes_button = self._create_button('Yes', lambda w: self.app.submit_yesno_answer('Yes'), padding=(5, 10, 5, 5))
        self.no_button = self._create_button('No', lambda w: self.app.submit_yesno_answer('No'), padding=(5, 10, 10, 5))
        self.options_selection = self._create_selection()
        self.enhanced_photo_button = self._create_button('📷 Take Photo', self.app.take_photo_enhanced)
        submit_answer_button = self._create_button('Submit Answer', self.app.submit_answer)
        next_question_button = self._create_button('Next Question', self.app.next_question)
        finish_survey_button = self._create_button('Finish Survey', self.app.finish_survey)

        # Legacy UI components
        self.question_box = self._create_box(direction=COLUMN, visibility='hidden')
        question_label_legacy = self._create_label("Question")
        answer_input_legacy = self._create_text_input()
        answer_selection = self._create_selection()
        next_question_button_legacy = self._create_button('Next', self.app.next_question)
        self.progress_bar = self._create_progress_bar()
        self.question_box.add(question_label_legacy, answer_input_legacy, answer_selection, next_question_button_legacy, self.progress_bar)

        # Photo UI
        self.photo_box = self._create_box(direction=COLUMN, visibility='hidden')
        take_photo_button = self._create_button('Take Photo', self.app.take_photo)
        image_view = self._create_image_view()
        photo_description_input = self._create_text_input('Photo description')
        photo_location_input = self._create_text_input('Photo location (lat, long)')
        save_photo_button = self._create_button('Save Photo', self.app.save_photo)
        self.photo_box.add(take_photo_button, image_view, photo_description_input, photo_location_input, save_photo_button)

        # Status label
        self.status_label = self._create_label('Ready', padding=(10, 10, 10, 10), color='#666666')

        # Initially hide enhanced survey form
        self._hide_enhanced_survey_ui()

        # Create main box
        main_box = self._create_box(
            children=[
                header_label, survey_label, self.survey_selection, select_survey_button,
                projects_button, sites_button, templates_button, photos_button, config_button,
                sync_button, manage_tags_button, self.question_box, self.photo_box,
                self.survey_title_label, self.progress_label, self.question_label, self.answer_input,
                self.yes_button, self.no_button, self.options_selection, self.enhanced_photo_button,
                submit_answer_button, next_question_button, finish_survey_button, self.status_label
            ],
            direction=COLUMN
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
        if self.question_box:
            self.question_box.style.visibility = 'hidden'
        if self.photo_box:
            self.photo_box.style.visibility = 'hidden'

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
