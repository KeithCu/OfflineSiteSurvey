"""Template management handlers for SurveyApp."""
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