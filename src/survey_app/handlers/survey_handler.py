"""Survey management handlers for SurveyApp."""
import toga
import uuid
import asyncio
from PIL import Image, ExifTags
import io
import base64


class SurveyHandler:
    """Handles survey-related operations."""

    def __init__(self, app):
        self.app = app

    def start_survey(self, widget):
        """Start the selected survey"""
        if self.app.survey_selection.value:
            survey_id_str = self.app.survey_selection.value.split(':')[0]
            try:
                survey_id = int(survey_id_str)
                # Try to fetch from server first
                try:
                    response = self.app.api_service.get(f'/surveys/{survey_id}', timeout=5)
                    if response.status_code == 200:
                        survey_data = response.json()
                        self.app.current_survey = survey_data
                        self.app.db.save_survey(survey_data)  # Cache locally
                    else:
                        # Try local cache
                        survey_data = self.app.db.get_survey(survey_id)
                        if survey_data:
                            self.app.current_survey = survey_data
                        else:
                            self.app.status_label.text = "Survey not found"
                            return
                except Exception as e:
                    # Try local cache if server unavailable
                    self.app.logger.warning(f"Server request failed, trying local cache: {e}")
                    survey_data = self.app.db.get_survey(survey_id)
                    if survey_data:
                        self.app.current_survey = survey_data
                    else:
                        self.app.status_label.text = "Survey not found and server unavailable"
                        return

                # Reset responses
                self.app.responses = []

                # Load template fields if survey has a template_id
                if survey_data.get('template_id'):
                    try:
                        # Use new conditional fields API
                        template_response = self.app.api_service.get(f'/templates/{survey_data["template_id"]}/conditional-fields', timeout=5)
                        if template_response.status_code == 200:
                            template_data = template_response.json()
                            self.app.template_fields = template_data['fields']
                            self.app.total_fields = len(self.app.template_fields)
                        else:
                            self.app.template_fields = []
                            self.app.total_fields = 0
                    except Exception as e:
                        self.app.logger.warning(f"Failed to load template fields: {e}")
                        self.app.template_fields = []
                        self.app.total_fields = 0
                elif hasattr(self.app, 'default_template_fields'):
                    self.app.template_fields = self.app.default_template_fields
                    self.app.total_fields = len(self.app.template_fields)
                else:
                    self.app.template_fields = []
                    self.app.total_fields = 0

                # Use enhanced UI if template fields are available, otherwise use legacy
                if self.app.template_fields:
                    # Show enhanced survey form
                    self.app.ui.show_survey_ui()
                    self.app.current_question_index = 0
                    self.app.ui.show_question()
                else:
                    # Use legacy UI
                    self.app.question_box.style.visibility = 'visible'
                    self.app.photo_box.style.visibility = 'visible'
                    self.load_questions()
                    self.app.ui.display_question()
            except ValueError:
                self.app.status_label.text = "Invalid survey ID"
        else:
            self.app.status_label.text = "Please select a survey"
        self.app.ui.update_progress()

    def load_questions(self):
        """Load questions for legacy UI"""
        if self.app.current_survey and self.app.current_survey.get('template_id'):
            self.app.questions = self.app.db.get_template_fields(self.app.current_survey['template_id'])
        else:
            self.app.questions = []

    def load_surveys_for_site(self, site_id):
        """Load surveys for the selected site"""
        surveys = self.app.db.get_surveys_for_site(site_id)
        if surveys:
            survey_names = [f"{s.id}: {s.title}" for s in surveys]
            self.app.survey_selection.items = survey_names
            self.app.status_label.text = f"Loaded {len(surveys)} surveys for site {self.app.current_site.name}"
        else:
            self.app.survey_selection.items = []
            self.app.status_label.text = f"No surveys available for site {self.app.current_site.name}"

    def submit_answer(self, widget):
        """Submit the current answer in enhanced UI with Phase 2 tracking"""
        answer = self.app.answer_input.value.strip()
        # Check if this is a multiple choice question with options selected
        if not answer and self.app.options_selection.value:
            answer = self.app.options_selection.value
            response_type = 'multiple_choice'
        elif answer:
            response_type = 'text'
        else:
            self.app.status_label.text = "Please provide an answer"
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
        self.app.responses.append(response)
        self.app.current_responses.append(response)

        # Save response immediately to database
        if self.app.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.app.current_survey['id'],
                'question_id': current_field['id'],
                'question': question,
                'answer': answer,
                'response_type': response_type,
                'field_type': current_field.get('field_type', 'text')
            }
            self.app.db.save_response(response_data)

        self.app.status_label.text = f"Answer submitted for: {question[:50]}..."
        self.next_question(None)

    def next_question(self, widget):
        """Move to next question - works for both legacy and enhanced UI"""
        # Save current response if using legacy UI
        if hasattr(self.app, 'questions') and self.app.questions and self.app.current_question_index < len(self.app.questions):
            self.save_response()
        self.app.current_question_index += 1

        # Use appropriate display method
        if hasattr(self.app, 'questions') and self.app.questions:
            self.app.ui.display_question()
        else:
            self.app.ui.show_question()

    def save_response(self):
        """Save response for legacy UI"""
        if hasattr(self.app, 'questions') and self.app.current_question_index < len(self.app.questions):
            question = self.app.questions[self.app.current_question_index]
            answer = ''
            if question['field_type'] == 'text':
                answer = self.app.answer_input_legacy.value
            elif question['field_type'] == 'multiple_choice':
                answer = self.app.answer_selection.value

            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.app.current_survey['id'],
                'question': question['question'],
                'answer': answer,
                'response_type': question['field_type']
            }
            self.app.db.save_response(response_data)
            self.app.status_label.text = f"Saved response for: {question['question']}"

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
        self.app.responses.append(response)
        self.app.current_responses.append(response)

        # Save response immediately to database
        if self.app.current_survey:
            response_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.app.current_survey['id'],
                'question_id': current_field['id'],
                'question': question,
                'answer': answer,
                'response_type': 'yesno',
                'field_type': 'yesno'
            }
            self.app.db.save_response(response_data)

        self.app.status_label.text = f"Answer submitted: {answer}"
        self.app.current_question_index += 1
        self.app.ui.show_question()

    def take_photo_enhanced(self, widget):
        """Take a photo in enhanced UI"""
        # Create dummy photo data (same as take_photo)
        img = Image.new('RGB', (640, 480), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=75)
        photo_data = img_byte_arr.getvalue()

        # Store photo ID for requirement tracking
        self.app.last_photo_id = str(uuid.uuid4())

        # Extract EXIF data
        exif_dict = {}
        if hasattr(img, '_getexif') and img._getexif():
            exif_dict = {ExifTags.TAGS.get(tag, tag): value for tag, value in img._getexif().items()}
        exif_json = json.dumps(exif_dict)

        # Get GPS location
        async def capture_with_location():
            lat, long = await self.app.get_gps_location()
            if self.app.current_survey:
                # Save photo to database (hash and size computed automatically in save_photo)
                photo_record = {
                    'id': self.app.last_photo_id,
                    'survey_id': self.app.current_survey['id'],
                    'image_data': photo_data,
                    'latitude': lat,
                    'longitude': long,
                    'description': f"Photo for: {self.app.question_label.text}",
                    'category': self.app.enums.PhotoCategory.GENERAL.value,
                    'exif_data': exif_json
                }
                self.app.db.save_photo(photo_record)

                # Save response
                question = self.app.question_label.text
                response = {
                    'question': question,
                    'answer': f'[Photo captured - ID: {photo_record["id"]}]',
                    'response_type': 'photo'
                }
                self.app.responses.append(response)

                # Save response to database immediately
                response_data = {
                    'id': str(uuid.uuid4()),
                    'survey_id': self.app.current_survey['id'],
                    'question': question,
                    'answer': response['answer'],
                    'response_type': 'photo'
                }
                self.app.db.save_response(response_data)

                self.app.status_label.text = f"Photo captured for: {question[:50]}..."
                self.app.current_question_index += 1
                self.app.ui.show_question()

        asyncio.create_task(capture_with_location())

    def finish_survey(self, widget):
        """Finish the survey and save responses"""
        if self.app.current_survey:
            # Save responses locally
            if hasattr(self.app.db, 'save_responses'):
                self.app.db.save_responses(self.app.current_survey['id'], self.app.responses)
            else:
                # Fallback: save each response individually
                for response in self.app.responses:
                    response_data = {
                        'id': str(uuid.uuid4()),
                        'survey_id': self.app.current_survey['id'],
                        'question': response['question'],
                        'answer': response['answer'],
                        'response_type': response.get('response_type', 'text')
                    }
                    self.app.db.save_response(response_data)

            # Hide enhanced survey form
            self.app.survey_title_label.style.visibility = 'hidden'
            self.app.progress_label.style.visibility = 'hidden'
            self.app.question_label.style.visibility = 'hidden'
            self.app.answer_input.style.visibility = 'hidden'
            self.app.yes_button.style.visibility = 'hidden'
            self.app.no_button.style.visibility = 'hidden'
            self.app.options_selection.style.visibility = 'hidden'
            self.app.enhanced_photo_button.style.visibility = 'hidden'

            # Hide legacy UI as well
            self.app.question_box.style.visibility = 'hidden'
            self.app.photo_box.style.visibility = 'hidden'

            self.app.status_label.text = "Survey completed and saved!"

    def get_next_visible_field(self):
        """Get the next visible field based on conditional logic"""
        if not self.app.template_fields:
            return None

        # Evaluate conditions for each field
        for i in range(self.app.current_question_index, len(self.app.template_fields)):
            field = self.app.template_fields[i]

            # Check if field has conditions
            if field.get('conditions'):
                if self.app.db.should_show_field(field['conditions'], self.app.current_responses):
                    return field
            else:
                # No conditions, always show
                return field

        return None