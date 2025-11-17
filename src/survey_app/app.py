"""Site Survey App - Main application."""
try:
    import toga
    from toga.style import Pack
    from toga.style.pack import COLUMN, ROW
except (ImportError, RuntimeError):
    from . import toga_mock as toga
    from .toga_mock import Pack, COLUMN, ROW

from .local_db import LocalDatabase
from .enums import ProjectStatus, PriorityLevel, PhotoCategory
from .handlers.project_handler import ProjectHandler
from .handlers.site_handler import SiteHandler
from .handlers.survey_handler import SurveyHandler
from .handlers.photo_handler import PhotoHandler
from .handlers.template_handler import TemplateHandler
from .handlers.sync_handler import SyncHandler
from .ui.survey_ui import SurveyUI
from .services.api_service import APIService
from .services.db_service import DBService
from .logging_config import setup_logging
import asyncio
import logging
import uuid
import time
import threading
import json
import io
from PIL import Image, ExifTags


class SurveyApp(toga.App):
    """Main SurveyApp class."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__(formal_name='Site Survey App', app_id='com.keith.surveyapp')

    def startup(self):
        """Initialize the app"""
        # Setup logging first
        setup_logging()

        # Initialize services
        self.db = LocalDatabase()
        self.db_service = DBService(self.db)
        self.api_service = APIService()

        # Initialize state
        self.current_project = None
        self.current_survey = None
        self.current_site = None
        self.responses = []
        self.config = {}  # App configuration
        self.last_sync_version = 0
        self.template_fields = []
        self.total_fields = 0
        self.current_question_index = 0
        self.visible_fields = []  # Track which fields are visible based on conditions
        self.section_progress = {}  # Track progress by section
        self.photo_requirements = {}  # Track photo requirements by section
        self.current_responses = []  # Track responses for conditional logic
        self.offline_queue = []  # Queue for operations when offline
        self.auto_save_timer = None
        self.draft_responses = {}  # Temporary storage for in-progress answers

        # Initialize handlers
        self.project_handler = ProjectHandler(self)
        self.site_handler = SiteHandler(self)
        self.survey_handler = SurveyHandler(self)
        self.photo_handler = PhotoHandler(self)
        self.template_handler = TemplateHandler(self)
        self.sync_handler = SyncHandler(self)

        # Initialize UI
        self.ui = SurveyUI(self)

        # Create main window
        self.main_window = toga.MainWindow(title=self.formal_name)

        # Create UI components
        self.ui.create_main_ui()

        # Show the main window
        self.main_window.show()

        # Start the background sync scheduler
        self.sync_handler.start_sync_scheduler()

        # Initialize location service
        self.location = toga.Location()

    async def get_gps_location(self):
        """Get current GPS location."""
        try:
            location_info = await self.location.current_location()
            return location_info.latitude, location_info.longitude
        except Exception as e:
            self.status_label.text = f"GPS error: {e}"
            return None, None

    def schedule_auto_save(self, question_id, answer_text):
        """Debounced auto-save for in-progress answers"""
        # Cancel existing timer
        if self.auto_save_timer:
            self.auto_save_timer.cancel()

        # Store draft
        self.draft_responses[question_id] = {
            'answer': answer_text,
            'timestamp': time.time()
        }

        # Schedule save after 2 seconds of inactivity
        self.auto_save_timer = threading.Timer(2.0, self.perform_auto_save, args=[question_id])
        self.auto_save_timer.start()

    def perform_auto_save(self, question_id):
        """Actually save the draft response to database"""
        if question_id in self.draft_responses:
            draft = self.draft_responses[question_id]

            # Only save if it's been more than 30 seconds since last real save
            # (avoid excessive saves during normal typing)
            if time.time() - draft['timestamp'] > 30:
                try:
                    draft_data = {
                        'id': str(uuid.uuid4()),
                        'survey_id': self.current_survey['id'] if self.current_survey else None,
                        'question_id': question_id,
                        'question': f"Draft for question {question_id}",
                        'answer': draft['answer'],
                        'response_type': 'draft',
                        'field_type': 'text'
                    }
                    self.db.save_response(draft_data)
                    self.logger.info(f"Auto-saved draft for question {question_id}")
                except Exception as e:
                    self.logger.warning(f"Auto-save failed: {e}")

            # Clean up old drafts (keep only recent ones)
            current_time = time.time()
            self.draft_responses = {
                qid: draft for qid, draft in self.draft_responses.items()
                if current_time - draft['timestamp'] < 300  # Keep for 5 minutes
            }

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

        projects_button = toga.Button(
            'Projects',
            on_press=self.show_projects_ui,
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

        photos_button = toga.Button(
            'Photos',
            on_press=self.show_photos_ui,
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

        # Wire up auto-save to text input changes
        self.answer_input.on_change = self.on_answer_input_change

    def on_answer_input_change(self, widget):
        """Handle text input changes with debounced auto-save"""
        if self.current_survey and self.template_fields and self.current_question_index < len(self.template_fields):
            current_field = self.template_fields[self.current_question_index]
            question_id = current_field['id']
            answer_text = widget.value

            # Schedule auto-save with debounce
            self.schedule_auto_save(question_id, answer_text)

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
                projects_button,
                sites_button,
                templates_button,
                photos_button,
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
                    response = self.api_service.get(f'/api/surveys/{survey_id}', timeout=5)
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
                except Exception as e:
                    # Try local cache if server unavailable
                    self.logger.warning(f"Server request failed, trying local cache: {e}")
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
                        # Use new conditional fields API
                        template_response = self.api_service.get(f'/api/templates/{survey_data["template_id"]}/conditional-fields', timeout=5)
                        if template_response.status_code == 200:
                            template_data = template_response.json()
                            self.template_fields = template_data['fields']
                            self.total_fields = len(self.template_fields)
                        else:
                            self.template_fields = []
                            self.total_fields = 0
                    except Exception as e:
                        self.logger.warning(f"Failed to load template fields: {e}")
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
        """Update progress indicator with enhanced Phase 2 tracking"""
        if self.current_survey:
            # Get detailed progress from database
            progress_data = self.db.get_survey_progress(self.current_survey['id'])
            self.section_progress = progress_data.get('sections', {})
            overall_progress = progress_data.get('overall_progress', 0)
            
            # Update progress bar
            self.progress_bar.value = overall_progress
            
            # Update progress label with detailed information
            total_required = progress_data.get('total_required', 0)
            total_completed = progress_data.get('total_completed', 0)
            self.progress_label.text = f"Progress: {total_completed}/{total_required} ({overall_progress:.1f}%)"
        else:
            # Fallback to basic progress calculation
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
        """Show the current question in enhanced UI with Phase 2 features"""
        # Update progress
        self.update_progress()

        # Hide all input elements first
        self.answer_input.style.visibility = 'hidden'
        self.yes_button.style.visibility = 'hidden'
        self.no_button.style.visibility = 'hidden'
        self.options_selection.style.visibility = 'hidden'
        self.enhanced_photo_button.style.visibility = 'hidden'

        # Find the next visible field
        visible_field = self.get_next_visible_field()
        
        if not visible_field:
            self.finish_survey(None)
            return
        
        # Update question label with required indicator
        required_indicator = " * " if visible_field.get('required', False) else " "
        self.question_label.text = f"{required_indicator}{visible_field['question']}"

        # Handle different field types
        field_type = visible_field.get('field_type', 'text')
        if field_type == 'yesno':
            self.yes_button.style.visibility = 'visible'
            self.no_button.style.visibility = 'visible'
        elif field_type == 'photo':
            self.enhanced_photo_button.style.visibility = 'visible'
            # Show photo requirements if available
            if visible_field.get('photo_requirements'):
                self.show_photo_requirements(visible_field['photo_requirements'])
        elif visible_field.get('options'):
            # Multiple choice
            self.options_selection.items = visible_field['options']
            self.options_selection.style.visibility = 'visible'
        else:
            # Text input
            self.answer_input.placeholder = visible_field.get('description', 'Enter your answer')
            self.answer_input.value = ''
            self.answer_input.style.visibility = 'visible'
    
    def get_next_visible_field(self):
        """Get the next visible field based on conditional logic"""
        if not self.template_fields:
            return None
        
        # Evaluate conditions for each field
        for i in range(self.current_question_index, len(self.template_fields)):
            field = self.template_fields[i]
            
            # Check if field has conditions
            if field.get('conditions'):
                if self.db.should_show_field(field['conditions'], self.current_responses):
                    return field
            else:
                # No conditions, always show
                return field
        
        return None
    
    def show_photo_requirements(self, photo_requirements):
        """Show photo requirements for current photo field"""
        # This would show a small popup or label with photo requirements
        # For now, just update status
        req_text = photo_requirements.get('description', 'Photo required')
        self.status_label.text = f"Photo requirement: {req_text}"

    def submit_answer(self, widget):
        """Submit the current answer in enhanced UI with Phase 2 tracking"""
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

        # Get current field for tracking
        current_field = self.get_next_visible_field()
        if not current_field:
            return
        
        question = current_field['question']
        response = {
            'question_id': current_field['id'],
            'question': question,
            'answer': answer,
            'response_type': response_type
        }
        self.responses.append(response)
        self.current_responses.append(response)

        # Save response immediately to database
        if self.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.current_survey['id'],
                'question_id': current_field['id'],
                'question': question,
                'answer': answer,
                'response_type': response_type,
                'field_type': current_field.get('field_type', 'text')
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
        """Submit yes/no answer in enhanced UI with Phase 2 tracking"""
        # Get current field for tracking
        current_field = self.get_next_visible_field()
        if not current_field:
            return
        
        question = current_field['question']
        response = {
            'question_id': current_field['id'],
            'question': question,
            'answer': answer,
            'response_type': 'yesno'
        }
        self.responses.append(response)
        self.current_responses.append(response)

        # Save response immediately to database
        if self.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.current_survey['id'],
                'question_id': current_field['id'],
                'question': question,
                'answer': answer,
                'response_type': 'yesno',
                'field_type': 'yesno'
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
        
        # Store photo ID for requirement tracking
        self.last_photo_id = str(uuid.uuid4())

        # Extract EXIF data
        exif_dict = {}
        if hasattr(img, '_getexif') and img._getexif():
            exif_dict = {ExifTags.TAGS.get(tag, tag): value for tag, value in img._getexif().items()}
        exif_json = json.dumps(exif_dict)

        # Get GPS location
        async def capture_with_location():
            lat, long = await self.get_gps_location()
            if self.current_survey:
                # Save photo to database (hash and size computed automatically in save_photo)
                photo_record = {
                    'id': self.last_photo_id,
                    'survey_id': self.current_survey['id'],
                    'image_data': photo_data,
                    'latitude': lat,
                    'longitude': long,
                    'description': f"Photo for: {self.question_label.text}",
                    'category': PhotoCategory.GENERAL.value,
                    'exif_data': exif_json
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

    def show_projects_ui(self, widget):
        """Show projects management UI"""
        projects_window = toga.Window(title="Projects")

        projects_label = toga.Label('Available Projects:', style=Pack(padding=(10, 5, 10, 5)))
        self.projects_list = toga.Selection(items=['Loading...'], style=Pack(padding=(5, 5, 10, 5)))

        # Project status and metadata inputs
        self.project_status_selection = toga.Selection(
            items=[s.value for s in ProjectStatus],
            style=Pack(padding=(5, 5, 10, 5))
        )
        self.project_client_info_input = toga.TextInput(
            placeholder='Client information',
            style=Pack(padding=(5, 5, 10, 5))
        )
        self.project_due_date_input = toga.TextInput(
            placeholder='Due date (YYYY-MM-DD)',
            style=Pack(padding=(5, 5, 10, 5))
        )
        self.project_priority_selection = toga.Selection(
            items=[p.value for p in PriorityLevel],
            style=Pack(padding=(5, 5, 10, 5))
        )

        load_projects_button = toga.Button('Load Projects', on_press=self.load_projects, style=Pack(padding=(5, 5, 5, 5)))
        select_project_button = toga.Button('Select Project', on_press=lambda w: self.select_project(projects_window), style=Pack(padding=(5, 5, 10, 5)))

        new_project_label = toga.Label('Create New Project:', style=Pack(padding=(10, 5, 10, 5)))
        self.new_project_name_input = toga.TextInput(placeholder='Project Name', style=Pack(padding=(5, 5, 10, 5)))
        self.new_project_description_input = toga.TextInput(placeholder='Project Description', style=Pack(padding=(5, 5, 10, 5)))

        # Project metadata fields
        project_status_label = toga.Label('Status:', style=Pack(padding=(5, 5, 5, 5)))
        project_client_label = toga.Label('Client Info:', style=Pack(padding=(5, 5, 5, 5)))
        project_due_date_label = toga.Label('Due Date:', style=Pack(padding=(5, 5, 5, 5)))
        project_priority_label = toga.Label('Priority:', style=Pack(padding=(5, 5, 5, 5)))

        create_project_button = toga.Button('Create Project', on_press=self.create_project, style=Pack(padding=(5, 5, 10, 5)))

        close_button = toga.Button('Close', on_press=lambda w: projects_window.close(), style=Pack(padding=(5, 5, 10, 5)))

        projects_box = toga.Box(
            children=[
                projects_label,
                self.projects_list,
                load_projects_button,
                select_project_button,
                new_project_label,
                self.new_project_name_input,
                self.new_project_description_input,
                project_status_label,
                self.project_status_selection,
                project_client_label,
                self.project_client_info_input,
                project_due_date_label,
                self.project_due_date_input,
                project_priority_label,
                self.project_priority_selection,
                create_project_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )

        projects_window.content = projects_box
        projects_window.show()
        self.load_projects(None)

    def load_projects(self, widget):
        """Load projects from local db"""
        projects = self.db.get_projects()
        if projects:
            project_names = [f"{p.id}: {p.name}" for p in projects]
            self.projects_list.items = project_names
            self.projects_data = projects
            self.status_label.text = f"Loaded {len(projects)} projects"
        else:
            self.projects_list.items = ['No projects available']

    def create_project(self, widget):
        """Create a new project"""
        project_name = self.new_project_name_input.value
        project_description = self.new_project_description_input.value
        if project_name:
            project_data = {
                'name': project_name,
                'description': project_description,
                'status': self.project_status_selection.value or ProjectStatus.DRAFT.value,
                'client_info': self.project_client_info_input.value,
                'due_date': self.project_due_date_input.value,
                'priority': self.project_priority_selection.value or PriorityLevel.MEDIUM.value
            }
            self.db.save_project(project_data)
            self.status_label.text = f"Created project: {project_name}"
            self.load_projects(None)
        else:
            self.status_label.text = "Please enter a project name"

    def select_project(self, projects_window):
        if self.projects_list.value and hasattr(self, 'projects_data'):
            project_id = int(self.projects_list.value.split(':')[0])
            self.current_project = next((p for p in self.projects_data if p.id == project_id), None)
            if self.current_project:
                self.load_sites_for_project(self.current_project.id)
                projects_window.close()
            else:
                self.status_label.text = "Project not found"
        else:
            self.status_label.text = "Please select a project"

    def load_sites_for_project(self, project_id):
        """Load sites for the selected project"""
        sites = self.db.get_sites_for_project(project_id)
        if sites:
            site_names = [f"{s.id}: {s.name}" for s in sites]
            self.survey_selection.items = ['Select a site first...'] + site_names
            self.status_label.text = f"Loaded {len(sites)} sites for project {self.current_project.name}"
        else:
            self.survey_selection.items = ['Select a site first...']
            self.status_label.text = f"No sites available for project {self.current_project.name}"

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
        self.new_site_notes_input = toga.TextInput(placeholder='Site Notes', style=Pack(padding=(5, 5, 10, 5)))
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
                self.new_site_notes_input,
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
            site_data = {
                'name': site_name,
                'address': site_address,
                'notes': self.new_site_notes_input.value
            }
            if self.current_project:
                site_data['project_id'] = self.current_project.id
            self.db.save_site(site_data)
            self.status_label.text = f"Created site: {site_name}"
            self.load_sites(None)
            if self.current_project:
                self.load_sites_for_project(self.current_project.id)
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



def main():
    return SurveyApp()
