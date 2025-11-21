import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import threading

class LoginUI:
    def __init__(self, app, on_login_success):
        self.app = app
        self.on_login_success = on_login_success
        self.layout = self.create_layout()

    def create_layout(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        main_box.add(toga.Label("Site Survey App", style=Pack(padding=(0, 0, 20, 0), font_size=20, font_weight='bold', text_align='center')))

        self.username_input = toga.TextInput(placeholder="Username", style=Pack(padding=(0, 0, 10, 0)))
        self.password_input = toga.PasswordInput(placeholder="Password", style=Pack(padding=(0, 0, 20, 0)))

        self.login_button = toga.Button("Login", on_press=self.login, style=Pack(padding=(0, 0, 10, 0)))
        self.register_button = toga.Button("Register New Account", on_press=self.show_register, style=Pack(padding=(0, 0, 10, 0)))

        self.status_label = toga.Label("", style=Pack(color='red', text_align='center'))

        main_box.add(self.username_input)
        main_box.add(self.password_input)
        main_box.add(self.login_button)
        main_box.add(self.register_button)
        main_box.add(self.status_label)

        return main_box

    def login(self, widget):
        username = self.username_input.value
        password = self.password_input.value

        if not username or not password:
            self.status_label.text = "Please enter username and password"
            return

        self.status_label.text = "Logging in..."
        self.login_button.enabled = False

        # Submit login to thread pool
        future = self.app.executor.submit(self._login_async, username, password)
        future.add_done_callback(lambda f: self.app.main_window.call_soon(self._on_login_complete, f))

    def _login_async(self, username, password):
        """Perform login in background thread."""
        return self.app.auth_service.login(username, password)

    def _on_login_complete(self, future):
        """Handle login completion on main thread."""
        self.login_button.enabled = True
        try:
            success, error = future.result()
            if success:
                self.on_login_success()
            else:
                self.status_label.text = error
        except Exception as e:
            self.status_label.text = f"Login error: {str(e)}"

    def show_register(self, widget):
        # Switch content to RegistrationUI
        self.registration_ui = RegistrationUI(self.app, self)
        self.app.main_window.content = self.registration_ui.layout

class RegistrationUI:
    def __init__(self, app, login_ui):
        self.app = app
        self.login_ui = login_ui
        self.layout = self.create_layout()

    def create_layout(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        main_box.add(toga.Label("Register", style=Pack(padding=(0, 0, 20, 0), font_size=20, font_weight='bold', text_align='center')))

        self.username_input = toga.TextInput(placeholder="Username", style=Pack(padding=(0, 0, 10, 0)))
        self.email_input = toga.TextInput(placeholder="Email", style=Pack(padding=(0, 0, 10, 0)))
        self.password_input = toga.PasswordInput(placeholder="Password", style=Pack(padding=(0, 0, 10, 0)))
        self.confirm_input = toga.PasswordInput(placeholder="Confirm Password", style=Pack(padding=(0, 0, 20, 0)))

        self.register_button = toga.Button("Register", on_press=self.register, style=Pack(padding=(0, 0, 10, 0)))
        self.cancel_button = toga.Button("Cancel", on_press=self.cancel, style=Pack(padding=(0, 0, 10, 0)))

        self.status_label = toga.Label("", style=Pack(color='red', text_align='center'))

        main_box.add(self.username_input)
        main_box.add(self.email_input)
        main_box.add(self.password_input)
        main_box.add(self.confirm_input)
        main_box.add(self.register_button)
        main_box.add(self.cancel_button)
        main_box.add(self.status_label)

        return main_box

    def cancel(self, widget):
        self.app.main_window.content = self.login_ui.layout

    def register(self, widget):
        username = self.username_input.value
        email = self.email_input.value
        password = self.password_input.value
        confirm = self.confirm_input.value

        if not username or not email or not password:
            self.status_label.text = "All fields are required"
            return

        if password != confirm:
            self.status_label.text = "Passwords do not match"
            return

        self.status_label.text = "Registering..."
        self.register_button.enabled = False

        # Submit registration to thread pool
        future = self.app.executor.submit(self._register_async, username, email, password)
        future.add_done_callback(lambda f: self.app.main_window.call_soon(self._on_register_complete, f))

    def _register_async(self, username, email, password):
        """Perform registration in background thread."""
        return self.app.auth_service.register(username, email, password)

    def _on_register_complete(self, future):
        """Handle registration completion on main thread."""
        self.register_button.enabled = True
        try:
            success, error = future.result()
            if success:
                self.app.main_window.info_dialog("Success", "Registration successful! Please login.")
                self.app.main_window.content = self.login_ui.layout
            else:
                self.status_label.text = error
        except Exception as e:
            self.status_label.text = f"Registration error: {str(e)}"
