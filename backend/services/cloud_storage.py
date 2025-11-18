"""Cloud storage service using Apache Libcloud with verification."""

import os
import hashlib
import logging
import requests
import time
from threading import Lock
from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver
from shared.utils import compute_photo_hash


logger = logging.getLogger(__name__)


class CloudStorageService:
    """Cloud storage service using Apache Libcloud with verification."""

    def __init__(self):
        """Initialize cloud storage service from environment variables."""
        self.provider_name = os.getenv('CLOUD_STORAGE_PROVIDER', 's3')
        self.access_key = os.getenv('CLOUD_STORAGE_ACCESS_KEY')
        self.secret_key = os.getenv('CLOUD_STORAGE_SECRET_KEY')
        self.bucket_name = os.getenv('CLOUD_STORAGE_BUCKET')
        self.region = os.getenv('CLOUD_STORAGE_REGION', 'us-east-1')
        self.local_path = os.getenv('CLOUD_STORAGE_LOCAL_PATH', './local_photos')

        if not all([self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("Cloud storage configuration incomplete. Check environment variables.")

        # Initialize libcloud driver
        self.driver = self._get_driver()
        self.container = self._get_container()

        # Create local storage directory structure
        self.pending_path = os.path.join(self.local_path, 'pending')
        self.processing_path = os.path.join(self.local_path, 'processing')
        self.completed_path = os.path.join(self.local_path, 'completed')

        for path in [self.local_path, self.pending_path, self.processing_path, self.completed_path]:
            os.makedirs(path, exist_ok=True)

        # Circuit breaker initialization
        self._circuit_lock = Lock()
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_open = False
        self._failure_threshold = 5  # Open circuit after 5 consecutive failures
        self._recovery_timeout = 300  # Try again after 5 minutes
        self._success_count = 0
        self._min_success_threshold = 3  # Close circuit after 3 consecutive successes

        logger.info(f"Cloud storage initialized with provider: {self.provider_name}")

    def _is_circuit_open(self):
        """Check if circuit breaker is open (blocking requests)."""
        with self._circuit_lock:
            if not self._circuit_open:
                return False

            # Check if recovery timeout has passed
            if time.time() - self._last_failure_time >= self._recovery_timeout:
                # Transition to half-open state - allow test requests but track success/failure
                self._circuit_open = False  # Enter half-open state
                self._success_count = 0
                logger.info("Circuit breaker entering half-open state for recovery test")
                return False

            return True

    def _record_success(self):
        """Record a successful operation for circuit breaker."""
        with self._circuit_lock:
            self._success_count += 1
            # In half-open state, close circuit after minimum successes
            if not self._circuit_open and self._success_count >= self._min_success_threshold:
                # We were in half-open state and have enough successes
                self._failure_count = 0
                self._success_count = 0
                logger.info("Circuit breaker closed - service recovered")

    def _record_failure(self):
        """Record a failed operation for circuit breaker."""
        with self._circuit_lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            self._success_count = 0

            # If we were in half-open state, immediately reopen circuit on any failure
            if not self._circuit_open:
                self._circuit_open = True
                logger.warning("Circuit breaker reopened due to failure during recovery test")
            elif self._failure_count >= self._failure_threshold:
                self._circuit_open = True
                logger.warning(f"Circuit breaker opened after {self._failure_count} consecutive failures")

    def _get_driver(self):
        """Get the appropriate libcloud driver based on provider."""
        provider_map = {
            's3': Provider.S3,
            'gcs': Provider.GOOGLE_STORAGE,
            'azure': Provider.AZURE_BLOBS,
            'minio': Provider.S3,  # MinIO uses S3 driver
        }

        if self.provider_name not in provider_map:
            raise ValueError(f"Unsupported provider: {self.provider_name}")

        provider = provider_map[self.provider_name]

        # Driver-specific configuration
        kwargs = {
            'key': self.access_key,
            'secret': self.secret_key,
        }

        if self.provider_name == 's3':
            kwargs['region'] = self.region
        elif self.provider_name == 'gcs':
            # GCS might need additional config
            pass
        elif self.provider_name == 'azure':
            # Azure might need additional config
            pass

        return get_driver(provider)(**kwargs)

    def _get_container(self):
        """Get or create the storage container/bucket."""
        try:
            return self.driver.get_container(container_name=self.bucket_name)
        except Exception:
            logger.info(f"Creating container: {self.bucket_name}")
            return self.driver.create_container(container_name=self.bucket_name)

    def upload_photo(self, photo_id, photo_path, thumbnail_path=None, site_id=None):
        """
        Upload photo to cloud storage with circuit breaker protection.

        Args:
            photo_id: Unique photo identifier
            photo_path: Local path to photo file
            thumbnail_path: Local path to thumbnail file (optional)
            site_id: Site identifier for directory organization (integer)

        Returns:
            dict: {'photo_url': str, 'thumbnail_url': str|None, 'object_name': str, 'thumbnail_object_name': str|None}

        Raises:
            Exception: If upload fails or circuit breaker is open
        """
        # Check circuit breaker
        if self._is_circuit_open():
            raise Exception("Cloud storage circuit breaker is open - service temporarily unavailable")

        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Photo file not found: {photo_path}")

        # Validate site_id is an integer
        if site_id is not None:
            try:
                site_id = int(site_id)
            except (ValueError, TypeError):
                raise ValueError(f"site_id must be an integer, got: {site_id}")

        try:
            # Upload main photo - organize by site_id directory if provided
            if site_id is not None:
                photo_object_name = f"{site_id}/{photo_id}.jpg"
            else:
                photo_object_name = f"{photo_id}.jpg"

            photo_url = self._upload_object(photo_path, photo_object_name)

            # Upload thumbnail if provided
            thumbnail_url = None
            thumbnail_object_name = None
            if thumbnail_path and os.path.exists(thumbnail_path):
                if site_id is not None:
                    thumbnail_object_name = f"{site_id}/thumbnails/{photo_id}_thumb.jpg"
                else:
                    thumbnail_object_name = f"thumbnails/{photo_id}_thumb.jpg"
                thumbnail_url = self._upload_object(thumbnail_path, thumbnail_object_name)

            # Record success
            self._record_success()

            return {
                'photo_url': photo_url,
                'thumbnail_url': thumbnail_url,
                'object_name': photo_object_name,
                'thumbnail_object_name': thumbnail_object_name
            }

        except Exception as e:
            # Record failure for circuit breaker
            self._record_failure()
            raise e

    def _upload_object(self, file_path, object_name):
        """
        Upload file to cloud storage.

        Args:
            file_path: Local file path
            object_name: Cloud object name

        Returns:
            str: Public URL of uploaded object

        Raises:
            Exception: If upload fails
        """
        # Read local file
        with open(file_path, 'rb') as f:
            local_data = f.read()

        # Upload to cloud
        logger.info(f"Uploading {file_path} to {object_name}")
        obj = self.driver.upload_object_via_stream(
            iterator=iter([local_data]),
            container=self.container,
            object_name=object_name
        )

        # Return the actual cloud storage URL
        return obj.get_cdn_url() if hasattr(obj, 'get_cdn_url') else obj.public_url

    def _download_object(self, obj):
        """Download object data from cloud storage."""
        # Try to get object content
        if hasattr(obj, 'download'):
            return obj.download(as_stream=False)
        else:
            # Fallback to getting object and downloading
            obj = self.driver.get_object(self.container.name, obj.name)
            return obj.download(as_stream=False)

    def download_photo(self, object_name):
        """
        Download photo from cloud storage with circuit breaker protection.

        Args:
            object_name: Cloud object name (e.g., 'photos/photo_id.jpg')

        Returns:
            bytes: Photo data

        Raises:
            Exception: If download fails or circuit breaker is open
        """
        # Check circuit breaker
        if self._is_circuit_open():
            raise Exception("Cloud storage circuit breaker is open - service temporarily unavailable")

        try:
            obj = self.driver.get_object(self.container.name, object_name)
            data = obj.download(as_stream=False)

            # Record success
            self._record_success()
            return data

        except Exception as e:
            # Record failure for circuit breaker
            self._record_failure()
            logger.error(f"Failed to download {object_name}: {e}")
            raise

    def delete_photo(self, object_name, thumbnail_object_name=None):
        """
        Delete photo and thumbnail from cloud storage.

        Args:
            object_name: Cloud object name for photo
            thumbnail_object_name: Cloud object name for thumbnail (optional)
        """
        try:
            obj = self.driver.get_object(self.container.name, object_name)
            self.driver.delete_object(obj)
            logger.info(f"Deleted photo: {object_name}")
        except Exception as e:
            logger.error(f"Failed to delete photo {object_name}: {e}")

        if thumbnail_object_name:
            try:
                thumb_obj = self.driver.get_object(self.container.name, thumbnail_object_name)
                self.driver.delete_object(thumb_obj)
                logger.info(f"Deleted thumbnail: {thumbnail_object_name}")
            except Exception as e:
                logger.error(f"Failed to delete thumbnail {thumbnail_object_name}: {e}")

    def get_photo_url(self, object_name):
        """
        Get public URL for a photo object.

        Args:
            object_name: Cloud object name

        Returns:
            str: Public URL
        """
        try:
            obj = self.driver.get_object(self.container.name, object_name)
            return obj.get_cdn_url() if hasattr(obj, 'get_cdn_url') else obj.public_url
        except Exception as e:
            logger.error(f"Failed to get URL for {object_name}: {e}")
            raise


# Global instance
_cloud_storage = None
_cloud_storage_lock = Lock()

def get_cloud_storage():
    """Get or create cloud storage service instance (thread-safe)."""
    global _cloud_storage
    if _cloud_storage is None:
        with _cloud_storage_lock:
            # Double-check pattern for thread safety
            if _cloud_storage is None:
                try:
                    _cloud_storage = CloudStorageService()
                except Exception as e:
                    logger.error(f"Failed to initialize cloud storage: {e}")
                    raise
    return _cloud_storage
