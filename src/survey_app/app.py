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
    def __init__(self):
        super().__init__(formal_name='Site Survey App', app_id='com.keith.surveyapp')
    def startup(self):
        """Initialize the app"""
        self.db = LocalDatabase()
        self.current_survey = None
        self.current_site = None
        self.responses = []
        self.config = {}  # App configuration
        self.last_sync_version = 0
        self.template_fields = []
        self.total_fields = 0
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

        # Initialize location service
        self.location = toga.Location()

    async def get_gps_location(self):
        try:
            location_info = await self.location.current_location()
            return location_info.latitude, location_info.longitude
        except Exception as e:
            self.status_label.text = f"GPS error: {e}"
            return None, None

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
                if self.current_site:
                    self.load_surveys_for_site(self.current_site.id)
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
            items=['Select a site first...'],
            style=Pack(padding=(5, 10, 10, 10))
        )

        select_survey_button = toga.Button(
            'Start Survey',
            on_press=self.start_survey,
            style=Pack(padding=(5, 10, 10, 10))
        )

        sites_button = toga.Button(
            'Sites',
            on_press=self.show_sites_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        templates_button = toga.Button(
            'Templates',
            on_press=self.show_templates_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Enhanced survey form (initially hidden)
        self.survey_title_label = toga.Label(
            '',
            style=Pack(font_size=18, padding=(20, 10, 10, 10), font_weight='bold')
        )

        # Progress indicator
        self.progress_label = toga.Label(
            '',
            style=Pack(padding=(5, 10, 5, 10), color='#666666')
        )

        # Field type specific UI elements
        self.yes_button = toga.Button(
            'Yes',
            on_press=lambda w: self.submit_yesno_answer('Yes'),
            style=Pack(padding=(5, 10, 5, 5))
        )
        self.no_button = toga.Button(
            'No',
            on_press=lambda w: self.submit_yesno_answer('No'),
            style=Pack(padding=(5, 10, 10, 5))
        )

        self.options_selection = toga.Selection(
            items=[],
            style=Pack(padding=(5, 10, 10, 10))
        )

        self.enhanced_photo_button = toga.Button(
            '📷 Take Photo',
            on_press=self.take_photo_enhanced,
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
            style=Pack(padding=(5, 10, 10, 10))
        )

        sync_button = toga.Button(
            'Sync Now',
            on_press=self.sync_with_server,
            style=Pack(padding=(5, 10, 10, 10))
        )

        config_button = toga.Button(
            'Settings',
            on_press=self.show_config_ui,
            style=Pack(padding=(5, 10, 10, 10))
        )

        # Question UI (legacy)
        self.question_box = toga.Box(style=Pack(direction=COLUMN, padding=10, visibility='hidden'))
        self.question_label_legacy = toga.Label("Question", style=Pack(padding=(5, 10, 5, 10)))
        self.answer_input_legacy = toga.TextInput(style=Pack(padding=(5, 10, 10, 10)))
        self.answer_selection = toga.Selection(style=Pack(padding=(5, 10, 10, 10)))

        next_question_button_legacy = toga.Button('Next', on_press=self.next_question, style=Pack(padding=(5, 10, 10, 10)))

        self.progress_bar = toga.ProgressBar(max=100, value=0, style=Pack(padding=(10, 10, 10, 10)))
        self.question_box.add(self.question_label_legacy, self.answer_input_legacy, self.answer_selection, next_question_button_legacy, self.progress_bar)

        # Enhanced question UI elements (separate from legacy)
        self.question_label = toga.Label(
            '',
            style=Pack(padding=(10, 10, 5, 10))
        )

        self.answer_input = toga.TextInput(
            placeholder='Enter your answer',
            style=Pack(padding=(5, 10, 10, 10))
        )


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

        # Initially hide enhanced survey form
        self.survey_title_label.style.visibility = 'hidden'
        self.progress_label.style.visibility = 'hidden'
        self.question_label.style.visibility = 'hidden'
        self.answer_input.style.visibility = 'hidden'
        self.yes_button.style.visibility = 'hidden'
        self.no_button.style.visibility = 'hidden'
        self.options_selection.style.visibility = 'hidden'
        self.enhanced_photo_button.style.visibility = 'hidden'
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
                select_survey_button,
                sites_button,
                templates_button,
                config_button,
                self.question_box,
                self.photo_box,
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
                sync_button,
                self.status_label
            ],
            style=Pack(direction=COLUMN, padding=10)
        )

        self.main_window.content = main_box

    def start_survey(self, widget):
        """Start the selected survey"""
        if self.survey_selection.value:
            survey_id_str = self.survey_selection.value.split(':')[0]
            try:
                survey_id = int(survey_id_str)
                # Try to fetch from server first
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
                    # Try local cache if server unavailable
                    survey_data = self.db.get_survey(survey_id)
                    if survey_data:
                        self.current_survey = survey_data
                    else:
                        self.status_label.text = "Survey not found and server unavailable"
                        return

                # Reset responses
                self.responses = []

                # Load template fields if survey has a template_id
                if survey_data.get('template_id'):
                    try:
                        template_response = requests.get(f'http://localhost:5000/api/templates/{survey_data["template_id"]}', timeout=5)
                        if template_response.status_code == 200:
                            template_data = template_response.json()
                            self.template_fields = template_data['fields']
                            self.total_fields = len(self.template_fields)
                        else:
                            self.template_fields = []
                            self.total_fields = 0
                    except:
                        self.template_fields = []
                        self.total_fields = 0
                elif hasattr(self, 'default_template_fields'):
                    self.template_fields = self.default_template_fields
                    self.total_fields = len(self.template_fields)
                else:
                    self.template_fields = []
                    self.total_fields = 0

                # Use enhanced UI if template fields are available, otherwise use legacy
                if self.template_fields:
                    # Show enhanced survey form
                    self.show_survey_ui()
                    self.current_question_index = 0
                    self.show_question()
                else:
                    # Use legacy UI
                    self.question_box.style.visibility = 'visible'
                    self.photo_box.style.visibility = 'visible'
                    self.load_questions()
                    self.display_question()
            except ValueError:
                self.status_label.text = "Invalid survey ID"
        else:
            self.status_label.text = "Please select a survey"
        self.update_progress()

    def load_questions(self):
        """Load questions for legacy UI"""
        if self.current_survey and self.current_survey.get('template_id'):
            self.questions = self.db.get_template_fields(self.current_survey['template_id'])
        else:
            self.questions = []

    def display_question(self):
        """Display question in legacy UI"""
        if self.current_question_index < len(self.questions):
            question = self.questions[self.current_question_index]
            self.question_label_legacy.text = question['question']
            if question['field_type'] == 'text':
                self.answer_input_legacy.style.visibility = 'visible'
                self.answer_selection.style.visibility = 'hidden'
            elif question['field_type'] == 'multiple_choice':
                self.answer_input_legacy.style.visibility = 'hidden'
                self.answer_selection.style.visibility = 'visible'
                self.answer_selection.items = json.loads(question['options'])
        else:
            self.question_box.style.visibility = 'hidden'
            self.status_label.text = "Survey complete!"
        self.update_progress()

    def update_progress(self):
        """Update progress indicator"""
        if hasattr(self, 'questions') and self.questions:
            progress = (self.current_question_index / len(self.questions)) * 100
            self.progress_bar.value = progress
        elif self.total_fields > 0:
            progress = (self.current_question_index / self.total_fields) * 100
            self.progress_bar.value = progress
        else:
            self.progress_bar.value = 0

    def show_survey_ui(self):
        """Show the enhanced survey interface"""
        self.survey_title_label.style.visibility = 'visible'
        self.progress_label.style.visibility = 'visible'
        self.question_label.style.visibility = 'visible'
        self.survey_title_label.text = self.current_survey['title']

    def show_question(self):
        """Show the current question in enhanced UI"""
        # Update progress
        if self.total_fields > 0:
            progress = f"Question {self.current_question_index + 1} of {self.total_fields}"
            self.progress_label.text = progress
        else:
            self.progress_label.text = ""

        # Hide all input elements first
        self.answer_input.style.visibility = 'hidden'
        self.yes_button.style.visibility = 'hidden'
        self.no_button.style.visibility = 'hidden'
        self.options_selection.style.visibility = 'hidden'
        self.enhanced_photo_button.style.visibility = 'hidden'

        if self.current_question_index < len(self.current_survey.get('responses', [])):
            # Show existing response
            response = self.current_survey['responses'][self.current_question_index]
            self.question_label.text = response['question']
            self.answer_input.value = response.get('answer', '')
            self.answer_input.style.visibility = 'visible'
        else:
            # Check if survey has template fields
            if self.template_fields and self.current_question_index < len(self.template_fields):
                field = self.template_fields[self.current_question_index]
                self.question_label.text = field['question']

                # Handle different field types
                field_type = field.get('field_type', 'text')
                if field_type == 'yesno':
                    self.yes_button.style.visibility = 'visible'
                    self.no_button.style.visibility = 'visible'
                elif field_type == 'photo':
                    self.enhanced_photo_button.style.visibility = 'visible'
                elif field.get('options'):
                    # Multiple choice
                    self.options_selection.items = field['options']
                    self.options_selection.style.visibility = 'visible'
                else:
                    # Text input
                    self.answer_input.placeholder = field.get('description', 'Enter your answer')
                    self.answer_input.value = ''
                    self.answer_input.style.visibility = 'visible'
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
                    self.answer_input.placeholder = 'Enter your answer'
                    self.answer_input.value = ''
                    self.answer_input.style.visibility = 'visible'
                else:
                    self.finish_survey(None)
                    return

    def submit_answer(self, widget):
        """Submit the current answer in enhanced UI"""
        answer = self.answer_input.value.strip()
        # Check if this is a multiple choice question with options selected
        if not answer and self.options_selection.value:
            answer = self.options_selection.value
            response_type = 'multiple_choice'
        elif answer:
            response_type = 'text'
        else:
            self.status_label.text = "Please provide an answer"
            return

        question = self.question_label.text
        response = {
            'question': question,
            'answer': answer,
            'response_type': response_type
        }
        self.responses.append(response)

        # Save response immediately to database
        if self.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.current_survey['id'],
                'question': question,
                'answer': answer,
                'response_type': response_type
            }
            self.db.save_response(response_data)

        self.status_label.text = f"Answer submitted for: {question[:50]}..."
        self.next_question(None)

    def next_question(self, widget):
        """Move to next question - works for both legacy and enhanced UI"""
        # Save current response if using legacy UI
        if hasattr(self, 'questions') and self.questions and self.current_question_index < len(self.questions):
            self.save_response()
        self.current_question_index += 1
        
        # Use appropriate display method
        if hasattr(self, 'questions') and self.questions:
            self.display_question()
        else:
            self.show_question()

    def save_response(self):
        """Save response for legacy UI"""
        if hasattr(self, 'questions') and self.current_question_index < len(self.questions):
            question = self.questions[self.current_question_index]
            answer = ''
            if question['field_type'] == 'text':
                answer = self.answer_input_legacy.value
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

    def submit_yesno_answer(self, answer):
        """Submit yes/no answer in enhanced UI"""
        question = self.question_label.text
        response = {
            'question': question,
            'answer': answer,
            'response_type': 'yesno'
        }
        self.responses.append(response)

        # Save response immediately to database
        if self.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.current_survey['id'],
                'question': question,
                'answer': answer,
                'response_type': 'yesno'
            }
            self.db.save_response(response_data)

        self.status_label.text = f"Answer submitted: {answer}"
        self.current_question_index += 1
        self.show_question()

    def take_photo_enhanced(self, widget):
        """Take a photo in enhanced UI"""
        # Create dummy photo data (same as take_photo)
        img = Image.new('RGB', (640, 480), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=75)
        photo_data = img_byte_arr.getvalue()

        # Get GPS location
        async def capture_with_location():
            lat, long = await self.get_gps_location()
            if self.current_survey:
                # Save photo to database
                photo_record = {
                    'id': str(uuid.uuid4()),
                    'survey_id': self.current_survey['id'],
                    'image_data': photo_data,
                    'latitude': lat,
                    'longitude': long,
                    'description': f"Photo for: {self.question_label.text}"
                }
                self.db.save_photo(photo_record)

                # Save response
                question = self.question_label.text
                response = {
                    'question': question,
                    'answer': f'[Photo captured - ID: {photo_record["id"]}]',
                    'response_type': 'photo'
                }
                self.responses.append(response)

                # Save response to database immediately
                response_data = {
                    'id': str(uuid.uuid4()),
                    'survey_id': self.current_survey['id'],
                    'question': question,
                    'answer': response['answer'],
                    'response_type': 'photo'
                }
                self.db.save_response(response_data)

                self.status_label.text = f"Photo captured for: {question[:50]}..."
                self.current_question_index += 1
                self.show_question()

        asyncio.create_task(capture_with_location())

    def finish_survey(self, widget):
        """Finish the survey and save responses"""
        if self.current_survey:
            # Save responses locally
            if hasattr(self.db, 'save_responses'):
                self.db.save_responses(self.current_survey['id'], self.responses)
            else:
                # Fallback: save each response individually
                for response in self.responses:
                    response_data = {
                        'id': str(uuid.uuid4()),
                        'survey_id': self.current_survey['id'],
                        'question': response['question'],
                        'answer': response['answer'],
                        'response_type': response.get('response_type', 'text')
                    }
                    self.db.save_response(response_data)

            # Hide enhanced survey form
            self.survey_title_label.style.visibility = 'hidden'
            self.progress_label.style.visibility = 'hidden'
            self.question_label.style.visibility = 'hidden'
            self.answer_input.style.visibility = 'hidden'
            self.yes_button.style.visibility = 'hidden'
            self.no_button.style.visibility = 'hidden'
            self.options_selection.style.visibility = 'hidden'
            self.enhanced_photo_button.style.visibility = 'hidden'
            
            # Hide legacy UI as well
            self.question_box.style.visibility = 'hidden'
            self.photo_box.style.visibility = 'hidden'
            
            self.status_label.text = "Survey completed and saved!"

    def show_sites_ui(self, widget):
        """Show sites management UI"""
        sites_window = toga.Window(title="Sites")

        sites_label = toga.Label('Available Sites:', style=Pack(padding=(10, 5, 10, 5)))
        self.sites_list = toga.Selection(items=['Loading...'], style=Pack(padding=(5, 5, 10, 5)))

        load_sites_button = toga.Button('Load Sites', on_press=self.load_sites, style=Pack(padding=(5, 5, 5, 5)))
        select_site_button = toga.Button('Select Site', on_press=lambda w: self.select_site(sites_window), style=Pack(padding=(5, 5, 10, 5)))

        new_site_label = toga.Label('Create New Site:', style=Pack(padding=(10, 5, 10, 5)))
        self.new_site_name_input = toga.TextInput(placeholder='Site Name', style=Pack(padding=(5, 5, 10, 5)))
        self.new_site_address_input = toga.TextInput(placeholder='Site Address', style=Pack(padding=(5, 5, 10, 5)))
        create_site_button = toga.Button('Create Site', on_press=self.create_site, style=Pack(padding=(5, 5, 10, 5)))

        close_button = toga.Button('Close', on_press=lambda w: sites_window.close(), style=Pack(padding=(5, 5, 10, 5)))

        sites_box = toga.Box(
            children=[
                sites_label,
                self.sites_list,
                load_sites_button,
                select_site_button,
                new_site_label,
                self.new_site_name_input,
                self.new_site_address_input,
                create_site_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )

        sites_window.content = sites_box
        sites_window.show()
        self.load_sites(None)

    def load_sites(self, widget):
        """Load sites from local db"""
        sites = self.db.get_sites()
        if sites:
            site_names = [f"{s.id}: {s.name}" for s in sites]
            self.sites_list.items = site_names
            self.sites_data = sites
            self.status_label.text = f"Loaded {len(sites)} sites"
        else:
            self.sites_list.items = ['No sites available']

    def create_site(self, widget):
        """Create a new site"""
        site_name = self.new_site_name_input.value
        site_address = self.new_site_address_input.value
        if site_name:
            site_data = {'name': site_name, 'address': site_address}
            self.db.save_site(site_data)
            self.status_label.text = f"Created site: {site_name}"
            self.load_sites(None)
        else:
            self.status_label.text = "Please enter a site name"

    def select_site(self, sites_window):
        if self.sites_list.value and hasattr(self, 'sites_data'):
            site_id = int(self.sites_list.value.split(':')[0])
            self.current_site = next((s for s in self.sites_data if s.id == site_id), None)
            if self.current_site:
                self.load_surveys_for_site(self.current_site.id)
                sites_window.close()
            else:
                self.status_label.text = "Site not found"
        else:
            self.status_label.text = "Please select a site"

    def load_surveys_for_site(self, site_id):
        """Load surveys for the selected site"""
        surveys = self.db.get_surveys_for_site(site_id)
        if surveys:
            survey_names = [f"{s.id}: {s.title}" for s in surveys]
            self.survey_selection.items = survey_names
            self.status_label.text = f"Loaded {len(surveys)} surveys for site {self.current_site.name}"
        else:
            self.survey_selection.items = []
            self.status_label.text = f"No surveys available for site {self.current_site.name}"

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
                if not self.current_site:
                    self.status_label.text = "Please select a site first"
                    return

                survey_data = {
                    'title': f"{template['name']} - New Survey",
                    'description': template['description'],
                    'site_id': self.current_site.id,
                    'status': 'draft',
                    'template_id': template_id
                }

                # In a real app, this would be a CRDT insert
                self.db.save_survey(survey_data)
                self.status_label.text = f"Created survey from template"
                # Refresh surveys list
                if self.current_site:
                    self.load_surveys_for_site(self.current_site.id)

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
        img.save(img_byte_arr, format='JPEG', quality=75)
        self.current_photo_data = img_byte_arr.getvalue()
        self.image_view.image = toga.Image(data=self.current_photo_data)

        # Get GPS location
        async def update_location():
            lat, long = await self.get_gps_location()
            if lat is not None and long is not None:
                self.photo_location_input.value = f"{lat}, {long}"

        asyncio.create_task(update_location())

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
    return SurveyApp()
