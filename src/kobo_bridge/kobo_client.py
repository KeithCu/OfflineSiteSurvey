import requests
import os
import json

class KoboClient:
    def __init__(self):
        self.base_url = os.environ.get('KOBO_API_HOST')
        self.token = os.environ.get('KOBO_API_TOKEN')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json'
        })

    def get_forms(self):
        url = f"{self.base_url}/api/v2/assets/"
        params = {'asset_type': 'survey'}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()['results']

    def get_submissions(self, form_uid, last_sync_time=None):
        url = f"{self.base_url}/api/v2/assets/{form_uid}/data/"
        params = {}
        if last_sync_time:
            # Kobo uses ISO format. Add a 1-second buffer.
            query_time = (last_sync_time).isoformat()
            params['query'] = json.dumps({
                "_submission_time": {"$gt": query_time}
            })

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()['results']

    def download_attachment_in_memory(self, attachment_url):
        # We use a separate session for this, as the auth
        # might be different (e.g., cookies)
        response = requests.get(
            attachment_url,
            headers={'Authorization': f'Token {self.token}'}
        )
        response.raise_for_status()
        return response.content # Return raw bytes
