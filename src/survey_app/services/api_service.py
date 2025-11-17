"""API service for HTTP client abstraction."""
import requests
import time
import logging


class APIService:
    """HTTP client for backend API calls with error handling and retry logic."""

    def __init__(self, base_url='http://localhost:5000', max_retries=3, retry_delay=1.0):
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)

    def _make_request(self, method, url, **kwargs):
        """Make HTTP request with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                # Don't retry on client errors (4xx) except for specific cases
                if response.status_code >= 400 and response.status_code < 500:
                    if response.status_code not in [408, 429]:  # Retry timeout and rate limit
                        return response
                elif response.status_code >= 500:  # Retry server errors
                    pass
                else:
                    return response

                # If we get here, we should retry
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {response.status_code} {response.reason}")
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Request exception (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    raise

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        # This shouldn't happen, but just in case
        raise requests.exceptions.RequestException("All retry attempts failed")

    def get(self, endpoint, **kwargs):
        """GET request with error handling and retry."""
        url = f"{self.base_url}{endpoint}"
        return self._make_request('GET', url, **kwargs)

    def post(self, endpoint, **kwargs):
        """POST request with error handling and retry."""
        url = f"{self.base_url}{endpoint}"
        return self._make_request('POST', url, **kwargs)

    def put(self, endpoint, **kwargs):
        """PUT request with error handling and retry."""
        url = f"{self.base_url}{endpoint}"
        return self._make_request('PUT', url, **kwargs)

    def delete(self, endpoint, **kwargs):
        """DELETE request with error handling and retry."""
        url = f"{self.base_url}{endpoint}"
        return self._make_request('DELETE', url, **kwargs)