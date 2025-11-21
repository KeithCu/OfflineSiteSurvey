import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import requests

class TeamUI:
    def __init__(self, app, on_close):
        self.app = app
        self.on_close = on_close
        self.layout = self.create_layout()
        self.load_team()

    def create_layout(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Header
        header = toga.Box(style=Pack(direction=ROW, padding=(0, 0, 10, 0)))

        back_button = toga.Button("Back", on_press=self.close, style=Pack(padding_right=10))
        header.add(back_button)

        header.add(toga.Label("My Team", style=Pack(font_weight='bold', font_size=16)))

        self.refresh_button = toga.Button("Refresh", on_press=self.load_team_handler, style=Pack(padding_left=10))
        header.add(self.refresh_button)

        main_box.add(header)

        # Member List
        self.member_list = toga.Table(
            headings=['Username', 'Email', 'Role'],
            style=Pack(flex=1, padding=(0, 0, 10, 0))
        )
        main_box.add(self.member_list)

        # Add Member Area
        add_box = toga.Box(style=Pack(direction=COLUMN, padding=10, background_color='#f0f0f0'))
        add_box.add(toga.Label("Add Member to Team", style=Pack(font_weight='bold')))

        input_row = toga.Box(style=Pack(direction=ROW, padding=(5, 0)))
        self.new_username_input = toga.TextInput(placeholder="Username to add", style=Pack(flex=1))
        self.add_button = toga.Button("Add", on_press=self.add_member)

        input_row.add(self.new_username_input)
        input_row.add(self.add_button)
        add_box.add(input_row)

        main_box.add(add_box)

        self.status_label = toga.Label("", style=Pack(color='blue'))
        main_box.add(self.status_label)

        return main_box

    def close(self, widget):
        self.on_close()

    def load_team_handler(self, widget):
        # We need to get current user's team_id first
        if not self.app.auth_service.user:
            return

        team_id = self.app.auth_service.user.get('team_id')
        if not team_id:
            self.status_label.text = "You are not in a team."
            return

        # Submit network request to thread pool
        future = self.app.executor.submit(self._load_team_async, team_id)
        future.add_done_callback(lambda f: self.app.main_window.call_soon(self._on_team_loaded, f))

    def _load_team_async(self, team_id):
        """Load team members in background thread."""
        headers = self.app.auth_service.get_headers()
        api_url = self.app.config.api_base_url
        resp = requests.get(f"{api_url}/api/teams/{team_id}/members", headers=headers, timeout=5)
        return resp

    def _on_team_loaded(self, future):
        """Handle team loading completion on main thread."""
        try:
            resp = future.result()
            if resp.status_code == 200:
                members = resp.json()
                self.member_list.data = [(m['username'], m['email'], m['role']) for m in members]
                self.status_label.text = f"Loaded {len(members)} members."
            else:
                self.status_label.text = f"Failed to load members: {resp.json().get('error')}"
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"

    def add_member(self, widget):
        username = self.new_username_input.value
        if not username:
            self.status_label.text = "Enter a username."
            return

        team_id = self.app.auth_service.user.get('team_id')
        if not team_id:
            self.status_label.text = "Create a team first (Contact Admin)."
            return

        self.add_button.enabled = False
        self.status_label.text = "Adding..."

        # Submit network request to thread pool
        future = self.app.executor.submit(self._add_member_async, team_id, username)
        future.add_done_callback(lambda f: self.app.main_window.call_soon(self._on_member_added, f))

    def _add_member_async(self, team_id, username):
        """Add team member in background thread."""
        headers = self.app.auth_service.get_headers()
        api_url = self.app.config.api_base_url
        resp = requests.post(
            f"{api_url}/api/teams/{team_id}/members",
            json={'username': username},
            headers=headers,
            timeout=10
        )
        return resp

    def _on_member_added(self, future):
        """Handle member addition completion on main thread."""
        self.add_button.enabled = True
        try:
            resp = future.result()
            if resp.status_code == 200:
                self.status_label.text = "User added successfully!"
                self.new_username_input.value = ""
                self.load_team_handler(None)  # Reload team list
            else:
                self.status_label.text = f"Failed: {resp.json().get('error')}"
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"
