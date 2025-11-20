"""Site management handlers for SurveyApp."""
import toga
import logging


class SiteHandler:
    """Handles site-related operations."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(self.__class__.__name__)
        from ..ui.site_view import SiteView
        self.view = SiteView(self)

    def show_sites_ui(self, widget):
        """Show sites management UI"""
        sites_window = self.view.create_sites_window()

        sites_label = toga.Label('Available Sites:', style=toga.Pack(padding=(10, 5, 10, 5)))
        self.app.sites_list = toga.Selection(items=['Loading...'], style=toga.Pack(padding=(5, 5, 10, 5)))

        load_sites_button = toga.Button('Load Sites', on_press=self.load_sites, style=toga.Pack(padding=(5, 5, 5, 5)))
        select_site_button = toga.Button('Select Site', on_press=lambda w: self.select_site(sites_window), style=toga.Pack(padding=(5, 5, 10, 5)))

        new_site_label = toga.Label('Create New Site:', style=toga.Pack(padding=(10, 5, 10, 5)))
        self.app.new_site_name_input = toga.TextInput(placeholder='Site Name', style=toga.Pack(padding=(5, 5, 10, 5)))
        self.app.new_site_address_input = toga.TextInput(placeholder='Site Address', style=toga.Pack(padding=(5, 5, 10, 5)))
        self.app.new_site_notes_input = toga.TextInput(placeholder='Site Notes', style=toga.Pack(padding=(5, 5, 10, 5)))
        create_site_button = toga.Button('Create Site', on_press=self.create_site, style=toga.Pack(padding=(5, 5, 10, 5)))

        close_button = toga.Button('Close', on_press=lambda w: sites_window.close(), style=toga.Pack(padding=(5, 5, 10, 5)))

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
            style=toga.Pack(direction=toga.COLUMN, padding=20)
        )

        sites_window.show()
        self.load_sites(None)

    def load_sites(self, widget):
        """Load sites from local db"""
        sites = self.app.db.get_sites()
        if sites:
            site_names = [f"{s.id}: {s.name}" for s in sites]
            self.app.sites_list.items = site_names
            self.app.state.sites_data = sites
            self.app.ui_manager.status_label.text = f"Loaded {len(sites)} sites"
        else:
            self.app.sites_list.items = ['No sites available']

    def create_site(self, widget):
        """Create a new site"""
        site_name = self.app.new_site_name_input.value
        site_address = self.app.new_site_address_input.value
        if site_name:
            site_data = {
                'name': site_name,
                'address': site_address,
                'notes': self.app.new_site_notes_input.value
            }
            if self.app.state.current_project:
                site_data['project_id'] = self.app.state.current_project.id
            self.app.db.save_site(site_data)
            self.app.ui_manager.status_label.text = f"Created site: {site_name}"
            self.load_sites(None)
            if self.app.state.current_project:
                self.load_sites_for_project(self.app.state.current_project.id)
        else:
            self.app.ui_manager.status_label.text = "Please enter a site name"

    def select_site(self, sites_window):
        if self.app.sites_list.value and hasattr(self.app.state, 'sites_data'):
            site_id = int(self.app.sites_list.value.split(':')[0])
            self.app.state.current_site = next((s for s in self.app.state.sites_data if s.id == site_id), None)
            if self.app.state.current_site:
                self.app.survey_handler.load_surveys_for_site(self.app.state.current_site.id)
                sites_window.close()
            else:
                self.app.ui_manager.status_label.text = "Site not found"
        else:
            self.app.ui_manager.status_label.text = "Please select a site"

    def load_sites_for_project(self, project_id):
        """Load sites for the selected project"""
        sites = self.app.db.get_sites_for_project(project_id)
        if sites:
            site_names = [f"{s.id}: {s.name}" for s in sites]
            self.app.ui_manager.survey_selection.items = ['Select a site first...'] + site_names
            self.app.ui_manager.status_label.text = f"Loaded {len(sites)} sites for project {self.app.state.current_project.name}"
        else:
            self.app.ui_manager.survey_selection.items = ['Select a site first...']
            self.app.ui_manager.status_label.text = f"No sites available for project {self.app.state.current_project.name}"