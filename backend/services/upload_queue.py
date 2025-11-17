"""Photo upload queue service for background cloud storage uploads."""

import os
import json
import time
import logging
import threading
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from shared.models import Photo
from .cloud_storage import get_cloud_storage
from shared.utils import generate_thumbnail, compute_photo_hash


logger = logging.getLogger(__name__)


class UploadQueueService:
    """Background service for uploading photos to cloud storage."""

    def __init__(self, db_uri='sqlite:///instance/backend_main.db'):
        """Initialize upload queue service."""
        self.db_uri = db_uri
        self.engine = create_engine(db_uri)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.cloud_storage = get_cloud_storage()
        self.running = False
        self.thread = None
        self.check_interval = 30  # seconds between queue checks

    def start(self):
        """Start the background upload queue processor."""
        if self.running:
            logger.warning("Upload queue service already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self.thread.start()
        logger.info("Upload queue service started")

    def stop(self):
        """Stop the background upload queue processor."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Upload queue service stopped")

    def _process_queue_loop(self):
        """Main processing loop for upload queue."""
        while self.running:
            try:
                self._process_pending_uploads()
            except Exception as e:
                logger.error(f"Error in upload queue processing: {e}")
            time.sleep(self.check_interval)

    def _process_pending_uploads(self):
        """Process all pending photo uploads."""
        session = self.SessionLocal()
        try:
            # Get pending photos
            pending_photos = session.query(Photo).filter_by(upload_status='pending').all()

            for photo in pending_photos:
                try:
                    self._process_single_upload(session, photo)
                except Exception as e:
                    logger.error(f"Failed to upload photo {photo.id}: {e}")
                    # Mark as failed for retry later
                    photo.upload_status = 'failed'
                    session.commit()

        finally:
            session.close()

    def _process_single_upload(self, session, photo):
        """Process upload for a single photo."""
        logger.info(f"Processing upload for photo {photo.id}")

        # Check if local file exists
        local_path = self._get_local_photo_path(photo.id)
        if not os.path.exists(local_path):
            logger.warning(f"Local photo file not found: {local_path}")
            photo.upload_status = 'failed'
            session.commit()
            return

        # Move to processing directory
        processing_path = self._move_to_processing(photo.id)

        try:
            # Generate thumbnail if not exists
            thumbnail_path = self._ensure_thumbnail(processing_path)

            # Upload to cloud with verification - organize by site_id
            result = self.cloud_storage.upload_photo(
                photo_id=photo.id,
                photo_path=processing_path,
                thumbnail_path=thumbnail_path,
                expected_hash=photo.hash_value,
                site_id=photo.site_id
            )

            # Update photo record with cloud URLs
            photo.cloud_url = result['photo_url']
            photo.thumbnail_url = result['thumbnail_url']
            photo.upload_status = 'completed'

            session.commit()

            # Move to completed directory
            self._move_to_completed(photo.id)

            logger.info(f"Successfully uploaded photo {photo.id}")

        except Exception as e:
            # Move back to pending on failure
            self._move_to_pending(photo.id)
            raise e

    def _get_local_photo_path(self, photo_id):
        """Get the local path for a pending photo."""
        return os.path.join(self.cloud_storage.pending_path, f"{photo_id}.jpg")

    def _move_to_processing(self, photo_id):
        """Move photo file to processing directory."""
        pending_path = self._get_local_photo_path(photo_id)
        processing_path = os.path.join(self.cloud_storage.processing_path, f"{photo_id}.jpg")

        if os.path.exists(pending_path):
            os.rename(pending_path, processing_path)
            return processing_path
        else:
            raise FileNotFoundError(f"Pending photo not found: {pending_path}")

    def _move_to_completed(self, photo_id):
        """Move photo file to completed directory."""
        processing_path = os.path.join(self.cloud_storage.processing_path, f"{photo_id}.jpg")
        completed_path = os.path.join(self.cloud_storage.completed_path, f"{photo_id}.jpg")

        if os.path.exists(processing_path):
            os.rename(processing_path, completed_path)

    def _move_to_pending(self, photo_id):
        """Move photo file back to pending directory."""
        processing_path = os.path.join(self.cloud_storage.processing_path, f"{photo_id}.jpg")
        pending_path = self._get_local_photo_path(photo_id)

        if os.path.exists(processing_path):
            os.rename(processing_path, pending_path)

    def _ensure_thumbnail(self, photo_path):
        """Ensure thumbnail exists for photo."""
        thumbnail_path = photo_path.replace('.jpg', '_thumb.jpg')

        if os.path.exists(thumbnail_path):
            return thumbnail_path

        # Generate thumbnail
        try:
            with open(photo_path, 'rb') as f:
                image_data = f.read()

            thumbnail_data = generate_thumbnail(image_data, max_size=200)

            with open(thumbnail_path, 'wb') as f:
                f.write(thumbnail_data)

            return thumbnail_path

        except Exception as e:
            logger.warning(f"Failed to generate thumbnail for {photo_path}: {e}")
            return None

    def queue_photo_for_upload(self, photo_id, photo_data, thumbnail_data=None):
        """
        Queue a photo for upload to cloud storage.

        Args:
            photo_id: Photo identifier
            photo_data: Raw photo bytes
            thumbnail_data: Raw thumbnail bytes (optional)
        """
        try:
            # Save photo data locally
            photo_path = self._get_local_photo_path(photo_id)
            with open(photo_path, 'wb') as f:
                f.write(photo_data)

            # Save thumbnail if provided
            if thumbnail_data:
                thumbnail_path = photo_path.replace('.jpg', '_thumb.jpg')
                with open(thumbnail_path, 'wb') as f:
                    f.write(thumbnail_data)

            logger.info(f"Queued photo {photo_id} for upload")

        except Exception as e:
            logger.error(f"Failed to queue photo {photo_id}: {e}")
            raise


# Global instance
_upload_queue = None

def get_upload_queue(db_uri=None):
    """Get or create upload queue service instance."""
    global _upload_queue
    if _upload_queue is None:
        if db_uri is None:
            # Try to get from environment or use default
            db_uri = os.getenv('DATABASE_URL', 'sqlite:///instance/backend_main.db')
        _upload_queue = UploadQueueService(db_uri)
    return _upload_queue
