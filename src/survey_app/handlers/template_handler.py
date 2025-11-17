"""Template management handlers for SurveyApp."""
import json
import toga


class TemplateHandler:
    """Handles template-related operations."""

    def __init__(self, app):
        self.app = app

    def show_templates_ui(self, widget):
        """Show templates management UI"""
        # Create templates window
        templates_window = toga.Window(title="Survey Templates")

        # Template list
        templates_label = toga.Label('Available Templates:', style=toga.Pack(padding=(10, 5, 10, 5)))
        self.app.templates_list = toga.Selection(items=['Loading...'], style=toga.Pack(padding=(5, 5, 10, 5)))

        # Buttons
        load_templates_button = toga.Button(
            'Load Templates',
            on_press=self.load_templates,
            style=toga.Pack(padding=(5, 5, 5, 5))
        )

        create_survey_button = toga.Button(
            'Create Survey from Template',
            on_press=self.create_survey_from_template,
            style=toga.Pack(padding=(5, 5, 10, 5))
        )
        edit_tags_button = toga.Button(
            'Edit Section Tags',
            on_press=self.open_section_tags_editor,
            style=toga.Pack(padding=(5, 5, 5, 5))
        )

        close_button = toga.Button(
            'Close',
            on_press=lambda w: templates_window.close(),
            style=toga.Pack(padding=(5, 5, 10, 5))
        )

        # Create templates box
        templates_box = toga.Box(
            children=[
                templates_label,
                self.app.templates_list,
                load_templates_button,
                create_survey_button,
                edit_tags_button,
                close_button
            ],
            style=toga.Pack(direction=toga.COLUMN, padding=20)
        )

        templates_window.content = templates_box
        templates_window.show()

        # Auto-load templates
        self.load_templates(None)

    def load_templates(self, widget):
        """Load templates from local db"""
        templates = self.app.db.get_templates()
        if templates:
            template_names = [f"{t['id']}: {t['name']} ({t['category']})" for t in templates]
            self.app.templates_list.items = template_names
            self.app.templates_data = templates  # Store for later use
            self.app.status_label.text = f"Loaded {len(templates)} templates"
        else:
            self.app.templates_list.items = ['Failed to load templates']

    def create_survey_from_template(self, widget):
        """Create a new survey from selected template"""
        if self.app.templates_list.value and hasattr(self.app, 'templates_data'):
            template_id = int(self.app.templates_list.value.split(':')[0])

            # Find template data
            template = next((t for t in self.app.templates_data if t['id'] == template_id), None)
            if template:
                if not self.app.current_site:
                    self.app.status_label.text = "Please select a site first"
                    return

                survey_data = {
                    'title': f"{template['name']} - New Survey",
                    'description': template['description'],
                    'site_id': self.app.current_site.id,
                    'status': 'draft',
                    'template_id': template_id
                }

                # In a real app, this would be a CRDT insert
                self.app.db.save_survey(survey_data)
                self.app.status_label.text = f"Created survey from template"
                # Refresh surveys list
                if self.app.current_site:
                    self.app.survey_handler.load_surveys_for_site(self.app.current_site.id)

            else:
                self.app.status_label.text = "Template not found"
        else:
            self.app.status_label.text = "Please select a template first"

    def open_section_tags_editor(self, widget):
        if not self.app.templates_list.value or not hasattr(self.app, 'templates_data'):
            self.app.status_label.text = "Please select a template first"
            return

        template_id = int(self.app.templates_list.value.split(':')[0])
        template = next((t for t in self.app.templates_data if t.id == template_id), None)
        if not template:
            self.app.status_label.text = "Template not found"
            return

        sections = sorted({field.section or 'General' for field in template.fields})
        if not sections:
            sections = ['General']

        try:
            existing_tags = json.loads(template.section_tags) if template.section_tags else {}
        except json.JSONDecodeError:
            existing_tags = {}

        self.section_tag_inputs = {}
        editor_window = toga.Window(title="Section Tags")
        editor_box = toga.Box(style=toga.Pack(direction=toga.COLUMN, padding=10))

        for section in sections:
            section_label = toga.Label(section, style=toga.Pack(font_weight='bold', padding=(5, 0, 0, 0)))
            editor_box.add(section_label)

            tag_input = toga.TextInput(
                value=", ".join(existing_tags.get(section, [])),
                style=toga.Pack(padding=(0, 5, 5, 5))
            )
            self.section_tag_inputs[section] = tag_input
            editor_box.add(tag_input)

        save_button = toga.Button(
            'Save Section Tags',
            on_press=lambda w: self.save_section_tags(template_id, editor_window),
            style=toga.Pack(padding=(5, 5, 5, 5))
        )
        close_button = toga.Button(
            'Cancel',
            on_press=lambda w: editor_window.close(),
            style=toga.Pack(padding=(5, 5, 5, 5))
        )
        editor_box.add(save_button, close_button)

        editor_window.content = editor_box
        editor_window.show()

    def save_section_tags(self, template_id, window):
        if not hasattr(self, 'section_tag_inputs'):
            self.app.status_label.text = "No metadata to save"
            return

        section_tags = {}
        for section, widget in self.section_tag_inputs.items():
            raw_value = widget.value or ''
            tags = [tag.strip() for tag in raw_value.split(',') if tag.strip()]
            section_tags[section] = tags

        try:
            response = self.app.api_service.put(
                f'/templates/{template_id}/section-tags',
                json={'section_tags': section_tags},
                timeout=5
            )
            if response.status_code == 200:
                self.app.db.update_template_section_tags(template_id, section_tags)
                self.load_templates(None)
                self.app.status_label.text = "Section tags saved"
                window.close()
            else:
                self.app.status_label.text = f"Failed to save tags ({response.status_code})"
        except Exception as e:
            self.app.status_label.text = f"Failed to save tags: {e}"