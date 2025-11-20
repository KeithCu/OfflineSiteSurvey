"""API service for HTTP client abstraction."""
import requests
import time
import logging
from .network_queue import get_network_queue


class APIService:
    """HTTP client for backend API calls with error handling and retry logic.

    Now uses background threading for non-blocking network operations.
    """

    def __init__(self, base_url='http://localhost:5000', max_retries=3, retry_delay=1.0, offline_queue=None, auth_service=None, access_token=None):
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        self.offline_queue = offline_queue or []
        self.network_queue = get_network_queue()
        self.auth_service = auth_service
        self.access_token = access_token

    def _get_auth_headers(self):
        """Get authorization headers for API requests.
        
        Supports both auth_service and access_token approaches.
        auth_service takes precedence if both are provided.
        """
        headers = {}
        # Prefer auth_service if available
        if self.auth_service:
            headers.update(self.auth_service.get_headers())
        elif self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        return headers

    def _merge_headers(self, kwargs):
        """Merge auth headers with any provided headers in kwargs."""
        auth_headers = self._get_auth_headers()
        if not auth_headers:
            return kwargs
        
        # Get existing headers or create new dict
        existing_headers = kwargs.get('headers', {})
        if not isinstance(existing_headers, dict):
            existing_headers = {}
        
        # Merge auth headers with existing headers (auth headers take precedence)
        merged_headers = {**existing_headers, **auth_headers}
        kwargs['headers'] = merged_headers
        return kwargs

    def _make_request(self, method, url, **kwargs):
        """Make HTTP request with retry logic (synchronous - for backward compatibility)."""
        # Merge auth headers with any provided headers
        kwargs = self._merge_headers(kwargs)
        
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

    def submit_request_async(self, method, endpoint, **kwargs):
        """Submit an API request for asynchronous processing.

        Returns a request ID that can be used to poll for completion.
        """
        # Merge auth headers with any provided headers
        kwargs = self._merge_headers(kwargs)
        
        url = f"{self.base_url}{endpoint}"
        return self.network_queue.submit_request(
            operation='api_request',
            args=(method, url),
            kwargs=kwargs,
            timeout=kwargs.get('timeout', 30)
        )

    def poll_request_result(self, request_id):
        """Poll for the result of an asynchronous API request.

        Returns:
            dict or None: {'success': bool, 'response': Response, 'error': str} or None if not complete
        """
        result = self.network_queue.poll_result(request_id)
        if result:
            operation_result = result['result']
            if operation_result['success']:
                return {
                    'success': True,
                    'response': operation_result['data']
                }
            else:
                return {
                    'success': False,
                    'error': operation_result.get('error', 'Unknown error')
                }
        return None

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

    # Asynchronous versions
    def get_async(self, endpoint, **kwargs):
        """Asynchronous GET request - returns request ID for polling."""
        return self.submit_request_async('GET', endpoint, **kwargs)

    def post_async(self, endpoint, **kwargs):
        """Asynchronous POST request - returns request ID for polling."""
        return self.submit_request_async('POST', endpoint, **kwargs)

    def put_async(self, endpoint, **kwargs):
        """Asynchronous PUT request - returns request ID for polling."""
        return self.submit_request_async('PUT', endpoint, **kwargs)

    def delete_async(self, endpoint, **kwargs):
        """Asynchronous DELETE request - returns request ID for polling."""
        return self.submit_request_async('DELETE', endpoint, **kwargs)

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

    def upload_photo_async(self, endpoint, photo_path, data=None, timeout=60):
        """Asynchronous photo upload - returns request ID for polling."""
        try:
            # Read file data for async upload
            with open(photo_path, 'rb') as f:
                file_data = f.read()

            filename = photo_path.split('/')[-1]
            files = {'image': (filename, file_data, 'image/jpeg')}

            kwargs = {
                'files': files,
                'data': data,
                'timeout': timeout
            }

            return self.submit_request_async('POST', endpoint, **kwargs)

        except IOError as e:
            self.logger.error(f"Failed to read photo file {photo_path}: {e}")
            raise
