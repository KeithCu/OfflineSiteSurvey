"""UI Builder utility for reducing Toga boilerplate."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


def create_label(text, style_overrides=None):
    """Create a Label widget with default styling.
    
    Args:
        text: Label text
        style_overrides: Optional dict of style overrides
        
    Returns:
        toga.Label widget
    """
    default_style = Pack(padding=(5, 10, 5, 10))
    if style_overrides:
        default_style.update(**style_overrides)
    return toga.Label(text, style=default_style)


def create_text_input(placeholder='', style_overrides=None, on_change=None):
    """Create a TextInput widget with default styling.
    
    Args:
        placeholder: Placeholder text
        style_overrides: Optional dict of style overrides
        on_change: Optional change handler
        
    Returns:
        toga.TextInput widget
    """
    default_style = Pack(padding=(5, 10, 10, 10))
    if style_overrides:
        default_style.update(**style_overrides)
    widget = toga.TextInput(placeholder=placeholder, style=default_style)
    if on_change:
        widget.on_change = on_change
    return widget


def create_button(text, on_press=None, style_overrides=None):
    """Create a Button widget with default styling.
    
    Args:
        text: Button text
        on_press: Optional press handler
        style_overrides: Optional dict of style overrides
        
    Returns:
        toga.Button widget
    """
    default_style = Pack(padding=(5, 10, 10, 10))
    if style_overrides:
        default_style.update(**style_overrides)
    return toga.Button(text, on_press=on_press, style=default_style)


def create_selection(items=None, style_overrides=None):
    """Create a Selection widget with default styling.
    
    Args:
        items: Optional list of items
        style_overrides: Optional dict of style overrides
        
    Returns:
        toga.Selection widget
    """
    default_style = Pack(padding=(5, 10, 10, 10))
    if style_overrides:
        default_style.update(**style_overrides)
    return toga.Selection(items=items or [], style=default_style)


def create_field(label_text, placeholder='', style_overrides=None, on_change=None):
    """Create a Box containing a Label and TextInput.
    
    Args:
        label_text: Label text
        placeholder: Input placeholder text
        style_overrides: Optional dict of style overrides for the Box
        on_change: Optional change handler for the input
        
    Returns:
        toga.Box containing Label and TextInput
    """
    label = create_label(label_text)
    text_input = create_text_input(placeholder, on_change=on_change)
    
    box_style = Pack(direction=COLUMN)
    if style_overrides:
        box_style.update(**style_overrides)
    
    return toga.Box(
        children=[label, text_input],
        style=box_style
    )


class SurveyQuestionWidget(toga.Box):
    """Composite widget for displaying a survey question with appropriate input.
    
    Encapsulates the question label and input widget based on field type.
    Manages visibility and updates internally.
    """
    
    def __init__(self, style_overrides=None):
        """Initialize the survey question widget.
        
        Args:
            style_overrides: Optional dict of style overrides for the container Box
        """
        box_style = Pack(direction=COLUMN, padding=(10, 10, 5, 10))
        if style_overrides:
            box_style.update(**style_overrides)
        
        self.question_label = create_label(
            '',
            style_overrides={'padding': (10, 10, 5, 10)}
        )
        
        self.answer_input = create_text_input(
            placeholder='Enter your answer',
            style_overrides={'padding': (5, 10, 10, 10)}
        )
        
        self.yes_button = create_button(
            'Yes',
            style_overrides={'padding': (5, 10, 5, 5)}
        )
        
        self.no_button = create_button(
            'No',
            style_overrides={'padding': (5, 10, 10, 5)}
        )
        
        self.options_selection = create_selection(
            style_overrides={'padding': (5, 10, 10, 10)}
        )
        
        self.photo_button = create_button(
            '📷 Take Photo',
            style_overrides={'padding': (5, 10, 10, 10)}
        )
        
        button_row = toga.Box(
            children=[self.yes_button, self.no_button],
            style=Pack(direction=ROW)
        )
        
        super().__init__(
            children=[
                self.question_label,
                self.answer_input,
                button_row,
                self.options_selection,
                self.photo_button
            ],
            style=box_style
        )
        
        self._hide_all_inputs()
    
    def _hide_all_inputs(self):
        """Hide all input widgets."""
        self.answer_input.style.visibility = 'hidden'
        self.yes_button.style.visibility = 'hidden'
        self.no_button.style.visibility = 'hidden'
        self.options_selection.style.visibility = 'hidden'
        self.photo_button.style.visibility = 'hidden'
    
    def update_question(self, question_text, required=False):
        """Update the question label text.
        
        Args:
            question_text: The question text to display
            required: Whether the question is required (adds * indicator)
        """
        required_indicator = " * " if required else " "
        self.question_label.text = f"{required_indicator}{question_text}"
    
    def show_text_input(self, placeholder='Enter your answer', value='', on_change=None):
        """Show text input widget.
        
        Args:
            placeholder: Placeholder text for the input
            value: Initial value for the input
            on_change: Optional change handler
        """
        self._hide_all_inputs()
        self.answer_input.placeholder = placeholder
        self.answer_input.value = value
        if on_change:
            self.answer_input.on_change = on_change
        self.answer_input.style.visibility = 'visible'
    
    def show_yesno_buttons(self, on_yes=None, on_no=None):
        """Show Yes/No buttons.
        
        Args:
            on_yes: Optional handler for Yes button press
            on_no: Optional handler for No button press
        """
        self._hide_all_inputs()
        if on_yes:
            self.yes_button.on_press = on_yes
        if on_no:
            self.no_button.on_press = on_no
        self.yes_button.style.visibility = 'visible'
        self.no_button.style.visibility = 'visible'
    
    def show_selection(self, items, on_change=None):
        """Show selection dropdown.
        
        Args:
            items: List of items for the selection
            on_change: Optional change handler
        """
        self._hide_all_inputs()
        self.options_selection.items = items
        if on_change:
            self.options_selection.on_change = on_change
        self.options_selection.style.visibility = 'visible'
    
    def show_photo_button(self, on_press=None):
        """Show photo capture button.
        
        Args:
            on_press: Optional handler for photo button press
        """
        self._hide_all_inputs()
        if on_press:
            self.photo_button.on_press = on_press
        self.photo_button.style.visibility = 'visible'
    
    def get_answer_value(self):
        """Get the current answer value based on visible input type.
        
        Returns:
            The answer value or None if no input is visible
        """
        if self.answer_input.style.visibility == 'visible':
            return self.answer_input.value
        elif self.options_selection.style.visibility == 'visible':
            return self.options_selection.value
        elif self.yes_button.style.visibility == 'visible':
            return None
        elif self.photo_button.style.visibility == 'visible':
            return None
        return None
    
    def set_visible(self, visible=True):
        """Set widget visibility.
        
        Args:
            visible: Whether to show or hide the widget
        """
        self.style.visibility = 'visible' if visible else 'hidden'


class SurveyProgressWidget(toga.Box):
    """Composite widget for displaying survey progress."""
    
    def __init__(self, style_overrides=None):
        """Initialize the progress widget.
        
        Args:
            style_overrides: Optional dict of style overrides for the container Box
        """
        box_style = Pack(direction=COLUMN, padding=(5, 10, 5, 10))
        if style_overrides:
            box_style.update(**style_overrides)
        
        self.progress_label = create_label(
            '',
            style_overrides={'color': '#666666', 'padding': (5, 10, 5, 10)}
        )
        
        super().__init__(
            children=[self.progress_label],
            style=box_style
        )
    
    def update_progress(self, current, total, percentage=None):
        """Update progress display.
        
        Args:
            current: Current progress value
            total: Total value
            percentage: Optional percentage (calculated if not provided)
        """
        if percentage is None:
            percentage = (current / total * 100) if total > 0 else 0
        self.progress_label.text = f"Progress: {current}/{total} ({percentage:.1f}%)"
    
    def set_visible(self, visible=True):
        """Set widget visibility.
        
        Args:
            visible: Whether to show or hide the widget
        """
        self.style.visibility = 'visible' if visible else 'hidden'

