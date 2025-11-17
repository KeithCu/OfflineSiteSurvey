"""Tests for UI manager."""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestUIManager:
    """Test UI manager functionality."""

    def test_ui_manager_initialization(self):
        """Test that UI manager initializes correctly."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)
        assert ui_manager.app == mock_app
        assert ui_manager.main_window is None
        assert ui_manager.survey_selection is None
        assert ui_manager.status_label is None

    @patch('src.survey_app.ui_manager.toga')
    def test_create_main_ui_assigns_components(self, mock_toga):
        """Test that create_main_ui assigns UI components."""
        mock_app = Mock()
        mock_window = Mock()

        # Mock toga components
        mock_toga.Label = Mock()
        mock_toga.Button = Mock()
        mock_toga.Selection = Mock()
        mock_toga.TextInput = Mock()
        mock_toga.Box = Mock()
        mock_toga.ProgressBar = Mock()

        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)
        ui_manager.main_window = mock_window

        ui_manager.create_main_ui()

        # Check that components were assigned
        assert ui_manager.survey_selection is not None
        assert ui_manager.status_label is not None
        assert ui_manager.progress_label is not None
        assert ui_manager.question_label is not None
        assert ui_manager.answer_input is not None

    @patch('src.survey_app.ui_manager.toga')
    def test_hide_enhanced_survey_ui(self, mock_toga):
        """Test hiding enhanced survey UI elements."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        # Mock toga components
        mock_label = Mock()
        mock_toga.Label = Mock(return_value=mock_label)

        ui_manager = UIManager(mock_app)
        # Don't call create_main_ui, just manually set components
        ui_manager.survey_title_label = mock_label
        ui_manager.progress_label = Mock()
        ui_manager.question_label = Mock()
        ui_manager.answer_input = Mock()
        ui_manager.yes_button = Mock()
        ui_manager.no_button = Mock()
        ui_manager.options_selection = Mock()
        ui_manager.enhanced_photo_button = Mock()

        ui_manager.hide_enhanced_survey_ui()

        # Verify visibility was set to hidden
        mock_label.style.visibility.assert_called_with('hidden')
        ui_manager.progress_label.style.visibility.assert_called_with('hidden')
        ui_manager.question_label.style.visibility.assert_called_with('hidden')

    def test_show_question_ui_text(self):
        """Test showing question UI for text input."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)

        # Mock UI components
        ui_manager.answer_input = Mock()
        ui_manager.yes_button = Mock()
        ui_manager.no_button = Mock()
        ui_manager.options_selection = Mock()
        ui_manager.enhanced_photo_button = Mock()

        ui_manager.show_question_ui('text', None, 'Enter answer')

        # Verify text input is shown with correct placeholder
        ui_manager.answer_input.style.visibility.assert_called_with('visible')
        ui_manager.answer_input.placeholder.assert_called_with('Enter answer')

        # Verify other inputs are hidden
        ui_manager.yes_button.style.visibility.assert_called_with('hidden')
        ui_manager.options_selection.style.visibility.assert_called_with('hidden')

    def test_show_question_ui_yesno(self):
        """Test showing question UI for yes/no input."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)

        # Mock UI components
        ui_manager.answer_input = Mock()
        ui_manager.yes_button = Mock()
        ui_manager.no_button = Mock()
        ui_manager.options_selection = Mock()
        ui_manager.enhanced_photo_button = Mock()

        ui_manager.show_question_ui('yesno', None, None)

        # Verify yes/no buttons are shown
        ui_manager.yes_button.style.visibility.assert_called_with('visible')
        ui_manager.no_button.style.visibility.assert_called_with('visible')

        # Verify other inputs are hidden
        ui_manager.answer_input.style.visibility.assert_called_with('hidden')
        ui_manager.options_selection.style.visibility.assert_called_with('hidden')

    def test_show_question_ui_options(self):
        """Test showing question UI for multiple choice."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)

        # Mock UI components
        ui_manager.answer_input = Mock()
        ui_manager.yes_button = Mock()
        ui_manager.no_button = Mock()
        ui_manager.options_selection = Mock()
        ui_manager.enhanced_photo_button = Mock()

        options = ['Option 1', 'Option 2']
        ui_manager.show_question_ui('text', options, None)

        # Verify selection is shown with options
        ui_manager.options_selection.items.assert_called_with(options)
        ui_manager.options_selection.style.visibility.assert_called_with('visible')

        # Verify other inputs are hidden
        ui_manager.answer_input.style.visibility.assert_called_with('hidden')
        ui_manager.yes_button.style.visibility.assert_called_with('hidden')
