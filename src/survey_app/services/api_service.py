"""API service for HTTP client abstraction."""
import requests


class APIService:
    """HTTP client for backend API calls."""

    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url.rstrip('/')

    def get(self, endpoint, **kwargs):
        """GET request."""
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, **kwargs)

    def post(self, endpoint, **kwargs):
        """POST request."""
        url = f"{self.base_url}{endpoint}"
        return requests.post(url, **kwargs)

    def put(self, endpoint, **kwargs):
        """PUT request."""
        url = f"{self.base_url}{endpoint}"
        return requests.put(url, **kwargs)

    def delete(self, endpoint, **kwargs):
        """DELETE request."""
        url = f"{self.base_url}{endpoint}"
        return requests.delete(url, **kwargs)