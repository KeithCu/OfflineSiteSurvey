import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .local_db import LocalDatabase
import requests
import json
import asyncio
import threading
import time
from PIL import Image
import io
import base64

class SurveyApp(toga.App):
    def startup(self):
        """Initialize the app"""
        self.db = LocalDatabase()
        self.current_survey = None
        self.responses = []
        self.config = {}  # App configuration

        # Create main window
        self.main_window = toga.MainWindow(title=self.formal_name)

        # Load configuration
        self.load_configuration()

        # Create UI components
        self.create_main_ui()

        # Show the main window
        self.main_window.show()

    def load_configuration(self):
        """Load configuration from server"""
        try:
            response = requests.get('http://localhost:5000/api/config', timeout=5)
            if response.status_code == 200:
                self.config = response.json()
                self.status_label.text = "Configuration loaded from server"
            else:
                # Fall back to defaults
                self.config = {
                    'image_compression_quality': 75,
                    'auto_sync_interval': 300,
                    'max_offline_days': 30
                }
                self.status_label.text = "Using default configuration"
        except:
            # Use defaults if server unavailable
            self.config = {
                'image_compression_quality': 75,
                'auto_sync_interval': 300,
                'max_offline_days': 30
            }
            self.status_label.text = "Server unavailable, using defaults"

    def compress_image(self, image_data):
        """Compress image using configured quality"""
        quality = self.config.get('image_compression_quality', 75)
        return self.db.compress_image(image_data, quality)

    def create_main_ui(self):
        """Create the main user interface"""
        # Header
        header_label = toga.Label(
            'Site Survey App',
            style=Pack(font_size=24, padding=(10, 10, 20, 10))
        )

        # Survey selection
        survey_label = toga.Label(
            'Select Survey:',
            style=Pack(padding=(5, 10, 5, 10))
        )

        self.survey_selection = toga.Selection(
            items=['Loading surveys...'],
            style=Pack(padding=(5, 10, 10, 10))
        )

        load_surveys_button = toga.Button(
            'Load Surveys',
            on_press=self.load_surveys,
            style=Pack(padding=(5, 10, 10, 10))
        )

        select_survey_button = toga.Button(
            'Start Survey',
            on_press=self.start_survey,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Survey form (initially hidden)
        self.survey_title_label = toga.Label(
            '',
            style=Pack(font_size=18, padding=(20, 10, 10, 10), font_weight='bold')
        )

        self.question_label = toga.Label(
            '',
            style=Pack(padding=(10, 10, 5, 10))
        )

        self.answer_input = toga.TextInput(
            placeholder='Enter your answer',
            style=Pack(padding=(5, 10, 10, 10))
        )

        submit_answer_button = toga.Button(
            'Submit Answer',
            on_press=self.submit_answer,
            style=Pack(padding=(5, 10, 10, 10))
        )

        next_question_button = toga.Button(
            'Next Question',
            on_press=self.next_question,
            style=Pack(padding=(5, 10, 10, 10))
        )

        finish_survey_button = toga.Button(
            'Finish Survey',
            on_press=self.finish_survey,
            style=Pack(padding=(5, 10, 20, 10))
        )

        sync_button = toga.Button(
            'Sync with Server',
            on_press=self.sync_with_server,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Configuration button
        config_button = toga.Button(
            '⚙️ Settings',
            on_press=self.show_config_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Templates button
        templates_button = toga.Button(
            '📋 Templates',
            on_press=self.show_templates_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Status label
        self.status_label = toga.Label(
            'Ready',
            style=Pack(padding=(10, 10, 10, 10), color='#666666')
        )

        # Initially hide survey form
        self.survey_title_label.style.visibility = 'hidden'
        self.question_label.style.visibility = 'hidden'
        self.answer_input.style.visibility = 'hidden'
        submit_answer_button.style.visibility = 'hidden'
        next_question_button.style.visibility = 'hidden'
        finish_survey_button.style.visibility = 'hidden'
        sync_button.style.visibility = 'hidden'

        # Create main box
        main_box = toga.Box(
            children=[
                header_label,
                survey_label,
                self.survey_selection,
                load_surveys_button,
                select_survey_button,
                config_button,
                templates_button,
                self.survey_title_label,
                self.question_label,
                self.answer_input,
                submit_answer_button,
                next_question_button,
                finish_survey_button,
                sync_button,
                self.status_label
            ],
            style=Pack(direction=COLUMN, padding=10)
        )

        self.main_window.content = main_box

    def load_surveys(self, widget):
        """Load surveys from server"""
        try:
            # Try to load from server first
            response = requests.get('http://localhost:5000/api/surveys', timeout=5)
            if response.status_code == 200:
                surveys = response.json()

                # Load default template if available
                try:
                    template_response = requests.get('http://localhost:5000/api/templates', timeout=5)
                    if template_response.status_code == 200:
                        templates = template_response.json()
                        default_template = next((t for t in templates if t['is_default']), None)
                        if default_template:
                            # Load template details
                            template_detail = requests.get(f'http://localhost:5000/api/templates/{default_template["id"]}', timeout=5)
                            if template_detail.status_code == 200:
                                template_data = template_detail.json()
                                # Store template fields for later use
                                self.default_template_fields = template_data['fields']
                except:
                    pass  # Template loading is optional

                survey_names = [f"{s['id']}: {s['title']}" for s in surveys]
                self.survey_selection.items = survey_names
                self.status_label.text = f"Loaded {len(surveys)} surveys from server"
            else:
                raise Exception("Server not available")
        except:
            # Fall back to local surveys
            local_surveys = self.db.get_surveys()
            if local_surveys:
                survey_names = [f"{s['id']}: {s['title']}" for s in local_surveys]
                self.survey_selection.items = survey_names
                self.status_label.text = f"Loaded {len(local_surveys)} surveys from local storage"
            else:
                self.status_label.text = "No surveys available"

    def start_survey(self, widget):
        """Start the selected survey"""
        if self.survey_selection.value:
            survey_id = int(self.survey_selection.value.split(':')[0])

            # Load survey data
            try:
                response = requests.get(f'http://localhost:5000/api/surveys/{survey_id}', timeout=5)
                if response.status_code == 200:
                    survey_data = response.json()
                    self.current_survey = survey_data
                    self.db.save_survey(survey_data)  # Cache locally
                else:
                    # Try local cache
                    survey_data = self.db.get_survey(survey_id)
                    if survey_data:
                        self.current_survey = survey_data
                    else:
                        self.status_label.text = "Survey not found"
                        return
            except:
                # Try local cache
                survey_data = self.db.get_survey(survey_id)
                if survey_data:
                    self.current_survey = survey_data
                else:
                    self.status_label.text = "Survey not found and server unavailable"
                    return

            # Reset responses
            self.responses = []

            # Load template fields if available
            if hasattr(self, 'default_template_fields'):
                self.current_survey.template_fields = self.default_template_fields

            # Show survey form
            self.show_survey_ui()

            # Start with first question
            self.current_question_index = 0
            self.show_question()
        else:
            # Try to create from template
            self.create_basic_survey()

    def show_survey_ui(self):
        """Show the survey interface"""
        self.survey_title_label.style.visibility = 'visible'
        self.question_label.style.visibility = 'visible'
        self.answer_input.style.visibility = 'visible'
        self.survey_title_label.text = self.current_survey['title']

    def show_question(self):
        """Show the current question"""
        if self.current_question_index < len(self.current_survey.get('responses', [])):
            # Show existing response
            response = self.current_survey['responses'][self.current_question_index]
            self.question_label.text = response['question']
            self.answer_input.value = response.get('answer', '')
        else:
            # Check if survey has template fields
            if hasattr(self.current_survey, 'template_fields') and self.current_survey.template_fields:
                fields = self.current_survey.template_fields
                if self.current_question_index < len(fields):
                    field = fields[self.current_question_index]
                    self.question_label.text = field['question']
                    self.answer_input.value = ''
                    # Handle different field types
                    if field.get('field_type') == 'yesno':
                        self.answer_input.placeholder = 'Yes/No'
                    elif field.get('field_type') == 'photo':
                        self.answer_input.placeholder = 'Photo will be captured'
                    else:
                        self.answer_input.placeholder = 'Enter your answer'
                else:
                    self.finish_survey(None)
                    return
            else:
                # Fallback to basic questions
                questions = [
                    "What is the store's overall condition?",
                    "Are there any maintenance issues?",
                    "How is the store lighting?",
                    "Describe the store layout",
                    "Any additional notes?"
                ]

                if self.current_question_index < len(questions):
                    self.question_label.text = questions[self.current_question_index]
                    self.answer_input.value = ''
                else:
                    self.finish_survey(None)
                    return

    def submit_answer(self, widget):
        """Submit the current answer"""
        answer = self.answer_input.value.strip()
        if answer:
            question = self.question_label.text
            response = {
                'question': question,
                'answer': answer,
                'response_type': 'text'
            }
            self.responses.append(response)
            self.status_label.text = f"Answer submitted for: {question[:50]}..."

    def next_question(self, widget):
        """Move to next question"""
        self.current_question_index += 1
        self.show_question()

    def finish_survey(self, widget):
        """Finish the survey and save responses"""
        if self.current_survey:
            # Save responses locally
            self.db.save_responses(self.current_survey['id'], self.responses)

            # Hide survey form
            self.survey_title_label.style.visibility = 'hidden'
            self.question_label.style.visibility = 'hidden'
            self.answer_input.style.visibility = 'hidden'

            self.status_label.text = f"Survey completed! {len(self.responses)} responses saved locally."

            # Show sync button
            # Note: In a real app, you'd want to show this button earlier
            # self.sync_button.style.visibility = 'visible'

    def sync_with_server(self, widget):
        """Sync local data with server"""
        try:
            # Get all local responses that haven't been synced
            unsynced_responses = self.db.get_unsynced_responses()

            for survey_id, responses in unsynced_responses.items():
                if responses:
                    data = {'responses': responses}
                    response = requests.post(
                        f'http://localhost:5000/api/surveys/{survey_id}/sync',
                        json=data,
                        timeout=10
                    )

                    if response.status_code == 200:
                        # Mark as synced
                        self.db.mark_synced(survey_id)
                        self.status_label.text = f"Synced {len(responses)} responses for survey {survey_id}"
                    else:
                        self.status_label.text = "Sync failed - server error"
                        return

            self.status_label.text = "All data synced successfully!"

        except requests.exceptions.RequestException:
            self.status_label.text = "Sync failed - server not available"
        except Exception as e:
            self.status_label.text = f"Sync error: {str(e)}"

    def show_config_ui(self, widget):
        """Show configuration settings UI"""
        # Create config window
        config_window = toga.Window(title="Settings")

        # Config labels and inputs
        quality_label = toga.Label('Image Compression Quality (1-100):', style=Pack(padding=(10, 5, 5, 5)))
        self.quality_input = toga.TextInput(
            value=str(self.config.get('image_compression_quality', 75)),
            style=Pack(padding=(5, 5, 10, 5))
        )

        sync_label = toga.Label('Auto-sync Interval (seconds, 0=disabled):', style=Pack(padding=(10, 5, 5, 5)))
        self.sync_input = toga.TextInput(
            value=str(self.config.get('auto_sync_interval', 300)),
            style=Pack(padding=(5, 5, 10, 5))
        )

        offline_label = toga.Label('Max Offline Days:', style=Pack(padding=(10, 5, 5, 5)))
        self.offline_input = toga.TextInput(
            value=str(self.config.get('max_offline_days', 30)),
            style=Pack(padding=(5, 5, 10, 5))
        )

        # Save button
        save_button = toga.Button(
            'Save Settings',
            on_press=self.save_config,
            style=Pack(padding=(10, 5, 10, 5))
        )

        close_button = toga.Button(
            'Close',
            on_press=lambda w: config_window.close(),
            style=Pack(padding=(5, 5, 10, 5))
        )

        # Create config box
        config_box = toga.Box(
            children=[
                quality_label,
                self.quality_input,
                sync_label,
                self.sync_input,
                offline_label,
                self.offline_input,
                save_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )

        config_window.content = config_box
        config_window.show()

    def save_config(self, widget):
        """Save configuration settings"""
        try:
            # Update local config
            self.config['image_compression_quality'] = int(self.quality_input.value)
            self.config['auto_sync_interval'] = int(self.sync_input.value)
            self.config['max_offline_days'] = int(self.offline_input.value)

            # Try to save to server
            for key, value in self.config.items():
                try:
                    response = requests.put(
                        f'http://localhost:5000/api/config/{key}',
                        json={'value': value},
                        timeout=5
                    )
                    if response.status_code == 200:
                        self.status_label.text = f"Saved {key} to server"
                    else:
                        self.status_label.text = f"Failed to save {key} to server"
                except:
                    self.status_label.text = f"Server unavailable, {key} saved locally only"

        except ValueError:
            self.status_label.text = "Invalid configuration values"

    def show_templates_ui(self, widget):
        """Show templates management UI"""
        # Create templates window
        templates_window = toga.Window(title="Survey Templates")

        # Template list
        templates_label = toga.Label('Available Templates:', style=Pack(padding=(10, 5, 10, 5)))
        self.templates_list = toga.Selection(items=['Loading...'], style=Pack(padding=(5, 5, 10, 5)))

        # Buttons
        load_templates_button = toga.Button(
            'Load Templates',
            on_press=self.load_templates,
            style=Pack(padding=(5, 5, 5, 5))
        )

        create_survey_button = toga.Button(
            'Create Survey from Template',
            on_press=self.create_survey_from_template,
            style=Pack(padding=(5, 5, 10, 5))
        )

        close_button = toga.Button(
            'Close',
            on_press=lambda w: templates_window.close(),
            style=Pack(padding=(5, 5, 10, 5))
        )

        # Create templates box
        templates_box = toga.Box(
            children=[
                templates_label,
                self.templates_list,
                load_templates_button,
                create_survey_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )

        templates_window.content = templates_box
        templates_window.show()

        # Auto-load templates
        self.load_templates(None)

    def load_templates(self, widget):
        """Load templates from server"""
        try:
            response = requests.get('http://localhost:5000/api/templates', timeout=5)
            if response.status_code == 200:
                templates = response.json()
                template_names = [f"{t['id']}: {t['name']} ({t['category']})" for t in templates]
                self.templates_list.items = template_names
                self.templates_data = templates  # Store for later use
                self.status_label.text = f"Loaded {len(templates)} templates"
            else:
                self.templates_list.items = ['Failed to load templates']
        except:
            self.templates_list.items = ['Server unavailable']

    def create_survey_from_template(self, widget):
        """Create a new survey from selected template"""
        if self.templates_list.value and hasattr(self, 'templates_data'):
            template_id = int(self.templates_list.value.split(':')[0])

            # Find template data
            template = next((t for t in self.templates_data if t['id'] == template_id), None)
            if template:
                try:
                    response = requests.get(f'http://localhost:5000/api/templates/{template_id}', timeout=5)
                    if response.status_code == 200:
                        template_data = response.json()
                        # Create survey from template
                        survey_data = {
                            'title': f"{template_data['name']} - New Survey",
                            'description': template_data['description'],
                            'store_name': 'New Store',
                            'store_address': 'Address TBD',
                            'status': 'draft'
                        }

                        create_response = requests.post(
                            'http://localhost:5000/api/surveys',
                            json=survey_data,
                            timeout=5
                        )

                        if create_response.status_code == 201:
                            survey_id = create_response.json()['id']
                            self.status_label.text = f"Created survey {survey_id} from template"
                            # Refresh surveys list
                            self.load_surveys(None)
                        else:
                            self.status_label.text = "Failed to create survey"
                    else:
                        self.status_label.text = "Failed to load template details"
                except:
                    self.status_label.text = "Server unavailable for survey creation"
            else:
                self.status_label.text = "Template not found"
        else:
            self.status_label.text = "Please select a template first"

    def create_basic_survey(self):
        """Create a basic survey if no template is available"""
        # Create a simple survey
        survey_data = {
            'title': 'Basic Store Survey',
            'description': 'A simple store survey',
            'store_name': 'Unknown Store',
            'store_address': 'Unknown Address',
            'status': 'draft'
        }

        try:
            response = requests.post(
                'http://localhost:5000/api/surveys',
                json=survey_data,
                timeout=5
            )

            if response.status_code == 201:
                survey_id = response.json()['id']
                self.status_label.text = f"Created basic survey {survey_id}"
                # Refresh surveys list
                self.load_surveys(None)
            else:
                self.status_label.text = "Failed to create survey"
        except:
            self.status_label.text = "Server unavailable for survey creation"

def main():
    return SurveyApp('Site Survey App', 'com.example.survey_app')
