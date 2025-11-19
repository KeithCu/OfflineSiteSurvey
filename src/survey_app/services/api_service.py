"""API service for HTTP client abstraction."""
import requests
import time
import logging


class APIService:
    """HTTP client for backend API calls with error handling and retry logic."""

    def __init__(self, base_url='http://localhost:5000', max_retries=3, retry_delay=1.0, offline_queue=None):
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        self.offline_queue = offline_queue or []

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
                    # Queue offline if this is a write operation
                    if method in ['POST', 'PUT', 'DELETE'] and self.offline_queue is not None:
                        self.logger.info(f"Queueing offline request: {method} {url}")
                        # Extract endpoint from URL
                        endpoint = url.replace(self.base_url, '')
                        self.offline_queue.append({
                            'method': method,
                            'endpoint': endpoint,
                            'kwargs': kwargs,
                            'timestamp': time.time()
                        })
                    last_exception = e

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

    def upload_photo(self, endpoint, photo_path, data=None, timeout=60):
        """Upload a photo file with multipart/form-data."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            with open(photo_path, 'rb') as f:
                files = {'image': (photo_path.split('/')[-1], f, 'image/jpeg')}
                return self._make_request('POST', url, files=files, data=data, timeout=timeout)
        except IOError as e:
            self.logger.error(f"Failed to read photo file {photo_path}: {e}")
            raise
