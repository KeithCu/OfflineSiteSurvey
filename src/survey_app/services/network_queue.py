"""Network queue service for non-blocking network operations using background threading."""

import threading
import queue
import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable


class NetworkQueue:
    """Background network request queue for non-blocking operations.

    Uses a single background thread to process network requests from a queue,
    with results placed in a result queue for polling by the main thread.
    This avoids cross-thread UI update issues in BeeWare/Toga.
    """

    def __init__(self, max_retries=3, retry_delay=1.0):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Request and result queues
        self.request_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # Track active requests
        self.active_requests: Dict[str, Dict[str, Any]] = {}

        # Background thread
        self.thread = None
        self.running = False

        # Start the background thread
        self.start()

    def start(self):
        """Start the background network processing thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._process_requests, daemon=True)
        self.thread.start()
        self.logger.info("Network queue service started")

    def stop(self):
        """Stop the background network processing thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Network queue service stopped")

    def submit_request(self, operation: str, args: tuple = None, kwargs: dict = None,
                      callback: Callable = None, timeout: float = 30.0) -> str:
        """Submit a network request for background processing.

        Args:
            operation: Name of the operation to perform
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation
            callback: Optional callback function (called on main thread)
            timeout: Request timeout in seconds

        Returns:
            str: Unique request ID for polling results
        """
        request_id = str(uuid.uuid4())

        request = {
            'id': request_id,
            'operation': operation,
            'args': args or (),
            'kwargs': kwargs or {},
            'callback': callback,
            'timeout': timeout,
            'submitted_at': time.time()
        }

        self.active_requests[request_id] = request
        self.request_queue.put(request)

        self.logger.debug(f"Submitted network request {request_id} for operation {operation}")
        return request_id

    def poll_result(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Poll for completion of a network request.

        Args:
            request_id: The request ID returned by submit_request

        Returns:
            dict or None: Result dict if complete, None if still processing
        """
        # Check result queue for this request
        try:
            while True:
                result = self.result_queue.get_nowait()
                if result['request_id'] == request_id:
                    # Remove from active requests
                    self.active_requests.pop(request_id, None)
                    return result
                else:
                    # Put back if not our result
                    self.result_queue.put(result)
                    break
        except queue.Empty:
            pass

        return None

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending network request.

        Args:
            request_id: The request ID to cancel

        Returns:
            bool: True if cancelled, False if not found or already processing
        """
        if request_id in self.active_requests:
            del self.active_requests[request_id]
            self.logger.debug(f"Cancelled network request {request_id}")
            return True
        return False

    def get_active_requests(self) -> list:
        """Get list of currently active request IDs."""
        return list(self.active_requests.keys())

    def _process_requests(self):
        """Background thread main loop for processing network requests."""
        while self.running:
            try:
                # Get next request with timeout
                try:
                    request = self.request_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Check if request was cancelled
                if request['id'] not in self.active_requests:
                    continue

                # Process the request
                result = self._execute_operation(request)

                # Put result in result queue
                result_message = {
                    'request_id': request['id'],
                    'operation': request['operation'],
                    'result': result,
                    'completed_at': time.time()
                }

                self.result_queue.put(result_message)

                # Call callback if provided (on background thread - careful!)
                if request.get('callback') and result.get('success', False):
                    try:
                        request['callback'](result)
                    except Exception as e:
                        self.logger.error(f"Error in callback for request {request['id']}: {e}")

            except Exception as e:
                self.logger.error(f"Error in network queue processing: {e}")

    def _execute_operation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a network operation with retry logic.

        Args:
            request: Request dictionary

        Returns:
            dict: Result with 'success', 'data', and 'error' keys
        """
        operation = request['operation']
        args = request['args']
        kwargs = request['kwargs']
        timeout = request['timeout']

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if operation == 'api_request':
                    return self._execute_api_request(*args, **kwargs)
                elif operation == 'companycam_request':
                    return self._execute_companycam_request(*args, **kwargs)
                elif operation == 'sync_request':
                    return self._execute_sync_request(*args, **kwargs)
                else:
                    return {
                        'success': False,
                        'error': f'Unknown operation: {operation}',
                        'data': None
                    }

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Operation {operation} failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"Operation {operation} failed after {self.max_retries} attempts: {e}")

        return {
            'success': False,
            'error': str(last_exception) if last_exception else 'Unknown error',
            'data': None
        }

    def _execute_api_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Execute an API request."""
        import requests

        # Apply timeout if not specified
        kwargs.setdefault('timeout', 30)

        # Handle file uploads specially - files need to be reopened
        if 'files' in kwargs:
            files = kwargs['files']
            # Reconstruct files dict with file data instead of file objects
            new_files = {}
            for key, file_tuple in files.items():
                if len(file_tuple) == 3:
                    filename, file_data, content_type = file_tuple
                    if hasattr(file_data, 'read'):  # File object
                        file_data = file_data.read()
                    new_files[key] = (filename, file_data, content_type)
                else:
                    new_files[key] = file_tuple
            kwargs['files'] = new_files

        response = requests.request(method, url, **kwargs)
        return {
            'success': response.status_code < 400,
            'data': response,
            'status_code': response.status_code
        }

    def _execute_companycam_request(self, method: str, url: str, headers: dict = None,
                                   data: dict = None, json_data: dict = None,
                                   timeout: float = 30) -> Dict[str, Any]:
        """Execute a CompanyCam API request."""
        import requests

        kwargs = {'timeout': timeout}
        if headers:
            kwargs['headers'] = headers
        if data:
            kwargs['data'] = data
        if json_data:
            kwargs['json'] = json_data

        response = requests.request(method, url, **kwargs)
        return {
            'success': response.status_code < 400,
            'data': response,
            'status_code': response.status_code
        }

    def _execute_sync_request(self, sync_func, *args, **kwargs) -> Dict[str, Any]:
        """Execute a sync operation."""
        try:
            result = sync_func(*args, **kwargs)
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None
            }


# Global instance
_network_queue = None
_network_queue_lock = threading.Lock()


def get_network_queue() -> NetworkQueue:
    """Get or create the global network queue instance (thread-safe)."""
    global _network_queue
    if _network_queue is None:
        with _network_queue_lock:
            if _network_queue is None:
                _network_queue = NetworkQueue()
    return _network_queue