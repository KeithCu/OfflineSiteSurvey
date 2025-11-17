"""CompanyCam API service for OAuth and data synchronization."""
import requests
import json
import time
import logging
import webbrowser
import urllib.parse
from typing import Optional, Dict, Any


class CompanyCamService:
    """Handles CompanyCam API interactions including OAuth 2.0."""

    BASE_URL = 'https://app.companycam.com'
    API_BASE_URL = 'https://api.companycam.com/v2'

    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(self.__class__.__name__)

        # OAuth configuration (these would be registered with CompanyCam)
        self.client_id = self.config.companycam_client_id or 'your_client_id_here'
        self.redirect_uri = 'mysurveyapp://auth'  # Custom URL scheme

    def is_connected(self) -> bool:
        """Check if we have valid CompanyCam credentials."""
        return bool(self.config.companycam_access_token and self.config.companycam_user_id)

    def start_oauth_flow(self) -> None:
        """Start the OAuth 2.0 authorization flow."""
        auth_url = f"{self.BASE_URL}/oauth/authorize"
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'read write',  # Adjust scopes as needed
            'state': 'survey_app_oauth'  # For CSRF protection
        }

        full_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
        self.logger.info(f"Opening OAuth URL: {full_url}")
        webbrowser.open(full_url)

    def handle_oauth_callback(self, auth_code: str) -> bool:
        """Handle the OAuth callback with authorization code."""
        try:
            # Exchange code for tokens
            token_url = f"{self.BASE_URL}/oauth/token"
            data = {
                'client_id': self.client_id,
                'client_secret': 'your_client_secret_here',  # Would be stored securely
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }

            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self._store_tokens(token_data)
            self.logger.info("OAuth flow completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"OAuth callback failed: {e}")
            return False

    def _store_tokens(self, token_data: Dict[str, Any]) -> None:
        """Store OAuth tokens in configuration."""
        self.config.set('companycam_access_token', token_data.get('access_token', ''))
        self.config.set('companycam_refresh_token', token_data.get('refresh_token', ''))
        self.config.set('companycam_user_id', str(token_data.get('user_id', '')))

    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.config.companycam_refresh_token:
            return False

        try:
            token_url = f"{self.BASE_URL}/oauth/token"
            data = {
                'client_id': self.client_id,
                'client_secret': 'your_client_secret_here',
                'refresh_token': self.config.companycam_refresh_token,
                'grant_type': 'refresh_token'
            }

            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self._store_tokens(token_data)
            self.logger.info("Access token refreshed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            return False

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            'Authorization': f"Bearer {self.config.companycam_access_token}",
            'Content-Type': 'application/json'
        }

    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refreshing if necessary."""
        if not self.config.companycam_access_token:
            return False

        # For now, assume token is valid. In production, you might check expiration
        # and refresh proactively
        return True

    def create_project(self, name: str, description: str = "", address: str = "") -> Optional[Dict[str, Any]]:
        """Create a new CompanyCam project."""
        if not self._ensure_valid_token():
            return None

        try:
            url = f"{self.API_BASE_URL}/projects"
            data = {
                'name': name,
                'description': description,
                'address': address
            }

            response = requests.post(url, json=data, headers=self._get_auth_headers(), timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expired, try refresh
                if self.refresh_access_token():
                    return self.create_project(name, description, address)
            self.logger.error(f"Failed to create project: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to create project: {e}")
            return None

    def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an existing project by name."""
        if not self._ensure_valid_token():
            return None

        try:
            url = f"{self.API_BASE_URL}/projects"
            params = {'query': name}

            response = requests.get(url, params=params, headers=self._get_auth_headers(), timeout=30)
            response.raise_for_status()

            projects = response.json()
            # Return first exact match
            for project in projects:
                if project.get('name', '').strip().lower() == name.strip().lower():
                    return project

            return None

        except Exception as e:
            self.logger.error(f"Failed to search projects: {e}")
            return None

    def upload_photo(self, project_id: str, image_data: bytes, filename: str,
                    description: str = "", latitude: float = None, longitude: float = None) -> Optional[Dict[str, Any]]:
        """Upload a photo to a CompanyCam project."""
        if not self._ensure_valid_token():
            return None

        try:
            url = f"{self.API_BASE_URL}/projects/{project_id}/photos"

            # Prepare multipart form data
            files = {
                'photo': (filename, image_data, 'image/jpeg')
            }

            data = {}
            if description:
                data['description'] = description
            if latitude is not None and longitude is not None:
                data['coordinates'] = f"{latitude},{longitude}"

            headers = {'Authorization': f"Bearer {self.config.companycam_access_token}"}

            response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                if self.refresh_access_token():
                    return self.upload_photo(project_id, image_data, filename, description, latitude, longitude)
            elif e.response.status_code == 429:
                # Rate limited, could implement backoff here
                self.logger.warning("Rate limited by CompanyCam API")
            self.logger.error(f"Failed to upload photo: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to upload photo: {e}")
            return None