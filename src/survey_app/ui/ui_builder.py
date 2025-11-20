"""UI Builder utility for reducing Toga boilerplate."""
import toga
from toga.style import Pack


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
    from toga.style.pack import COLUMN
    
    label = create_label(label_text)
    text_input = create_text_input(placeholder, on_change=on_change)
    
    box_style = Pack(direction=COLUMN)
    if style_overrides:
        box_style.update(**style_overrides)
    
    return toga.Box(
        children=[label, text_input],
        style=box_style
    )

