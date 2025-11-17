# This is a mock of the toga library, used for running the app in a headless environment
# where the GUI is not available. It allows for testing of the application logic
# without a graphical interface.

class App:
    def __init__(self, name, app_id):
        pass

    def main_loop(self):
        pass

class MainWindow:
    def __init__(self, title):
        pass

    def show(self):
        pass

class Label:
    def __init__(self, text, style=None):
        pass

class Button:
    def __init__(self, text, on_press=None, style=None):
        pass

class TextInput:
    def __init__(self, placeholder='', style=None):
        pass

class Selection:
    def __init__(self, items=[], style=None):
        pass

class ImageView:
    def __init__(self, style=None):
        pass

class Box:
    def __init__(self, children=[], style=None):
        self.style = style if style else Pack()
        for child in children:
            self.add(child)

    def add(self, child):
        pass

class Pack:
    def __init__(self, direction=None, padding=None, font_size=None, color=None, font_weight=None, height=None, visibility=None):
        self.visibility = visibility
        pass

class Image:
    def __init__(self, data=None):
        pass

# Constants
COLUMN = 'column'
ROW = 'row'

class ProgressBar:
    def __init__(self, max=100, value=0, style=None):
        pass

class Location:
    async def current_location(self):
        return type('LocationInfo', (), {'latitude': 0.0, 'longitude': 0.0})()
