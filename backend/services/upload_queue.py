"""Photo upload queue service for background cloud storage uploads."""

import os
import json
import time
import logging
import threading
from datetime import datetime
from threading import Lock
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
        self.max_retries = 5  # maximum retry attempts
        self.base_backoff_seconds = 60  # base delay for exponential backoff

        # Thread synchronization
        self._running_lock = Lock()
        self._queue_lock = Lock()

    def start(self):
        """Start the background upload queue processor."""
        with self._running_lock:
            if self.running:
                logger.warning("Upload queue service already running")
                return

            self.running = True
            self.thread = threading.Thread(target=self._process_queue_loop, daemon=True)
            self.thread.start()
            logger.info("Upload queue service started")

    def stop(self):
        """Stop the background upload queue processor."""
        with self._running_lock:
            self.running = False

        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Upload queue service stopped")

    def recover_permanently_failed_uploads(self, photo_ids=None):
        """
        Manually recover permanently failed uploads by resetting their status.

        Args:
            photo_ids: List of photo IDs to recover. If None, recovers all permanently failed uploads.
        """
        session = self.SessionLocal()
        try:
            query = session.query(Photo).filter_by(upload_status='permanently_failed')

            if photo_ids:
                query = query.filter(Photo.id.in_(photo_ids))

            failed_photos = query.all()
            recovered_count = 0

            for photo in failed_photos:
                # Reset status to allow retry
                photo.upload_status = 'failed'
                photo.retry_count = max(0, self.max_retries - 2)  # Allow at least 2 more attempts
                photo.last_retry_at = None  # Allow immediate retry
                logger.info(f"Recovered permanently failed upload for photo {photo.id}")
                recovered_count += 1

            session.commit()
            logger.info(f"Recovered {recovered_count} permanently failed uploads")
            return recovered_count

        except Exception as e:
            session.rollback()
            logger.error(f"Error recovering permanently failed uploads: {e}")
            raise
        finally:
            session.close()

    def _process_queue_loop(self):
        """Main processing loop for upload queue."""
        while True:
            with self._running_lock:
                if not self.running:
                    break

            try:
                self._process_pending_uploads()
            except Exception as e:
                logger.error(f"Error in upload queue processing: {e}")

            time.sleep(self.check_interval)

    def _process_pending_uploads(self):
        """Process all pending and failed photo uploads with retry logic."""
        session = self.SessionLocal()
        try:
            # Get pending photos (never failed before)
            pending_photos = session.query(Photo).filter_by(upload_status='pending').all()

            # Get failed photos that are eligible for retry
            failed_photos = self._get_retryable_failed_photos(session)

            all_photos = pending_photos + failed_photos

            for photo in all_photos:
                try:
                    self._process_single_upload(session, photo)
                except Exception as e:
                    logger.error(f"Failed to upload photo {photo.id}: {e}")
                    self._handle_upload_failure(session, photo, e)

        finally:
            session.close()

    def _get_retryable_failed_photos(self, session):
        """Get failed photos that are eligible for retry based on backoff logic."""
        from datetime import datetime, timedelta
        from shared.models import utc_now
        current_time = utc_now()

        failed_photos = session.query(Photo).filter_by(upload_status='failed').all()
        retryable_photos = []

        for photo in failed_photos:
            if photo.retry_count >= self.max_retries:
                # Max retries exceeded, mark as permanently failed
                photo.upload_status = 'permanently_failed'
                logger.warning(f"Photo {photo.id} exceeded max retries ({self.max_retries}), marking as permanently failed")
                continue

            # Calculate backoff delay (exponential: base * 2^retry_count)
            backoff_seconds = self.base_backoff_seconds * (2 ** photo.retry_count)

            if photo.last_retry_at:
                time_since_last_retry = current_time - photo.last_retry_at
                if time_since_last_retry.total_seconds() < backoff_seconds:
                    # Not enough time has passed, skip this photo
                    continue

            retryable_photos.append(photo)

        # Also check for permanently failed photos that might be retryable after a longer period
        permanently_failed_photos = session.query(Photo).filter_by(upload_status='permanently_failed').all()
        for photo in permanently_failed_photos:
            # Retry permanently failed photos once per day after 24 hours have passed
            if photo.last_retry_at:
                time_since_last_retry = current_time - photo.last_retry_at
                if time_since_last_retry.total_seconds() > 86400:  # 24 hours
                    logger.info(f"Attempting recovery retry for permanently failed photo {photo.id}")
                    # Reset retry count to allow one more attempt
                    photo.retry_count = self.max_retries - 1
                    photo.upload_status = 'failed'
                    retryable_photos.append(photo)

        return retryable_photos

    def _handle_upload_failure(self, session, photo, error):
        """Handle upload failure with retry tracking."""
        from datetime import datetime
        photo.retry_count += 1
        from shared.models import utc_now
        photo.last_retry_at = utc_now()

        if photo.retry_count >= self.max_retries:
            photo.upload_status = 'permanently_failed'
            logger.error(f"Photo {photo.id} permanently failed after {photo.retry_count} attempts: {error}")
        else:
            photo.upload_status = 'failed'
            logger.warning(f"Photo {photo.id} failed (attempt {photo.retry_count}/{self.max_retries}), will retry later: {error}")

        session.commit()

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

            # Upload to cloud - organize by site_id
            result = self.cloud_storage.upload_photo(
                photo_id=photo.id,
                photo_path=processing_path,
                thumbnail_path=thumbnail_path,
                site_id=photo.site_id
            )

            # Update photo record with cloud URLs
            photo.cloud_url = result['photo_url']
            photo.thumbnail_url = result['thumbnail_url']
            photo.upload_status = 'completed'
            photo.retry_count = 0  # Reset retry count on success
            photo.last_retry_at = None  # Clear last retry time

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
        with self._queue_lock:
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


# Global instance with thread-safe lazy initialization
_upload_queue = None
_upload_queue_lock = Lock()

def get_upload_queue(db_uri=None):
    """Get or create upload queue service instance (thread-safe)."""
    global _upload_queue
    if _upload_queue is None:
        with _upload_queue_lock:
            # Double-check pattern for thread safety
            if _upload_queue is None:
                if db_uri is None:
                    # Try to get from environment or use default
                    db_uri = os.getenv('DATABASE_URL', 'sqlite:///instance/backend_main.db')
                _upload_queue = UploadQueueService(db_uri)
    return _upload_queue
