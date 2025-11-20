"""Survey UI components for SurveyApp."""
import toga
from .ui_builder import (
    create_label, create_button, create_selection,
    SurveyQuestionWidget, SurveyProgressWidget
)


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
        self.app.survey_title_label = create_label(
            '',
            style_overrides={'font_size': 18, 'padding': (20, 10, 10, 10), 'font_weight': 'bold'}
        )

        # Use composite widgets
        self.app.progress_widget = SurveyProgressWidget()
        self.app.question_widget = SurveyQuestionWidget()
        
        # Wire up question widget handlers
        self.app.question_widget.answer_input.on_change = self.app.survey_handler.on_answer_input_change
        self.app.question_widget.yes_button.on_press = lambda w: self.app.survey_handler.submit_yesno_answer('Yes')
        self.app.question_widget.no_button.on_press = lambda w: self.app.survey_handler.submit_yesno_answer('No')
        self.app.question_widget.photo_button.on_press = self.app.survey_handler.take_photo_enhanced
        
        # Backward compatibility: expose individual components
        self.app.progress_label = self.app.progress_widget.progress_label
        self.app.question_label = self.app.question_widget.question_label
        self.app.answer_input = self.app.question_widget.answer_input
        self.app.yes_button = self.app.question_widget.yes_button
        self.app.no_button = self.app.question_widget.no_button
        self.app.options_selection = self.app.question_widget.options_selection
        self.app.enhanced_photo_button = self.app.question_widget.photo_button

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

        self.sync_companycam_button = toga.Button(
            '📤 Sync to CompanyCam',
            on_press=self.app.companycam_handler.sync_survey_to_companycam,
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

        # Enhanced question UI elements (already created above via composite widget)

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
        self.app.section_tag_label = toga.Label(
            'Section Tags',
            style=toga.Pack(font_size=12, padding=(5, 5, 5, 5))
        )
        self.app.section_tag_switches_box = toga.Box(
            style=toga.Pack(direction=toga.COLUMN, padding=(0, 5, 5, 5))
        )
        self.app.section_tags_box = toga.Box(
            children=[self.app.section_tag_label, self.app.section_tag_switches_box],
            style=toga.Pack(direction=toga.COLUMN, padding=(5, 0, 5, 0), background_color='#f9f9f9')
        )
        self.app.photo_box.add(self.app.section_tags_box)

        # Status label
        self.app.status_label = toga.Label(
            'Ready',
            style=toga.Pack(padding=(10, 10, 10, 10), color='#666666')
        )

        # Initially hide enhanced survey form
        self.app.survey_title_label.style.visibility = 'hidden'
        self.app.progress_widget.set_visible(False)
        self.app.question_widget.set_visible(False)
        submit_answer_button.style.visibility = 'hidden'
        next_question_button.style.visibility = 'hidden'
        finish_survey_button.style.visibility = 'hidden'
        sync_companycam_button.style.visibility = 'hidden'
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
                self.app.photo_box,
                self.app.survey_title_label,
                self.app.progress_widget,
                self.app.question_widget,
                submit_answer_button,
                next_question_button,
                finish_survey_button,
                self.sync_companycam_button,
                sync_button,
                self.app.status_label
            ],
            style=toga.Pack(direction=toga.COLUMN, padding=10)
        )

        self.app.main_window.content = main_box

    def show_survey_ui(self):
        """Show the enhanced survey interface"""
        self.app.survey_title_label.style.visibility = 'visible'
        self.app.progress_widget.set_visible(True)
        self.app.question_widget.set_visible(True)
        self.app.survey_title_label.text = self.app.current_survey['title']

    def show_question(self):
        """Show the current question in enhanced UI with Phase 2 features"""
        # Update progress
        self.update_progress()

        # Find the next visible field
        visible_field = self.app.survey_handler.get_next_visible_field()

        if not visible_field:
            self.app.survey_handler.finish_survey(None)
            return

        section = visible_field.get('section') or 'General'
        self.app.current_section = section
        self.update_section_tag_controls(section)

        # Update question widget
        self.app.question_widget.update_question(
            visible_field['question'],
            required=visible_field.get('required', False)
        )

        # Handle different field types using composite widget
        field_type = visible_field.get('field_type', 'text')
        if field_type == 'yesno':
            self.app.question_widget.show_yesno_buttons(
                on_yes=lambda w: self.app.survey_handler.submit_yesno_answer('Yes'),
                on_no=lambda w: self.app.survey_handler.submit_yesno_answer('No')
            )
        elif field_type == 'photo':
            self.app.question_widget.show_photo_button(
                on_press=self.app.survey_handler.take_photo_enhanced
            )
            # Show photo requirements if available
            if visible_field.get('photo_requirements'):
                self.show_photo_requirements(visible_field['photo_requirements'])
        elif visible_field.get('options'):
            # Multiple choice
            self.app.question_widget.show_selection(items=visible_field['options'])
        else:
            # Text input
            self.app.question_widget.show_text_input(
                placeholder=visible_field.get('description', 'Enter your answer'),
                value='',
                on_change=self.app.survey_handler.on_answer_input_change
            )

    def show_photo_requirements(self, photo_requirements):
        """Show photo requirements for current photo field"""
        # This would show a small popup or label with photo requirements
        # For now, just update status
        req_text = photo_requirements.get('description', 'Photo required')
        self.app.status_label.text = f"Photo requirement: {req_text}"

    def update_section_tag_controls(self, section):
        """Rebuild section-scoped tag toggles"""
        section_name = section or 'General'
        self.app.section_tag_label.text = f"{section_name} Tags"
        self.app.clear_photo_tag_selection()
        while self.app.section_tag_switches_box.children:
            child = self.app.section_tag_switches_box.children[0]
            self.app.section_tag_switches_box.remove(child)
        self.app.section_tag_switches.clear()

        tags = self.app.section_tags.get(section_name, []) if isinstance(self.app.section_tags, dict) else []
        if not tags:
            info_label = toga.Label(
                "No tags defined for this section.",
                style=toga.Pack(font_size=10, color='#666666', padding=(0, 5, 5, 5))
            )
            self.app.section_tag_switches_box.add(info_label)
            return

        for tag in tags:
            switch = toga.Switch(
                label=tag,
                value=False,
                on_toggle=lambda widget, tag=tag: self.app.toggle_photo_tag(tag, widget.is_on),
                style=toga.Pack(padding=(0, 5, 5, 5))
            )
            self.app.section_tag_switches_box.add(switch)
            self.app.section_tag_switches[tag] = switch

    def update_progress(self):
        """Update progress indicator with enhanced Phase 2 tracking"""
        if self.app.current_survey:
            # Get detailed progress from database
            progress_data = self.app.db.get_survey_progress(self.app.current_survey['id'])
            self.app.section_progress = progress_data.get('sections', {})
            overall_progress = progress_data.get('overall_progress', 0)

            # Update progress label with detailed information
            total_required = progress_data.get('total_required', 0)
            total_completed = progress_data.get('total_completed', 0)
            self.app.progress_label.text = f"Progress: {total_completed}/{total_required} ({overall_progress:.1f}%)"
        elif self.app.total_fields > 0:
            progress = (self.app.current_question_index / self.app.total_fields) * 100
            self.app.progress_label.text = f"Progress: {self.app.current_question_index}/{self.app.total_fields} ({progress:.1f}%)"
        else:
            self.app.progress_label.text = "Progress: 0/0 (0%)"