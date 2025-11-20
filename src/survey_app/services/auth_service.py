import json
import os
import requests
from pathlib import Path
from appdirs import user_data_dir

class AuthService:
    def __init__(self, api_base_url):
        self.api_base_url = api_base_url
        self.token = None
        self.user = None
        self.data_dir = Path(user_data_dir("survey_app", "keith"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.data_dir / "auth_token.json"
        self._load_token()

    def _load_token(self):
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('token')
                    self.user = data.get('user')
            except Exception:
                pass

    def _save_token(self):
        with open(self.token_file, 'w') as f:
            json.dump({'token': self.token, 'user': self.user}, f)

    def login(self, username, password):
        try:
            resp = requests.post(f"{self.api_base_url}/api/auth/login", json={
                'username': username,
                'password': password
            }, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                self.token = data['token']
                self.user = data['user']
                self._save_token()
                return True, None
            else:
                return False, resp.json().get('error', 'Login failed')
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def register(self, username, email, password):
        try:
            resp = requests.post(f"{self.api_base_url}/api/auth/register", json={
                'username': username,
                'email': email,
                'password': password
            }, timeout=10)

            if resp.status_code == 201:
                return True, None
            else:
                return False, resp.json().get('error', 'Registration failed')
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def logout(self):
        if self.token:
            try:
                requests.post(f"{self.api_base_url}/api/auth/logout", headers=self.get_headers(), timeout=5)
            except Exception:
                pass
        self.token = None
        self.user = None
        if self.token_file.exists():
            os.remove(self.token_file)

    def get_headers(self):
        if self.token:
            return {'Authorization': f'Bearer {self.token}'}
        return {}

    def is_authenticated(self):
        return self.token is not None
