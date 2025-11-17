"""Survey UI components for SurveyApp."""
import toga


class SurveyUI:
    """Handles survey-related UI components."""

    def __init__(self, app):
        self.app = app

    def create_main_ui(self):
        """Create the main user interface"""
        # Header
        header_label = toga.Label(
            'Site Survey App',
            style=toga.Pack(font_size=24, padding=(10, 10, 20, 10))
        )

        # Survey selection
        survey_label = toga.Label(
            'Select Survey:',
            style=toga.Pack(padding=(5, 10, 5, 10))
        )

        self.app.survey_selection = toga.Selection(
            items=['Select a site first...'],
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        select_survey_button = toga.Button(
            'Start Survey',
            on_press=self.app.survey_handler.start_survey,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        projects_button = toga.Button(
            'Projects',
            on_press=self.app.project_handler.show_projects_ui,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        sites_button = toga.Button(
            'Sites',
            on_press=self.app.site_handler.show_sites_ui,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        templates_button = toga.Button(
            'Templates',
            on_press=self.app.template_handler.show_templates_ui,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        photos_button = toga.Button(
            'Photos',
            on_press=self.app.photo_handler.show_photos_ui,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        # Enhanced survey form (initially hidden)
        self.app.survey_title_label = toga.Label(
            '',
            style=toga.Pack(font_size=18, padding=(20, 10, 10, 10), font_weight='bold')
        )

        # Progress indicator
        self.app.progress_label = toga.Label(
            '',
            style=toga.Pack(padding=(5, 10, 5, 10), color='#666666')
        )

        # Field type specific UI elements
        self.app.yes_button = toga.Button(
            'Yes',
            on_press=lambda w: self.app.survey_handler.submit_yesno_answer('Yes'),
            style=toga.Pack(padding=(5, 10, 5, 5))
        )
        self.app.no_button = toga.Button(
            'No',
            on_press=lambda w: self.app.survey_handler.submit_yesno_answer('No'),
            style=toga.Pack(padding=(5, 10, 10, 5))
        )

        self.app.options_selection = toga.Selection(
            items=[],
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        self.app.enhanced_photo_button = toga.Button(
            '📷 Take Photo',
            on_press=self.app.survey_handler.take_photo_enhanced,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        submit_answer_button = toga.Button(
            'Submit Answer',
            on_press=self.app.survey_handler.submit_answer,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        next_question_button = toga.Button(
            'Next Question',
            on_press=self.app.survey_handler.next_question,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        finish_survey_button = toga.Button(
            'Finish Survey',
            on_press=self.app.survey_handler.finish_survey,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        sync_button = toga.Button(
            'Sync Now',
            on_press=self.app.sync_handler.sync_with_server,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        config_button = toga.Button(
            'Settings',
            on_press=self.app.sync_handler.show_config_ui,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        # Question UI (legacy)
        self.app.question_box = toga.Box(style=toga.Pack(direction=toga.COLUMN, padding=10, visibility='hidden'))
        self.app.question_label_legacy = toga.Label("Question", style=toga.Pack(padding=(5, 10, 5, 10)))
        self.app.answer_input_legacy = toga.TextInput(style=toga.Pack(padding=(5, 10, 10, 10)))
        self.app.answer_selection = toga.Selection(style=toga.Pack(padding=(5, 10, 10, 10)))

        next_question_button_legacy = toga.Button('Next', on_press=self.app.survey_handler.next_question, style=toga.Pack(padding=(5, 10, 10, 10)))

        self.app.progress_bar = toga.ProgressBar(max=100, value=0, style=toga.Pack(padding=(10, 10, 10, 10)))
        self.app.question_box.add(self.app.question_label_legacy, self.app.answer_input_legacy, self.app.answer_selection, next_question_button_legacy, self.app.progress_bar)

        # Enhanced question UI elements (separate from legacy)
        self.app.question_label = toga.Label(
            '',
            style=toga.Pack(padding=(10, 10, 5, 10))
        )

        self.app.answer_input = toga.TextInput(
            placeholder='Enter your answer',
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        # Wire up auto-save to text input changes
        self.app.answer_input.on_change = self.app.survey_handler.on_answer_input_change

        # Photo capture UI
        self.app.photo_box = toga.Box(style=toga.Pack(direction=toga.COLUMN, padding=10, visibility='hidden'))

        take_photo_button = toga.Button(
            'Take Photo',
            on_press=self.app.photo_handler.take_photo,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        self.app.image_view = toga.ImageView(style=toga.Pack(height=200))

        self.app.photo_description_input = toga.TextInput(
            placeholder='Photo description',
            style=toga.Pack(padding=(5, 10, 10, 10))
        )
        self.app.photo_location_input = toga.TextInput(
            placeholder='Photo location (lat, long)',
            style=toga.Pack(padding=(5, 10, 10, 10))
        )
        save_photo_button = toga.Button(
            'Save Photo',
            on_press=self.app.photo_handler.save_photo,
            style=toga.Pack(padding=(5, 10, 10, 10))
        )

        self.app.photo_box.add(
            take_photo_button,
            self.app.image_view,
            self.app.photo_description_input,
            self.app.photo_location_input,
            save_photo_button
        )

        # Status label
        self.app.status_label = toga.Label(
            'Ready',
            style=toga.Pack(padding=(10, 10, 10, 10), color='#666666')
        )

        # Initially hide enhanced survey form
        self.app.survey_title_label.style.visibility = 'hidden'
        self.app.progress_label.style.visibility = 'hidden'
        self.app.question_label.style.visibility = 'hidden'
        self.app.answer_input.style.visibility = 'hidden'
        self.app.yes_button.style.visibility = 'hidden'
        self.app.no_button.style.visibility = 'hidden'
        self.app.options_selection.style.visibility = 'hidden'
        self.app.enhanced_photo_button.style.visibility = 'hidden'
        submit_answer_button.style.visibility = 'hidden'
        next_question_button.style.visibility = 'hidden'
        finish_survey_button.style.visibility = 'hidden'
        sync_button.style.visibility = 'hidden'

        # Create main box
        main_box = toga.Box(
            children=[
                header_label,
                survey_label,
                self.app.survey_selection,
                select_survey_button,
                projects_button,
                sites_button,
                templates_button,
                photos_button,
                config_button,
                self.app.question_box,
                self.app.photo_box,
                self.app.survey_title_label,
                self.app.progress_label,
                self.app.question_label,
                self.app.answer_input,
                self.app.yes_button,
                self.app.no_button,
                self.app.options_selection,
                self.app.enhanced_photo_button,
                submit_answer_button,
                next_question_button,
                finish_survey_button,
                sync_button,
                self.app.status_label
            ],
            style=toga.Pack(direction=toga.COLUMN, padding=10)
        )

        self.app.main_window.content = main_box

    def show_survey_ui(self):
        """Show the enhanced survey interface"""
        self.app.survey_title_label.style.visibility = 'visible'
        self.app.progress_label.style.visibility = 'visible'
        self.app.question_label.style.visibility = 'visible'
        self.app.survey_title_label.text = self.app.current_survey['title']

    def show_question(self):
        """Show the current question in enhanced UI with Phase 2 features"""
        # Update progress
        self.update_progress()

        # Hide all input elements first
        self.app.answer_input.style.visibility = 'hidden'
        self.app.yes_button.style.visibility = 'hidden'
        self.app.no_button.style.visibility = 'hidden'
        self.app.options_selection.style.visibility = 'hidden'
        self.app.enhanced_photo_button.style.visibility = 'hidden'

        # Find the next visible field
        visible_field = self.app.survey_handler.get_next_visible_field()

        if not visible_field:
            self.app.survey_handler.finish_survey(None)
            return

        # Update question label with required indicator
        required_indicator = " * " if visible_field.get('required', False) else " "
        self.app.question_label.text = f"{required_indicator}{visible_field['question']}"

        # Handle different field types
        field_type = visible_field.get('field_type', 'text')
        if field_type == 'yesno':
            self.app.yes_button.style.visibility = 'visible'
            self.app.no_button.style.visibility = 'visible'
        elif field_type == 'photo':
            self.app.enhanced_photo_button.style.visibility = 'visible'
            # Show photo requirements if available
            if visible_field.get('photo_requirements'):
                self.show_photo_requirements(visible_field['photo_requirements'])
        elif visible_field.get('options'):
            # Multiple choice
            self.app.options_selection.items = visible_field['options']
            self.app.options_selection.style.visibility = 'visible'
        else:
            # Text input
            self.app.answer_input.placeholder = visible_field.get('description', 'Enter your answer')
            self.app.answer_input.value = ''
            self.app.answer_input.style.visibility = 'visible'

    def show_photo_requirements(self, photo_requirements):
        """Show photo requirements for current photo field"""
        # This would show a small popup or label with photo requirements
        # For now, just update status
        req_text = photo_requirements.get('description', 'Photo required')
        self.app.status_label.text = f"Photo requirement: {req_text}"

    def update_progress(self):
        """Update progress indicator with enhanced Phase 2 tracking"""
        if self.app.current_survey:
            # Get detailed progress from database
            progress_data = self.app.db.get_survey_progress(self.app.current_survey['id'])
            self.app.section_progress = progress_data.get('sections', {})
            overall_progress = progress_data.get('overall_progress', 0)

            # Update progress bar
            self.app.progress_bar.value = overall_progress

            # Update progress label with detailed information
            total_required = progress_data.get('total_required', 0)
            total_completed = progress_data.get('total_completed', 0)
            self.app.progress_label.text = f"Progress: {total_completed}/{total_required} ({overall_progress:.1f}%)"
        else:
            # Fallback to basic progress calculation
            if hasattr(self.app, 'questions') and self.app.questions:
                progress = (self.app.current_question_index / len(self.app.questions)) * 100
                self.app.progress_bar.value = progress
            elif self.app.total_fields > 0:
                progress = (self.app.current_question_index / self.app.total_fields) * 100
                self.app.progress_bar.value = progress
            else:
                self.app.progress_bar.value = 0

    def display_question(self):
        """Display question in legacy UI"""
        if self.app.current_question_index < len(self.app.questions):
            question = self.app.questions[self.app.current_question_index]
            self.app.question_label_legacy.text = question['question']
            if question['field_type'] == 'text':
                self.app.answer_input_legacy.style.visibility = 'visible'
                self.app.answer_selection.style.visibility = 'hidden'
            elif question['field_type'] == 'multiple_choice':
                self.app.answer_input_legacy.style.visibility = 'hidden'
                self.app.answer_selection.style.visibility = 'visible'
                self.app.answer_selection.items = json.loads(question['options'])
        else:
            self.app.question_box.style.visibility = 'hidden'
            self.app.status_label.text = "Survey complete!"
        self.update_progress()