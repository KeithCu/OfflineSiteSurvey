"""Survey management handlers for SurveyApp."""
import json
import toga
import uuid
import time
import threading
from PIL import Image, ExifTags
import io
import base64


class SurveyHandler:
    """Handles survey-related operations."""

    def __init__(self, app):
        self.app = app
    
    def schedule_auto_save(self, question_id, answer_text):
        """Debounced auto-save for in-progress answers"""
        state = self.app.state
        # Cancel existing timer
        if state.auto_save_timer:
            state.auto_save_timer.cancel()

        # Store draft
        state.draft_responses[question_id] = {
            'answer': answer_text,
            'timestamp': time.time()
        }

        # Schedule save after configured delay
        state.auto_save_timer = threading.Timer(
            self.app.config.auto_save_delay,
            self.perform_auto_save,
            args=[question_id]
        )
        state.auto_save_timer.start()

    def perform_auto_save(self, question_id):
        """Actually save the draft response to database"""
        state = self.app.state
        if question_id in state.draft_responses:
            draft = state.draft_responses[question_id]

            # Only save if it's been more than configured interval since last real save
            # (avoid excessive saves during normal typing)
            if time.time() - draft['timestamp'] > self.app.config.auto_save_min_interval:
                try:
                    draft_data = {
                        'id': str(uuid.uuid4()),
                        'survey_id': state.current_survey['id'] if state.current_survey else None,
                        'question_id': question_id,
                        'question': f"Draft for question {question_id}",
                        'answer': draft['answer'],
                        'response_type': 'draft',
                        'field_type': 'text'
                    }
                    self.app.db.save_response(draft_data)
                    self.app.logger.info(f"Auto-saved draft for question {question_id}")
                except Exception as e:
                    self.app.logger.warning(f"Auto-save failed: {e}")

            # Clean up old drafts (keep only recent ones)
            current_time = time.time()
            state.draft_responses = {
                qid: draft for qid, draft in state.draft_responses.items()
                if current_time - draft['timestamp'] < self.app.config.draft_retention_time
            }
    
    def load_survey_from_selection(self):
        """Load survey from UI selection dropdown"""
        if self.app.ui_manager.survey_selection.value:
            survey_id_str = self.app.ui_manager.survey_selection.value.split(':')[0]
            try:
                survey_id = int(survey_id_str)
                # Try to fetch from server first
                try:
                    response = self.app.api_service.get(f'/api/surveys/{survey_id}', timeout=self.app.config.api_timeout)
                    if response.status_code == 200:
                        survey_data = response.json()
                        self.app.state.current_survey = survey_data
                        self.app.db.save_survey(survey_data)  # Cache locally
                    else:
                        # Try local cache
                        survey_data = self.app.db.get_survey(survey_id)
                        if survey_data:
                            self.app.state.current_survey = survey_data
                        else:
                            self.app.ui_manager.status_label.text = "Survey not found"
                            return
                except Exception as e:
                    # Try local cache if server unavailable
                    self.app.logger.warning(f"Server request failed, trying local cache: {e}")
                    survey_data = self.app.db.get_survey(survey_id)
                    if survey_data:
                        self.app.state.current_survey = survey_data
                    else:
                        self.app.ui_manager.status_label.text = "Survey not found and server unavailable"
                        return

                # Reset responses and lookup
                self.app.state.reset_survey_state()

                # Load template fields if survey has a template_id
                if survey_data.get('template_id'):
                    try:
                        # Use new conditional fields API
                        template_response = self.app.api_service.get(f'/api/templates/{survey_data["template_id"]}/conditional-fields', timeout=self.app.config.api_timeout)
                        if template_response.status_code == 200:
                            template_data = template_response.json()
                            self.app.state.template_fields = template_data['fields']
                            self.app.state.total_fields = len(self.app.state.template_fields)
                        else:
                            self.app.state.template_fields = []
                            self.app.state.total_fields = 0
                    except Exception as e:
                        self.app.logger.warning(f"Failed to load template fields: {e}")
                        self.app.state.template_fields = []
                        self.app.state.total_fields = 0
                elif hasattr(self.app, 'default_template_fields'):
                    self.app.state.template_fields = self.app.default_template_fields
                    self.app.state.total_fields = len(self.app.state.template_fields)
                else:
                    self.app.state.template_fields = []
                    self.app.state.total_fields = 0

                # Show enhanced survey form
                if self.app.state.template_fields:
                    self.app.ui_manager.show_enhanced_survey_ui()
                    self.app.state.current_question_index = 0
                    self.show_question()
                else:
                    self.app.ui_manager.status_label.text = "No template fields available for this survey"
            except ValueError:
                self.app.ui_manager.status_label.text = "Invalid survey ID"
        else:
            self.app.ui_manager.status_label.text = "Please select a survey"
        self.update_progress()
    
    def show_question(self):
        """Show the current question in enhanced UI with Phase 2 features"""
        # Update progress
        self.update_progress()
        state = self.app.state

        # Hide all input elements first
        self.app.ui_manager.answer_input.style.visibility = 'hidden'
        self.app.ui_manager.yes_button.style.visibility = 'hidden'
        self.app.ui_manager.no_button.style.visibility = 'hidden'
        self.app.ui_manager.options_selection.style.visibility = 'hidden'
        self.app.ui_manager.enhanced_photo_button.style.visibility = 'hidden'

        # Find the next visible field
        visible_field = self.get_next_visible_field()

        if not visible_field:
            self.finish_survey(None)
            return

        # Update question label with required indicator
        required_indicator = " * " if visible_field.get('required', False) else " "
        self.app.ui_manager.question_label.text = f"{required_indicator}{visible_field['question']}"

        # Handle different field types using ui_manager
        field_type = visible_field.get('field_type', 'text')
        options = visible_field.get('options')
        description = visible_field.get('description', 'Enter your answer')

        self.app.ui_manager.show_question_ui(field_type, options, description)

        # Show photo requirements if available
        if field_type == 'photo' and visible_field.get('photo_requirements'):
            self.show_photo_requirements(visible_field['photo_requirements'])
    
    def show_photo_requirements(self, photo_requirements):
        """Show photo requirements for current photo field"""
        # This would show a small popup or label with photo requirements
        # For now, just update status
        req_text = photo_requirements.get('description', 'Photo required')
        self.app.ui_manager.status_label.text = f"Photo requirement: {req_text}"
    
    def update_progress(self):
        """Update progress indicator with enhanced Phase 2 tracking"""
        state = self.app.state
        if state.current_survey:
            # Get detailed progress from database
            progress_data = self.app.db.get_survey_progress(state.current_survey['id'])
            state.section_progress = progress_data.get('sections', {})
            overall_progress = progress_data.get('overall_progress', 0)
            
            # Update progress label with detailed information
            total_required = progress_data.get('total_required', 0)
            total_completed = progress_data.get('total_completed', 0)
            self.app.ui_manager.progress_label.text = f"Progress: {total_completed}/{total_required} ({overall_progress:.1f}%)"
        elif state.total_fields > 0:
            progress = (state.current_question_index / state.total_fields) * 100
            self.app.ui_manager.progress_label.text = f"Progress: {state.current_question_index}/{state.total_fields} ({progress:.1f}%)"
        else:
            self.app.ui_manager.progress_label.text = "Progress: 0/0 (0%)"

    def start_survey(self, widget):
        """Start the selected survey"""
        if self.app.ui_manager.survey_selection.value:
            survey_id_str = self.app.ui_manager.survey_selection.value.split(':')[0]
            try:
                survey_id = int(survey_id_str)
                # Try to fetch from server first
                try:
                    response = self.app.api_service.get(f'/surveys/{survey_id}', timeout=5)
                    if response.status_code == 200:
                        survey_data = response.json()
                        self.app.state.current_survey = survey_data
                        self.app.db.save_survey(survey_data)  # Cache locally
                    else:
                        # Try local cache
                        survey_data = self.app.db.get_survey(survey_id)
                        if survey_data:
                            self.app.state.current_survey = survey_data
                        else:
                            self.app.ui_manager.status_label.text = "Survey not found"
                            return
                except Exception as e:
                    # Try local cache if server unavailable
                    self.app.logger.warning(f"Server request failed, trying local cache: {e}")
                    survey_data = self.app.db.get_survey(survey_id)
                    if survey_data:
                        self.app.state.current_survey = survey_data
                    else:
                        self.app.ui_manager.status_label.text = "Survey not found and server unavailable"
                        return

                # Reset responses and load existing ones from database
                self.app.state.reset_survey_state()
                
                # Load existing responses from database and pre-compute lookup
                from shared.utils import build_response_lookup
                existing_responses = self.app.db.get_responses_for_survey(survey_id)
                if existing_responses:
                    # Convert database responses to the format expected by conditional logic
                    for resp in existing_responses:
                        response_dict = {
                            'question_id': resp.question_id,
                            'answer': resp.answer,
                            'question': resp.question,
                            'response_type': resp.response_type
                        }
                        self.app.state.current_responses.append(response_dict)
                        self.app.state.responses.append(response_dict)
                
                # Pre-compute response lookup dictionary once for fast conditional evaluation
                self.app.state.response_lookup = build_response_lookup(self.app.state.current_responses)

                # Load template fields if survey has a template_id
                if survey_data.get('template_id'):
                    try:
                        template_response = self.app.api_service.get(
                            f'/api/templates/{survey_data["template_id"]}/conditional-fields',
                            timeout=self.app.config.api_timeout
                        )
                        if template_response.status_code == 200:
                            template_data = template_response.json()
                        else:
                            template_data = self.app.db.get_conditional_fields(survey_data["template_id"])
                    except Exception as e:
                        self.app.logger.warning(f"Failed to load template fields: {e}")
                        template_data = self.app.db.get_conditional_fields(survey_data["template_id"])

                    if not template_data:
                        template_data = {'fields': [], 'section_tags': {}}

                    self.app.state.template_fields = template_data.get('fields', [])
                    section_tags = template_data.get('section_tags', {})
                    if isinstance(section_tags, str):
                        try:
                            section_tags = json.loads(section_tags)
                        except json.JSONDecodeError:
                            section_tags = {}
                    self.app.state.section_tags = section_tags
                    self.app.state.total_fields = len(self.app.state.template_fields)
                elif hasattr(self.app, 'default_template_fields'):
                    self.app.state.template_fields = self.app.default_template_fields
                    self.app.state.total_fields = len(self.app.state.template_fields)
                    self.app.state.section_tags = {}
                else:
                    self.app.state.template_fields = []
                    self.app.state.section_tags = {}
                    self.app.state.total_fields = 0

                # Show enhanced survey form
                if self.app.state.template_fields:
                    self.app.ui_manager.show_enhanced_survey_ui()
                    self.app.state.current_question_index = 0
                    self.show_question()
                else:
                    self.app.ui_manager.status_label.text = "No template fields available for this survey"
            except ValueError:
                self.app.ui_manager.status_label.text = "Invalid survey ID"
        else:
            self.app.ui_manager.status_label.text = "Please select a survey"
        self.update_progress()


    def load_surveys_for_site(self, site_id):
        """Load surveys for the selected site"""
        surveys = self.app.db.get_surveys_for_site(site_id)
        if surveys:
            survey_names = [f"{s.id}: {s.title}" for s in surveys]
            self.app.ui_manager.survey_selection.items = survey_names
            self.app.ui_manager.status_label.text = f"Loaded {len(surveys)} surveys for site {self.app.state.current_site.name}"
        else:
            self.app.ui_manager.survey_selection.items = []
            self.app.ui_manager.status_label.text = f"No surveys available for site {self.app.state.current_site.name}"

    def submit_answer(self, widget):
        """Submit the current answer in enhanced UI with Phase 2 tracking"""
        state = self.app.state
        answer = self.app.ui_manager.answer_input.value.strip()
        # Check if this is a multiple choice question with options selected
        if not answer and self.app.ui_manager.options_selection.value:
            answer = self.app.ui_manager.options_selection.value
            response_type = 'multiple_choice'
        elif answer:
            response_type = 'text'
        else:
            self.app.ui_manager.status_label.text = "Please provide an answer"
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
        state.responses.append(response)
        state.current_responses.append(response)
        
        # Update pre-computed response lookup incrementally for fast conditional evaluation
        state.response_lookup[response['question_id']] = response['answer']

        # Save response immediately to database
        if state.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': state.current_survey['id'],
                'question_id': current_field['id'],
                'question': question,
                'answer': answer,
                'response_type': response_type,
                'field_type': current_field.get('field_type', 'text')
            }
            self.app.db.save_response(response_data)

        self.app.ui_manager.status_label.text = f"Answer submitted for: {question[:50]}..."
        self.next_question(None)

    def next_question(self, widget):
        """Move to next question"""
        self.app.state.current_question_index += 1
        self.show_question()

    def submit_yesno_answer(self, answer):
        """Submit yes/no answer in enhanced UI with Phase 2 tracking"""
        state = self.app.state
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
        state.responses.append(response)
        state.current_responses.append(response)
        
        # Update pre-computed response lookup incrementally for fast conditional evaluation
        state.response_lookup[response['question_id']] = response['answer']

        # Save response immediately to database
        if state.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': state.current_survey['id'],
                'question_id': current_field['id'],
                'question': question,
                'answer': answer,
                'response_type': 'yesno',
                'field_type': 'yesno'
            }
            self.app.db.save_response(response_data)

        self.app.ui_manager.status_label.text = f"Answer submitted: {answer}"
        state.current_question_index += 1
        self.show_question()

    def take_photo_enhanced(self, widget):
        """Take a photo in enhanced UI

        NOTE: Toga currently does not provide camera access APIs.
        Real camera integration would require platform-specific code:
        - iOS: AVFoundation framework
        - Android: Camera2 API
        - Desktop: Platform-specific camera libraries

        For now, this uses a file picker fallback for development/testing.
        """
        try:
            # Try to use file picker as fallback (if Toga supports it)
            if hasattr(self.app.main_window, 'open_file_dialog'):
                def on_file_selected(file_path):
                    if file_path:
                        with open(file_path, 'rb') as f:
                            photo_data = f.read()
                        self._process_photo_data(photo_data)
                    else:
                        # User cancelled - create mock photo for development
                        self._create_mock_photo()

                # Open file dialog for image selection
                self.app.main_window.open_file_dialog(
                    title="Select Photo",
                    file_types=['jpg', 'jpeg', 'png'],
                    on_result=on_file_selected
                )
            else:
                # Fallback to mock photo if no file dialog available
                self._create_mock_photo()

        except Exception as e:
            self.app.logger.warning(f"Photo capture failed, using mock: {e}")
            self._create_mock_photo()

    def _create_mock_photo(self):
        """Create a mock photo for development/testing"""
        img = Image.new('RGB', (640, 480), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=75)
        photo_data = img_byte_arr.getvalue()
        self._process_photo_data(photo_data)

    def _process_photo_data(self, photo_data):
        """Process the captured/selected photo data"""
        # Load image from bytes to extract EXIF data
        img = Image.open(io.BytesIO(photo_data))

        # Store photo ID for requirement tracking
        self.app.last_photo_id = str(uuid.uuid4())

        # Extract EXIF data
        exif_dict = {}
        if hasattr(img, '_getexif') and img._getexif():
            exif_dict = {ExifTags.TAGS.get(tag, tag): value for tag, value in img._getexif().items()}
        exif_json = json.dumps(exif_dict)

        # Get GPS location synchronously
        state = self.app.state
        lat, long = self.app.get_gps_location()
        if state.current_survey:
            # Save photo to database (hash and size computed automatically in save_photo)
            photo_record = {
                'id': self.app.last_photo_id,
                'survey_id': state.current_survey['id'],
                'image_data': photo_data,
                'latitude': lat,
                'longitude': long,
                'description': f"Photo for: {self.app.ui_manager.question_label.text}",
                'category': 'general',  # Using string directly
                'exif_data': exif_json,
                'tags': list(state.selected_photo_tags)
            }
            self.app.db.save_photo(photo_record)
            state.clear_photo_tag_selection()

            # Save response
            question = self.app.ui_manager.question_label.text
            response = {
                'question': question,
                'answer': f'[Photo captured - ID: {photo_record["id"]}]',
                'response_type': 'photo'
            }
            state.responses.append(response)

            # Save response to database immediately
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': state.current_survey['id'],
                'question': question,
                'answer': response['answer'],
                'response_type': 'photo'
            }
            self.app.db.save_response(response_data)

            self.app.ui_manager.status_label.text = f"Photo captured for: {question[:50]}..."
            state.current_question_index += 1
            self.show_question()

    def finish_survey(self, widget):
        """Finish the survey and save responses"""
        state = self.app.state
        if state.current_survey:
            # Save responses locally
            if hasattr(self.app.db, 'save_responses'):
                self.app.db.save_responses(state.current_survey['id'], state.responses)
            else:
                # Fallback: save each response individually
                for response in state.responses:
                    response_data = {
                        'id': str(uuid.uuid4()),
                        'survey_id': state.current_survey['id'],
                        'question': response['question'],
                        'answer': response['answer'],
                        'response_type': response.get('response_type', 'text')
                    }
                    self.app.db.save_response(response_data)

            # Hide enhanced survey form
            self.app.ui_manager.hide_enhanced_survey_ui()

            # Show CompanyCam sync button if connected
            if hasattr(self.app, 'companycam_handler') and self.app.companycam_service.is_connected():
                # Access the button through the UI
                if hasattr(self.app.ui_manager, 'sync_companycam_button'):
                    self.app.ui_manager.sync_companycam_button.style.visibility = 'visible'

            self.app.ui_manager.status_label.text = "Survey completed and saved!"

    def get_next_visible_field(self):
        """Get the next visible field based on conditional logic"""
        state = self.app.state
        if not state.template_fields:
            return None

        # Evaluate conditions for each field
        for i in range(state.current_question_index, len(state.template_fields)):
            field = state.template_fields[i]

            # Check if field has conditions
            if field.get('conditions'):
                # Use pre-computed response_lookup for fast evaluation
                from shared.utils import should_show_field
                if should_show_field(field['conditions'], response_lookup=state.response_lookup):
                    return field
            else:
                # No conditions, always show
                return field

        return None