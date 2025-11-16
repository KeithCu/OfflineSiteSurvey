try:
    import toga
    from toga.style import Pack
    from toga.style.pack import COLUMN, ROW
except (ImportError, RuntimeError):
    from . import toga_mock as toga
    from .toga_mock import Pack, COLUMN, ROW
from .local_db import LocalDatabase
import requests
import json
import asyncio
import threading
import time
from PIL import Image
import io
import base64
import uuid

class SurveyApp(toga.App):
    def startup(self):
        """Initialize the app"""
        self.db = LocalDatabase()
        self.current_survey = None
        self.responses = []
        self.config = {}  # App configuration
        self.last_sync_version = 0
        self.current_question_index = 0

        # Create main window
        self.main_window = toga.MainWindow(title=self.formal_name)

        # Create UI components
        self.create_main_ui()

        # Show the main window
        self.main_window.show()

        # Start the background sync thread
        self.sync_thread = threading.Thread(target=self.background_sync, daemon=True)
        self.sync_thread.start()

    def background_sync(self):
        while True:
            self.sync_with_server()
            time.sleep(10) # Sync every 10 seconds

    def sync_with_server(self, widget=None):
        """Sync local data with server"""
        try:
            # Get local changes
            local_changes = self.db.get_changes_since(self.last_sync_version)

            # Send local changes to the server
            if local_changes:
                response = requests.post(
                    'http://localhost:5000/api/changes',
                    json=local_changes,
                    timeout=10
                )
                if response.status_code != 200:
                    self.status_label.text = "Sync failed - server error"
                    return

            # Get remote changes from the server
            response = requests.get(
                f'http://localhost:5000/api/changes?version={self.last_sync_version}&site_id={self.db.site_id}',
                timeout=10
            )

            if response.status_code == 200:
                remote_changes = response.json()
                if remote_changes:
                    self.db.apply_changes(remote_changes)
                self.last_sync_version = self.db.get_current_version()
                self.status_label.text = "Sync complete"
                self.load_surveys() # Refresh the survey list
            else:
                self.status_label.text = "Sync failed - server error"

        except requests.exceptions.RequestException:
            self.status_label.text = "Sync failed - server not available"
        except Exception as e:
            self.status_label.text = f"Sync error: {str(e)}"

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

        templates_button = toga.Button(
            'Templates',
            on_press=self.show_templates_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        config_button = toga.Button(
            'Settings',
            on_press=self.show_config_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Question UI
        self.question_box = toga.Box(style=Pack(direction=COLUMN, padding=10, visibility='hidden'))
        self.question_label = toga.Label("Question", style=Pack(padding=(5, 10, 5, 10)))
        self.answer_input = toga.TextInput(style=Pack(padding=(5, 10, 10, 10)))
        self.answer_selection = toga.Selection(style=Pack(padding=(5, 10, 10, 10)))

        next_question_button = toga.Button('Next', on_press=self.next_question, style=Pack(padding=(5, 10, 10, 10)))

        self.question_box.add(self.question_label, self.answer_input, self.answer_selection, next_question_button)


        # Photo capture UI
        self.photo_box = toga.Box(style=Pack(direction=COLUMN, padding=10, visibility='hidden'))

        take_photo_button = toga.Button(
            'Take Photo',
            on_press=self.take_photo,
            style=Pack(padding=(5, 10, 10, 10))
        )

        self.image_view = toga.ImageView(style=Pack(height=200))

        self.photo_description_input = toga.TextInput(
            placeholder='Photo description',
            style=Pack(padding=(5, 10, 10, 10))
        )
        self.photo_location_input = toga.TextInput(
            placeholder='Photo location (lat, long)',
            style=Pack(padding=(5, 10, 10, 10))
        )
        save_photo_button = toga.Button(
            'Save Photo',
            on_press=self.save_photo,
            style=Pack(padding=(5, 10, 10, 10))
        )

        self.photo_box.add(
            take_photo_button,
            self.image_view,
            self.photo_description_input,
            self.photo_location_input,
            save_photo_button
        )

        # Status label
        self.status_label = toga.Label(
            'Ready',
            style=Pack(padding=(10, 10, 10, 10), color='#666666')
        )

        # Create main box
        main_box = toga.Box(
            children=[
                header_label,
                survey_label,
                self.survey_selection,
                load_surveys_button,
                select_survey_button,
                templates_button,
                config_button,
                self.question_box,
                self.photo_box,
                self.status_label
            ],
            style=Pack(direction=COLUMN, padding=10)
        )

        self.main_window.content = main_box

    def load_surveys(self, widget=None):
        """Load surveys from local db"""
        surveys = self.db.get_surveys()
        if surveys:
            survey_names = [f"{s['id']}: {s['title']}" for s in surveys]
            self.survey_selection.items = survey_names
            self.status_label.text = f"Loaded {len(surveys)} surveys from local storage"
        else:
            self.status_label.text = "No surveys available"

    def start_survey(self, widget):
        """Start the selected survey"""
        if self.survey_selection.value:
            survey_id_str = self.survey_selection.value.split(':')[0]
            try:
                survey_id = int(survey_id_str)
                self.current_survey = self.db.get_survey(survey_id)
                self.question_box.style.visibility = 'visible'
                self.photo_box.style.visibility = 'visible'
                self.load_questions()
                self.display_question()
            except ValueError:
                self.status_label.text = "Invalid survey ID"
        else:
            self.status_label.text = "Please select a survey"

    def load_questions(self):
        if self.current_survey and self.current_survey.get('template_id'):
            self.questions = self.db.get_template_fields(self.current_survey['template_id'])
        else:
            self.questions = []

    def display_question(self):
        if self.current_question_index < len(self.questions):
            question = self.questions[self.current_question_index]
            self.question_label.text = question['question']
            if question['field_type'] == 'text':
                self.answer_input.style.visibility = 'visible'
                self.answer_selection.style.visibility = 'hidden'
            elif question['field_type'] == 'multiple_choice':
                self.answer_input.style.visibility = 'hidden'
                self.answer_selection.style.visibility = 'visible'
                self.answer_selection.items = json.loads(question['options'])
        else:
            self.question_box.style.visibility = 'hidden'
            self.status_label.text = "Survey complete!"

    def next_question(self, widget):
        self.save_response()
        self.current_question_index += 1
        self.display_question()

    def save_response(self):
        question = self.questions[self.current_question_index]
        answer = ''
        if question['field_type'] == 'text':
            answer = self.answer_input.value
        elif question['field_type'] == 'multiple_choice':
            answer = self.answer_selection.value

        response_data = {
            'id': str(uuid.uuid4()),
            'survey_id': self.current_survey['id'],
            'question': question['question'],
            'answer': answer,
            'response_type': question['field_type']
        }
        self.db.save_response(response_data)
        self.status_label.text = f"Saved response for: {question['question']}"

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
        """Load templates from local db"""
        templates = self.db.get_templates()
        if templates:
            template_names = [f"{t['id']}: {t['name']} ({t['category']})" for t in templates]
            self.templates_list.items = template_names
            self.templates_data = templates  # Store for later use
            self.status_label.text = f"Loaded {len(templates)} templates"
        else:
            self.templates_list.items = ['Failed to load templates']

    def create_survey_from_template(self, widget):
        """Create a new survey from selected template"""
        if self.templates_list.value and hasattr(self, 'templates_data'):
            template_id = int(self.templates_list.value.split(':')[0])

            # Find template data
            template = next((t for t in self.templates_data if t['id'] == template_id), None)
            if template:
                survey_data = {
                    'title': f"{template['name']} - New Survey",
                    'description': template['description'],
                    'store_name': 'New Store',
                    'store_address': 'Address TBD',
                    'status': 'draft',
                    'template_id': template_id
                }

                # In a real app, this would be a CRDT insert
                self.db.save_survey(survey_data)
                self.status_label.text = f"Created survey from template"
                # Refresh surveys list
                self.load_surveys(None)

            else:
                self.status_label.text = "Template not found"
        else:
            self.status_label.text = "Please select a template first"

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
        # In a real app, this would be a CRDT insert
        pass

    def take_photo(self, widget):
        # In a real app, this would open the camera.
        # For now, we'll create a dummy image.
        img = Image.new('RGB', (640, 480), color = 'red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        self.current_photo_data = img_byte_arr.getvalue()
        self.image_view.image = toga.Image(data=self.current_photo_data)

    def save_photo(self, widget):
        if self.current_survey and hasattr(self, 'current_photo_data'):
            latitude, longitude = None, None
            try:
                lat_str, lon_str = self.photo_location_input.value.split(',')
                latitude = float(lat_str.strip())
                longitude = float(lon_str.strip())
            except (ValueError, IndexError):
                pass # Ignore if location is not a valid lat,long pair

            photo_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.current_survey['id'],
                'image_data': self.current_photo_data,
                'latitude': latitude,
                'longitude': longitude,
                'description': self.photo_description_input.value
            }
            self.db.save_photo(photo_data)
            self.status_label.text = "Photo saved locally"
        else:
            self.status_label.text = "Please select a survey and take a photo first"


def main():
    return SurveyApp('Site Survey App', 'com.example.survey_app')
