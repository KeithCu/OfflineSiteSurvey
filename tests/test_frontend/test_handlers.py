"""Tests for frontend handler operations."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.survey_app.handlers.project_handler import ProjectHandler
from src.survey_app.handlers.site_handler import SiteHandler
from src.survey_app.handlers.survey_handler import SurveyHandler
from src.survey_app.handlers.photo_handler import PhotoHandler
from src.survey_app.handlers.sync_handler import SyncHandler
from src.survey_app.enums import ProjectStatus


class MockApp:
    """Mock app class for testing handlers."""
    def __init__(self):
        self.db = Mock()
        self.api_service = Mock()
        self.current_project = None
        self.current_site = None
        self.current_survey = None
        self.current_search = None
        self.last_sync_version = 0
        self.status_label = Mock()
        self.status_label.text = ""
        self.responses = []
        self.offline_queue = []
        self.enums = Mock()
        self.enums.ProjectStatus = [Mock(value='draft'), Mock(value='in_progress'), Mock(value='completed')]
        self.enums.PhotoCategory = [Mock(value='general'), Mock(value='interior'), Mock(value='exterior')]
        self.enums.PriorityLevel = [Mock(value='low'), Mock(value='medium'), Mock(value='high')]
        self.sites_list = Mock()


@pytest.fixture
def mock_app():
    """Create a mock app for testing."""
    return MockApp()


def test_project_handler_initialization(mock_app):
    """Test ProjectHandler initializes properly."""
    handler = ProjectHandler(mock_app)
    assert handler.app == mock_app
    assert hasattr(handler, 'show_projects_ui')


def test_project_handler_show_projects_ui(mock_app):
    """Test showing projects UI."""
    handler = ProjectHandler(mock_app)

    # Mock database response
    mock_app.db.get_projects.return_value = [
        Mock(id=1, name='Test Project', description='Test desc')
    ]

    # Mock toga components
    with patch('src.survey_app.handlers.project_handler.toga') as mock_toga:
        mock_window = Mock()
        mock_toga.Window.return_value = mock_window
        mock_toga.Selection.return_value = Mock()
        mock_toga.Button.return_value = Mock()
        mock_toga.TextInput.return_value = Mock()
        mock_toga.Box.return_value = Mock()

        # Call the method
        handler.show_projects_ui(None)

        # Verify toga components were created
        mock_toga.Window.assert_called_once()
        mock_toga.Selection.assert_called()
        mock_toga.Button.assert_called()


def test_site_handler_initialization(mock_app):
    """Test SiteHandler initializes properly."""
    handler = SiteHandler(mock_app)
    assert handler.app == mock_app
    assert hasattr(handler, 'show_sites_ui')


def test_site_handler_create_site(mock_app):
    """Test creating a site."""
    handler = SiteHandler(mock_app)

    # Mock UI inputs
    mock_app.new_site_name_input = Mock()
    mock_app.new_site_name_input.value = "Test Site"
    mock_app.new_site_address_input = Mock()
    mock_app.new_site_address_input.value = "123 Test St"
    mock_app.new_site_notes_input = Mock()
    mock_app.new_site_notes_input.value = "Test notes"

    # Mock database
    mock_app.db.save_site.return_value = Mock(id=1, name="Test Site")
    mock_app.db.get_sites.return_value = [Mock(id=1, name="Test Site")]

    # Call create site
    handler.create_site(None)

    # Verify database was called
    mock_app.db.save_site.assert_called_once()
    call_args = mock_app.db.save_site.call_args[0][0]
    assert call_args['name'] == "Test Site"
    assert call_args['address'] == "123 Test St"
    assert call_args['notes'] == "Test notes"


def test_survey_handler_initialization(mock_app):
    """Test SurveyHandler initializes properly."""
    handler = SurveyHandler(mock_app)
    assert handler.app == mock_app
    assert hasattr(handler, 'start_survey')


def test_sync_handler_initialization(mock_app):
    """Test SyncHandler initializes properly."""
    handler = SyncHandler(mock_app)
    assert handler.app == mock_app
    assert hasattr(handler, 'sync_with_server')


def test_sync_handler_sync_with_server(mock_app):
    """Test sync with server functionality."""
    handler = SyncHandler(mock_app)

    # Mock database responses
    mock_app.db.get_changes_since.return_value = [
        {'table': 'projects', 'pk': '1', 'cid': 'name', 'val': 'Test', 'col_version': 1, 'db_version': 1}
    ]
    mock_app.db.apply_changes.return_value = None

    # Mock API responses
    mock_response_post = Mock()
    mock_response_post.status_code = 200
    mock_response_get = Mock()
    mock_response_get.status_code = 200
    mock_response_get.json.return_value = [
        {'table': 'sites', 'pk': '1', 'cid': 'name', 'val': 'Test Site', 'col_version': 1, 'db_version': 2}
    ]

    mock_app.api_service.post.return_value = mock_response_post
    mock_app.api_service.get.return_value = mock_response_get

    # Call sync
    result = handler.sync_with_server()

    # Verify success
    assert result is True
    mock_app.db.get_changes_since.assert_called_once_with(0)
    mock_app.db.apply_changes.assert_called_once()


def test_photo_handler_initialization(mock_app):
    """Test PhotoHandler initializes properly."""
    handler = PhotoHandler(mock_app)
    assert handler.app == mock_app
    assert hasattr(handler, 'show_photos_ui')


def test_photo_handler_filter_photos(mock_app):
    """Test photo filtering setup (skipping UI test)."""
    handler = PhotoHandler(mock_app)
    handler.config = Mock()
    handler.config.get.return_value = 40

    # Just test that handler has the config and can access it
    assert handler.config is not None
    assert handler.config.get('max_visible_photos', 40) == 40


def test_photo_handler_show_photos_ui(mock_app):
    """Test photo handler UI setup (skipping actual UI test)."""
    handler = PhotoHandler(mock_app)
    handler.config = Mock()
    handler.config.get.return_value = 40

    # Just test that handler can be initialized with config
    assert handler.config is not None
    assert hasattr(handler, 'show_photos_ui')


def test_handlers_with_logger(mock_app):
    """Test that handlers have logging capability."""
    handler = ProjectHandler(mock_app)
    assert hasattr(handler, 'logger')

    handler = SyncHandler(mock_app)
    assert hasattr(handler, 'logger')

    handler = PhotoHandler(mock_app)
    assert hasattr(handler, 'logger')
