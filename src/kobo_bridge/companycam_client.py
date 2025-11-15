import requests
import os
from .models import db, User
from datetime import datetime, timedelta

class CompanyCamClient:
    def __init__(self, user_id='admin'):
        # For this MVP, we hardcode the 'admin' user
        self.user = User.query.filter_by(username=user_id).first()
        self.base_url = 'https://api.companycam.com/v2'
        self.client_id = os.environ.get('COMPANYCAM_CLIENT_ID')
        self.client_secret = os.environ.get('COMPANYCAM_CLIENT_SECRET')

    def _get_headers(self):
        if not self.user or not self.user.companycam_access_token:
            raise Exception("User not authenticated with CompanyCam.")

        # Check if token is expired
        if self.user.companycam_token_expires_at <= datetime.utcnow():
            self.refresh_token()

        return {'Authorization': f'Bearer {self.user.companycam_access_token}'}

    def refresh_token(self):
        print("Refreshing CompanyCam token...")
        url = 'https://app.companycam.com/oauth/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.user.companycam_refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Update user in DB
        self.user.companycam_access_token = token_data['access_token']
        self.user.companycam_refresh_token = token_data['refresh_token']
        expires_in = token_data['expires_in'] - 300 # 5-min buffer
        self.user.companycam_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        db.session.commit()
        print("Token refreshed successfully.")

    def create_project(self, name, address=None):
        url = f"{self.base_url}/projects"
        payload = {'name': name}
        if address:
            payload['address'] = address

        response = requests.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def upload_photo(self, project_id, photo_data, filename, captured_at=None):
        url = f"{self.base_url}/projects/{project_id}/photos"

        # We upload from in-memory data, not a file path
        files = {'photo': (filename, photo_data, 'image/jpeg')}

        # Add metadata if available
        data = {}
        if captured_at:
            data['captured_at'] = captured_at.isoformat()

        response = requests.post(url, files=files, data=data, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
