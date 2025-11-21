"""Site Survey App - Main application."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from .local_db import LocalDatabase
from .state import SessionState
from shared.enums import ProjectStatus, PriorityLevel, PhotoCategory
from .handlers.project_handler import ProjectHandler
from .handlers.site_handler import SiteHandler
from .handlers.survey_handler import SurveyHandler
from .handlers.photo_handler import PhotoHandler
from .handlers.template_handler import TemplateHandler
from .handlers.sync_handler import SyncHandler
from .handlers.companycam_handler import CompanyCamHandler
from .handlers.tag_management_handler import TagManagementHandler
from .ui.survey_ui import SurveyUI
from .ui.login_ui import LoginUI
from .ui.team_ui import TeamUI
from .ui_manager import UIManager
from .config_manager import ConfigManager
from .services.api_service import APIService
from .services.auth_service import AuthService
from .services.db_service import DBService
from .services.companycam_service import CompanyCamService
from .services.tag_mapper import TagMapper
from .logging_config import setup_logging
import logging
import uuid
import time
import threading
import json
import io
import asyncio
import concurrent.futures
from PIL import Image, ExifTags


class SurveyApp(toga.App):
    """Main SurveyApp class."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__(formal_name='Site Survey App', app_id='com.keith.surveyapp')

    def startup(self):
        """Initialize the app"""
        self.logger.info("Starting SurveyApp initialization")
        
        # Setup logging first
        setup_logging()
        self.logger.info("Logging system initialized")

        # Initialize configuration
        self.logger.info("Initializing configuration manager")
        self.config = ConfigManager()
        self.logger.info(f"Configuration loaded: API URL={self.config.api_base_url}")

        # Initialize services
        self.logger.info("Initializing database and services")
        self.db = LocalDatabase(config=self.config)
        self.logger.info("Local database initialized")
        
        self.db_service = DBService(self.db)
        self.logger.debug("Database service initialized")

        self.auth_service = AuthService(self.config.api_base_url)
        self.logger.info("Auth service initialized")
        
        self.api_service = APIService(
            self.config.api_base_url,
            offline_queue=self.state.offline_queue if hasattr(self, 'state') else None,
            auth_service=self.auth_service
        )
        # Note: self.state is initialized later, so offline_queue might be None initially.
        # But APIService usually needs it for offline support.
        # We'll fix order below.
        
        self.companycam_service = CompanyCamService(self.config)
        self.logger.info("CompanyCam service initialized")
        
        self.tag_mapper = TagMapper(self.companycam_service)
        self.logger.debug("Tag mapper initialized")

        # Initialize state
        self.logger.debug("Initializing application state")
        self.state = SessionState()
        # Update APIService with offline queue now that state exists
        self.api_service.offline_queue = self.state.offline_queue
        self.logger.debug("Application state initialized")

        # Initialize thread pool executor for background operations
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.logger.debug("Thread pool executor initialized")

        # Initialize handlers
        self.logger.info("Initializing event handlers")
        self.project_handler = ProjectHandler(self)
        self.logger.debug("Project handler initialized")
        self.site_handler = SiteHandler(self)
        self.logger.debug("Site handler initialized")
        self.survey_handler = SurveyHandler(self)
        self.logger.debug("Survey handler initialized")
        self.photo_handler = PhotoHandler(self)
        self.logger.debug("Photo handler initialized")
        self.template_handler = TemplateHandler(self)
        self.logger.debug("Template handler initialized")
        self.sync_handler = SyncHandler(self)
        self.logger.debug("Sync handler initialized")
        self.companycam_handler = CompanyCamHandler(self)
        self.logger.debug("CompanyCam handler initialized")
        self.tag_management_handler = TagManagementHandler(self)
        self.logger.debug("Tag management handler initialized")
        self.logger.info("All event handlers initialized")

        # Pass config to handlers that need it
        self.photo_handler.config = self.config
        self.logger.debug("Configuration passed to photo handler")

        # Initialize UI
        self.logger.info("Initializing user interface")
        self.ui = SurveyUI(self)
        self.logger.debug("Survey UI initialized")
        self.ui_manager = UIManager(self)
        self.logger.debug("UI manager initialized")

        # Create main window
        self.logger.info("Creating main application window")
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.ui_manager.main_window = self.main_window
        self.logger.debug(f"Main window created: {self.formal_name}")

        # Auth check flow
        if not self.auth_service.is_authenticated():
            self.show_login()
        else:
            self.on_login_success()

        # Show the main window
        self.main_window.show()
        self.logger.info("Main window displayed")

        # Start the background sync scheduler (only if authenticated?)
        # We can start it, but sync checks might fail if not auth.
        # But SyncHandler handles API errors.
        self.logger.info("Starting background sync scheduler")
        self.sync_handler.start_sync_scheduler()
        self.logger.info("Background sync scheduler started")

        # Initialize location service
        self.logger.info("Initializing location service")
        self.location = toga.Location()
        self.logger.info("Location service initialized")
        
        self.logger.info("SurveyApp initialization completed successfully")

    def show_login(self):
        """Show login UI."""
        self.login_ui = LoginUI(self, self.on_login_success)
        self.main_window.content = self.login_ui.layout
        # Clear toolbar
        self.main_window.toolbar.clear()

    def on_login_success(self):
        """Handle successful login."""
        self.logger.info(f"Login successful/verified for: {self.auth_service.user.get('username')}")

        # Create main UI
        self.ui_manager.create_main_ui()

        # Add commands to toolbar
        cmd_team = toga.Command(
            self.show_team_management,
            text='Team',
            tooltip='Manage Team',
            group=toga.Group.FILE,
            section=1
        )
        cmd_logout = toga.Command(
            self.logout,
            text='Logout',
            tooltip='Logout',
            group=toga.Group.FILE,
            section=2
        )

        # Refresh toolbar
        # Note: UIManager might have already added some commands?
        # UIManager doesn't seem to add toolbar commands in create_main_ui based on previous code.
        # But handlers might have added some? No, they usually attach to buttons.
        self.main_window.toolbar.add(cmd_team, cmd_logout)

    def logout(self, widget):
        """Logout user."""
        self.auth_service.logout()
        self.show_login()

    def show_team_management(self, widget):
        """Show team management UI."""
        self.team_ui = TeamUI(self, self.restore_main_ui)
        self.main_window.content = self.team_ui.layout

    def restore_main_ui(self):
        """Restore main UI after team management."""
        self.ui_manager.create_main_ui()

    def get_gps_location(self):
        """Get current GPS location synchronously."""
        try:
            location_info = self.location.current_location()
            return location_info.latitude, location_info.longitude
        except Exception as e:
            if hasattr(self, 'ui_manager') and hasattr(self.ui_manager, 'status_label'):
                self.ui_manager.status_label.text = f"GPS error: {e}"
            return None, None

    def capture_photo(self):
        """
        Capture a photo using the device camera with fallback to file picker.
        Returns raw image bytes (JPEG) or None if cancelled/failed.
        """
        try:
            # Check camera availability and permissions
            if not self.camera:
                self.logger.warning("No camera device available")
                return self._fallback_capture_photo()

            try:
                # Request permission - for now assume permission is granted
                # (camera permission handling would need to be synchronous)
                self.logger.info("Camera permission requested (simulated)")

                # Take photo - for now use fallback since camera API is async
                self.logger.warning("Camera API not implemented synchronously, using fallback")
                return self._fallback_capture_photo()
            except NotImplementedError:
                self.logger.warning("Camera API not implemented on this platform")
                return self._fallback_capture_photo()
            except Exception as e:
                self.logger.error(f"Camera error: {e}")
                return self._fallback_capture_photo()

        except Exception as e:
            self.logger.error(f"Photo capture failed: {e}")
            return self._fallback_capture_photo()

    def _fallback_capture_photo(self):
        """Fallback photo capture using mock generation (file picker not available in threads)"""
        # Note: File picker dialogs cannot be used from background threads
        # They must be called from the main thread. For now, use mock photo.
        self.logger.info("Using mock photo for fallback capture (file picker not available in thread)")
        return self._create_mock_photo_bytes()

    def _create_mock_photo_bytes(self):
        """Create a mock photo for development/testing"""
        img = Image.new('RGB', (640, 480), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=self.config.image_compression_quality)
        return img_byte_arr.getvalue()

    def schedule_auto_save(self, question_id, answer_text):
        """Delegate to survey handler"""
        self.survey_handler.schedule_auto_save(question_id, answer_text)

    def perform_auto_save(self, question_id):
        """Delegate to survey handler"""
        self.survey_handler.perform_auto_save(question_id)

    def toggle_photo_tag(self, tag, enabled):
        """Track photo tag selection toggles."""
        if enabled:
            self.state.selected_photo_tags.add(tag)
        else:
            self.state.selected_photo_tags.discard(tag)

    def clear_photo_tag_selection(self):
        """Reset tag toggles for the current section."""
        self.state.clear_photo_tag_selection()

    def on_answer_input_change(self, widget):
        """Handle answer input changes for auto-save"""
        if hasattr(widget, 'value') and self.state.current_survey:
            current_field = self.survey_handler.get_next_visible_field()
            if current_field:
                self.schedule_auto_save(current_field['id'], widget.value)

    def start_survey(self, widget):
        """Delegate to survey handler"""
        self.survey_handler.start_survey(widget)

    def sync_with_server(self, widget):
        """Delegate to sync handler"""
        self.sync_handler.sync_with_server(widget)

    def show_photos_ui(self, widget):
        """Delegate to photo handler"""
        self.photo_handler.show_photos_ui(widget)

    # Delegate methods to handlers
    def load_survey_from_selection(self):
        """Delegate to survey handler"""
        self.survey_handler.load_survey_from_selection()

    def update_progress(self):
        """Delegate to survey handler"""
        self.survey_handler.update_progress()

    def show_survey_ui(self):
        """Show the enhanced survey interface"""
        self.ui_manager.show_enhanced_survey_ui()
        if self.ui_manager.survey_title_label:
            self.ui_manager.survey_title_label.text = self.state.current_survey['title']

    def show_question(self):
        """Delegate to survey handler"""
        self.survey_handler.show_question()

    def get_next_visible_field(self):
        """Delegate to survey handler"""
        self.survey_handler.get_next_visible_field()

    def show_photo_requirements(self, photo_requirements):
        """Delegate to survey handler"""
        self.survey_handler.show_photo_requirements(photo_requirements)

    def submit_answer(self, widget):
        """Delegate to survey handler"""
        self.survey_handler.submit_answer(widget)

    def next_question(self, widget):
        """Delegate to survey handler"""
        self.survey_handler.next_question(widget)

    def submit_yesno_answer(self, answer):
        """Delegate to survey handler"""
        self.survey_handler.submit_yesno_answer(answer)

    def take_photo_enhanced(self, widget):
        """Delegate to survey handler"""
        self.survey_handler.take_photo_enhanced(widget)

    def finish_survey(self, widget):
        """Delegate to survey handler"""
        self.survey_handler.finish_survey(widget)

    def show_projects_ui(self, widget):
        """Delegate to project handler"""
        self.project_handler.show_projects_ui(widget)

    def load_projects(self, widget):
        """Delegate to project handler"""
        self.project_handler.load_projects(widget)

    def create_project(self, widget):
        """Delegate to project handler"""
        self.project_handler.create_project(widget)

    def select_project(self, projects_window):
        """Delegate to project handler"""
        self.project_handler.select_project(projects_window)

    def load_sites_for_project(self, project_id):
        """Delegate to site handler"""
        self.site_handler.load_sites_for_project(project_id)

    def show_sites_ui(self, widget):
        """Delegate to site handler"""
        self.site_handler.show_sites_ui(widget)

    def load_sites(self, widget):
        """Delegate to site handler"""
        self.site_handler.load_sites(widget)

    def create_site(self, widget):
        """Delegate to site handler"""
        self.site_handler.create_site(widget)

    def select_site(self, sites_window):
        """Delegate to site handler"""
        self.site_handler.select_site(sites_window)

    def load_surveys_for_site(self, site_id):
        """Delegate to survey handler"""
        self.survey_handler.load_surveys_for_site(site_id)

    def show_templates_ui(self, widget):
        """Delegate to template handler"""
        self.template_handler.show_templates_ui(widget)

    def load_templates(self, widget):
        """Delegate to template handler"""
        self.template_handler.load_templates(widget)

    def create_survey_from_template(self, widget):
        """Delegate to template handler"""
        self.template_handler.create_survey_from_template(widget)

    def show_config_ui(self, widget):
        """Delegate to sync handler"""
        self.sync_handler.show_config_ui(widget)

    def save_config(self, widget):
        """Delegate to sync handler"""
        self.sync_handler.save_config(widget)


def main():
    return SurveyApp()
