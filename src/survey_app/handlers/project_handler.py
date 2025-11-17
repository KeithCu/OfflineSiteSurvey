"""Project management handlers for SurveyApp."""
import toga


class ProjectHandler:
    """Handles project-related operations."""

    def __init__(self, app):
        self.app = app

    def show_projects_ui(self, widget):
        """Show projects management UI"""
        projects_window = toga.Window(title="Projects")

        projects_label = toga.Label('Available Projects:', style=toga.Pack(padding=(10, 5, 10, 5)))
        self.app.projects_list = toga.Selection(items=['Loading...'], style=toga.Pack(padding=(5, 5, 10, 5)))

        # Project status and metadata inputs
        self.app.project_status_selection = toga.Selection(
            items=[s.value for s in self.app.enums.ProjectStatus],
            style=toga.Pack(padding=(5, 5, 10, 5))
        )
        self.app.project_client_info_input = toga.TextInput(
            placeholder='Client information',
            style=toga.Pack(padding=(5, 5, 10, 5))
        )
        self.app.project_due_date_input = toga.TextInput(
            placeholder='Due date (YYYY-MM-DD)',
            style=toga.Pack(padding=(5, 5, 10, 5))
        )
        self.app.project_priority_selection = toga.Selection(
            items=[p.value for p in self.app.enums.PriorityLevel],
            style=toga.Pack(padding=(5, 5, 10, 5))
        )

        load_projects_button = toga.Button('Load Projects', on_press=self.load_projects, style=toga.Pack(padding=(5, 5, 5, 5)))
        select_project_button = toga.Button('Select Project', on_press=lambda w: self.select_project(projects_window), style=toga.Pack(padding=(5, 5, 10, 5)))

        new_project_label = toga.Label('Create New Project:', style=toga.Pack(padding=(10, 5, 10, 5)))
        self.app.new_project_name_input = toga.TextInput(placeholder='Project Name', style=toga.Pack(padding=(5, 5, 10, 5)))
        self.app.new_project_description_input = toga.TextInput(placeholder='Project Description', style=toga.Pack(padding=(5, 5, 10, 5)))

        # Project metadata fields
        project_status_label = toga.Label('Status:', style=toga.Pack(padding=(5, 5, 5, 5)))
        project_client_label = toga.Label('Client Info:', style=toga.Pack(padding=(5, 5, 5, 5)))
        project_due_date_label = toga.Label('Due Date:', style=toga.Pack(padding=(5, 5, 5, 5)))
        project_priority_label = toga.Label('Priority:', style=toga.Pack(padding=(5, 5, 5, 5)))

        create_project_button = toga.Button('Create Project', on_press=self.create_project, style=toga.Pack(padding=(5, 5, 10, 5)))

        close_button = toga.Button('Close', on_press=lambda w: projects_window.close(), style=toga.Pack(padding=(5, 5, 10, 5)))

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
            style=toga.Pack(direction=toga.COLUMN, padding=20)
        )

        projects_window.content = projects_box
        projects_window.show()
        self.load_projects(None)

    def load_projects(self, widget):
        """Load projects from local db"""
        projects = self.app.db.get_projects()
        if projects:
            project_names = [f"{p.id}: {p.name}" for p in projects]
            self.app.projects_list.items = project_names
            self.app.projects_data = projects
            self.app.status_label.text = f"Loaded {len(projects)} projects"
        else:
            self.app.projects_list.items = ['No projects available']

    def create_project(self, widget):
        """Create a new project"""
        project_name = self.app.new_project_name_input.value
        project_description = self.app.new_project_description_input.value
        if project_name:
            project_data = {
                'name': project_name,
                'description': project_description,
                'status': self.app.project_status_selection.value or self.app.enums.ProjectStatus.DRAFT.value,
                'client_info': self.app.project_client_info_input.value,
                'due_date': self.app.project_due_date_input.value,
                'priority': self.app.project_priority_selection.value or self.app.enums.PriorityLevel.MEDIUM.value
            }
            self.app.db.save_project(project_data)
            self.app.status_label.text = f"Created project: {project_name}"
            self.load_projects(None)
        else:
            self.app.status_label.text = "Please enter a project name"

    def select_project(self, projects_window):
        if self.app.projects_list.value and hasattr(self.app, 'projects_data'):
            project_id = int(self.app.projects_list.value.split(':')[0])
            self.app.current_project = next((p for p in self.app.projects_data if p.id == project_id), None)
            if self.app.current_project:
                self.app.site_handler.load_sites_for_project(self.app.current_project.id)
                projects_window.close()
            else:
                self.app.status_label.text = "Project not found"
        else:
            self.app.status_label.text = "Please select a project"