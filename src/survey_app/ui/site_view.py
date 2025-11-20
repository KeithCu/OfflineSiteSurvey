"""Site management UI views."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN


class SiteView:
    """View class for site management UI.
    
    Handles all UI construction for site-related windows and dialogs.
    Separates UI concerns from business logic (which is in SiteHandler).
    """
    
    def __init__(self, handler):
        """Initialize the site view.
        
        Args:
            handler: SiteHandler instance that handles business logic
        """
        self.handler = handler
        self.app = handler.app
    
    def create_sites_window(self):
        """Create and return the sites management window.
        
        Returns:
            toga.Window: Configured sites window
        """
        sites_window = toga.Window(title="Sites")
        
        sites_label = toga.Label('Available Sites:', style=Pack(padding=(10, 5, 10, 5)))
        self.app.sites_list = toga.Selection(items=['Loading...'], style=Pack(padding=(5, 5, 10, 5)))
        
        load_sites_button = toga.Button('Load Sites', on_press=self.handler.load_sites, style=Pack(padding=(5, 5, 5, 5)))
        select_site_button = toga.Button('Select Site', on_press=lambda w: self.handler.select_site(sites_window), style=Pack(padding=(5, 5, 10, 5)))
        
        new_site_label = toga.Label('Create New Site:', style=Pack(padding=(10, 5, 10, 5)))
        self.app.new_site_name_input = toga.TextInput(placeholder='Site Name', style=Pack(padding=(5, 5, 10, 5)))
        self.app.new_site_address_input = toga.TextInput(placeholder='Site Address', style=Pack(padding=(5, 5, 10, 5)))
        self.app.new_site_notes_input = toga.TextInput(placeholder='Site Notes', style=Pack(padding=(5, 5, 10, 5)))
        create_site_button = toga.Button('Create Site', on_press=self.handler.create_site, style=Pack(padding=(5, 5, 10, 5)))
        
        close_button = toga.Button('Close', on_press=lambda w: sites_window.close(), style=Pack(padding=(5, 5, 10, 5)))
        
        sites_box = toga.Box(
            children=[
                sites_label,
                self.app.sites_list,
                load_sites_button,
                select_site_button,
                new_site_label,
                self.app.new_site_name_input,
                self.app.new_site_address_input,
                self.app.new_site_notes_input,
                create_site_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )
        
        sites_window.content = sites_box
        return sites_window

