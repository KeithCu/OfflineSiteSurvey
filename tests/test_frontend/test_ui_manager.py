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

        # Mock toga components with proper style mocks
        mock_style = Mock()
        mock_label = Mock()
        mock_label.style = mock_style
        mock_toga.Label = Mock(return_value=mock_label)

        ui_manager = UIManager(mock_app)
        # Don't call create_main_ui, just manually set components
        ui_manager.survey_title_label = mock_label

        # Create mocks for other components with style attributes
        for attr in ['progress_label', 'question_label', 'answer_input', 'yes_button', 'no_button', 'options_selection', 'enhanced_photo_button']:
            mock_component = Mock()
            mock_component.style = Mock()
            setattr(ui_manager, attr, mock_component)

        ui_manager.hide_enhanced_survey_ui()

        # Verify visibility was set to hidden
        assert mock_style.visibility == 'hidden'
        assert ui_manager.progress_label.style.visibility == 'hidden'
        assert ui_manager.question_label.style.visibility == 'hidden'

    def test_show_question_ui_text(self):
        """Test showing question UI for text input."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)

        # Mock UI components with style attributes
        for attr in ['answer_input', 'yes_button', 'no_button', 'options_selection', 'enhanced_photo_button']:
            mock_component = Mock()
            mock_component.style = Mock()
            setattr(ui_manager, attr, mock_component)

        ui_manager.show_question_ui('text', None, 'Enter answer')

        # Verify text input is shown with correct placeholder
        assert ui_manager.answer_input.style.visibility == 'visible'
        assert ui_manager.answer_input.placeholder == 'Enter answer'

        # Verify other inputs are hidden
        assert ui_manager.yes_button.style.visibility == 'hidden'
        assert ui_manager.options_selection.style.visibility == 'hidden'

    def test_show_question_ui_yesno(self):
        """Test showing question UI for yes/no input."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)

        # Mock UI components with style attributes
        for attr in ['answer_input', 'yes_button', 'no_button', 'options_selection', 'enhanced_photo_button']:
            mock_component = Mock()
            mock_component.style = Mock()
            setattr(ui_manager, attr, mock_component)

        ui_manager.show_question_ui('yesno', None, None)

        # Verify yes/no buttons are shown
        assert ui_manager.yes_button.style.visibility == 'visible'
        assert ui_manager.no_button.style.visibility == 'visible'

        # Verify other inputs are hidden
        assert ui_manager.answer_input.style.visibility == 'hidden'
        assert ui_manager.options_selection.style.visibility == 'hidden'

    def test_show_question_ui_options(self):
        """Test showing question UI for multiple choice."""
        mock_app = Mock()
        from src.survey_app.ui_manager import UIManager

        ui_manager = UIManager(mock_app)

        # Mock UI components with style attributes
        for attr in ['answer_input', 'yes_button', 'no_button', 'options_selection', 'enhanced_photo_button']:
            mock_component = Mock()
            mock_component.style = Mock()
            setattr(ui_manager, attr, mock_component)

        options = ['Option 1', 'Option 2']
        ui_manager.show_question_ui('text', options, None)

        # Verify selection is shown with options
        assert ui_manager.options_selection.items == options
        assert ui_manager.options_selection.style.visibility == 'visible'

        # Verify other inputs are hidden
        assert ui_manager.answer_input.style.visibility == 'hidden'
        assert ui_manager.yes_button.style.visibility == 'hidden'
