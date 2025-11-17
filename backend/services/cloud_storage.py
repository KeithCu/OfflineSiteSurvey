"""Cloud storage service using Apache Libcloud with verification."""

import os
import hashlib
import logging
import requests
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

        logger.info(f"Cloud storage initialized with provider: {self.provider_name}")

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

    def upload_photo(self, photo_id, photo_path, thumbnail_path=None, expected_hash=None, site_id=None):
        """
        Upload photo to cloud storage with verification.

        Args:
            photo_id: Unique photo identifier
            photo_path: Local path to photo file
            thumbnail_path: Local path to thumbnail file (optional)
            expected_hash: Expected SHA256 hash of the photo
            site_id: Site identifier for directory organization (integer)

        Returns:
            dict: {'photo_url': str, 'thumbnail_url': str|None, 'object_name': str, 'thumbnail_object_name': str|None}

        Raises:
            Exception: If upload or verification fails
        """
        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Photo file not found: {photo_path}")

        # Validate site_id is an integer
        if site_id is not None:
            try:
                site_id = int(site_id)
            except (ValueError, TypeError):
                raise ValueError(f"site_id must be an integer, got: {site_id}")

        # Upload main photo - organize by site_id directory if provided
        if site_id is not None:
            photo_object_name = f"{site_id}/{photo_id}.jpg"
        else:
            photo_object_name = f"{photo_id}.jpg"

        photo_url = self._upload_and_verify(photo_path, photo_object_name, expected_hash)

        # Upload thumbnail if provided
        thumbnail_url = None
        thumbnail_object_name = None
        if thumbnail_path and os.path.exists(thumbnail_path):
            if site_id is not None:
                thumbnail_object_name = f"{site_id}/thumbnails/{photo_id}_thumb.jpg"
            else:
                thumbnail_object_name = f"thumbnails/{photo_id}_thumb.jpg"
            thumbnail_url = self._upload_and_verify(thumbnail_path, thumbnail_object_name)

        return {
            'photo_url': photo_url,
            'thumbnail_url': thumbnail_url,
            'object_name': photo_object_name,
            'thumbnail_object_name': thumbnail_object_name
        }

    def _upload_and_verify(self, file_path, object_name, expected_hash=None):
        """
        Upload file to cloud and verify it matches expected hash.

        Args:
            file_path: Local file path
            object_name: Cloud object name
            expected_hash: Expected SHA256 hash (if None, computed from local file)

        Returns:
            str: Public URL of uploaded object

        Raises:
            Exception: If verification fails
        """
        # Read local file and compute hash if not provided
        with open(file_path, 'rb') as f:
            local_data = f.read()

        if expected_hash is None:
            expected_hash = compute_photo_hash(local_data)

        # Upload to cloud
        logger.info(f"Uploading {file_path} to {object_name}")
        obj = self.driver.upload_object_via_stream(
            iterator=iter([local_data]),
            container=self.container,
            object_name=object_name
        )

        # Verify upload by downloading and checking hash
        logger.info(f"Verifying upload for {object_name}")
        try:
            downloaded_data = self._download_object(obj)
            downloaded_hash = compute_photo_hash(downloaded_data)

            if downloaded_hash != expected_hash:
                # Delete the uploaded object since verification failed
                self.driver.delete_object(obj)
                raise ValueError(f"Upload verification failed for {object_name}. "
                               f"Expected hash: {expected_hash}, "
                               f"Downloaded hash: {downloaded_hash}")

            logger.info(f"Upload verification successful for {object_name}")
            return obj.get_cdn_url() if hasattr(obj, 'get_cdn_url') else obj.public_url

        except Exception as e:
            # Clean up on verification failure
            try:
                self.driver.delete_object(obj)
            except Exception:
                pass  # Ignore cleanup errors
            raise e

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
        Download photo from cloud storage.

        Args:
            object_name: Cloud object name (e.g., 'photos/photo_id.jpg')

        Returns:
            bytes: Photo data
        """
        try:
            obj = self.driver.get_object(self.container.name, object_name)
            return obj.download(as_stream=False)
        except Exception as e:
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

def get_cloud_storage():
    """Get or create cloud storage service instance."""
    global _cloud_storage
    if _cloud_storage is None:
        try:
            _cloud_storage = CloudStorageService()
        except Exception as e:
            logger.error(f"Failed to initialize cloud storage: {e}")
            raise
    return _cloud_storage
