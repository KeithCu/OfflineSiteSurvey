"""Project management UI views."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN
from shared.enums import ProjectStatus, PriorityLevel


class ProjectView:
    """View class for project management UI.
    
    Handles all UI construction for project-related windows and dialogs.
    Separates UI concerns from business logic (which is in ProjectHandler).
    """
    
    def __init__(self, handler):
        """Initialize the project view.
        
        Args:
            handler: ProjectHandler instance that handles business logic
        """
        self.handler = handler
        self.app = handler.app
    
    def create_projects_window(self):
        """Create and return the projects management window.
        
        Returns:
            toga.Window: Configured projects window
        """
        projects_window = toga.Window(title="Projects")
        
        projects_label = toga.Label('Available Projects:', style=Pack(padding=(10, 5, 10, 5)))
        self.app.projects_list = toga.Selection(items=['Loading...'], style=Pack(padding=(5, 5, 10, 5)))
        
        # Project status and metadata inputs
        self.app.project_status_selection = toga.Selection(
            items=[s.value for s in ProjectStatus],
            style=Pack(padding=(5, 5, 10, 5))
        )
        self.app.project_client_info_input = toga.TextInput(
            placeholder='Client information',
            style=Pack(padding=(5, 5, 10, 5))
        )
        self.app.project_due_date_input = toga.TextInput(
            placeholder='Due date (YYYY-MM-DD)',
            style=Pack(padding=(5, 5, 10, 5))
        )
        self.app.project_priority_selection = toga.Selection(
            items=[p.value for p in PriorityLevel],
            style=Pack(padding=(5, 5, 10, 5))
        )
        
        load_projects_button = toga.Button('Load Projects', on_press=self.handler.load_projects, style=Pack(padding=(5, 5, 5, 5)))
        select_project_button = toga.Button('Select Project', on_press=lambda w: self.handler.select_project(projects_window), style=Pack(padding=(5, 5, 10, 5)))
        
        new_project_label = toga.Label('Create New Project:', style=Pack(padding=(10, 5, 10, 5)))
        self.app.new_project_name_input = toga.TextInput(placeholder='Project Name', style=Pack(padding=(5, 5, 10, 5)))
        self.app.new_project_description_input = toga.TextInput(placeholder='Project Description', style=Pack(padding=(5, 5, 10, 5)))
        
        # Project metadata fields
        project_status_label = toga.Label('Status:', style=Pack(padding=(5, 5, 5, 5)))
        project_client_label = toga.Label('Client Info:', style=Pack(padding=(5, 5, 5, 5)))
        project_due_date_label = toga.Label('Due Date:', style=Pack(padding=(5, 5, 5, 5)))
        project_priority_label = toga.Label('Priority:', style=Pack(padding=(5, 5, 5, 5)))
        
        create_project_button = toga.Button('Create Project', on_press=self.handler.create_project, style=Pack(padding=(5, 5, 10, 5)))
        
        close_button = toga.Button('Close', on_press=lambda w: projects_window.close(), style=Pack(padding=(5, 5, 10, 5)))
        
        projects_box = toga.Box(
            children=[
                projects_label,
                self.app.projects_list,
                load_projects_button,
                select_project_button,
                new_project_label,
                self.app.new_project_name_input,
                self.app.new_project_description_input,
                project_status_label,
                self.app.project_status_selection,
                project_client_label,
                self.app.project_client_info_input,
                project_due_date_label,
                self.app.project_due_date_input,
                project_priority_label,
                self.app.project_priority_selection,
                create_project_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )
        
        projects_window.content = projects_box
        return projects_window

