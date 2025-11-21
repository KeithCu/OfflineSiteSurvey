"""Photo upload queue service for background cloud storage uploads."""

import json
import os
import time
import logging
import threading
import shutil
import queue
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, or_
from shared.models import Photo, now
from .cloud_storage import get_cloud_storage
from shared.utils import generate_thumbnail, compute_photo_hash, CorruptedImageError
from ..utils import safe_db_transaction


logger = logging.getLogger(__name__)


@contextmanager
def session_scope(session_factory):
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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

        # Thread-safe queue for coordinating worker thread
        self._work_queue = queue.Queue()
        self._stop_event = threading.Event()

    def start(self):
        """Start the background upload queue processor."""
        if self.running:
            logger.warning("Upload queue service already running")
            return

        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self.thread.start()
        logger.info("Upload queue service started")

    def stop(self):
        """Stop the background upload queue processor."""
        self.running = False
        self._stop_event.set()
        # Put a sentinel value to wake up the queue if it's waiting
        try:
            self._work_queue.put_nowait(None)
        except queue.Full:
            pass

        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Upload queue service stopped")

    @safe_db_transaction("recover permanently failed uploads")
    def recover_permanently_failed_uploads(self, photo_ids=None):
        """
        Manually recover permanently failed uploads by resetting their status.

        Args:
            photo_ids: List of photo IDs to recover. If None, recovers all permanently failed uploads.
        """
        with session_scope(self.SessionLocal) as session:
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

            logger.info(f"Recovered {recovered_count} permanently failed uploads")
            return recovered_count

    def _process_queue_loop(self):
        """Main processing loop for upload queue."""
        while not self._stop_event.is_set():
            try:
                # Process pending uploads from database
                self._process_pending_uploads()

                # Wait for next check interval or stop event
                # Use queue timeout to allow periodic checks even when queue is empty
                try:
                    item = self._work_queue.get(timeout=self.check_interval)
                    if item is None:  # Sentinel value for shutdown
                        break
                    # Process the queued item (photo_id)
                    self._process_queued_photo(item)
                except queue.Empty:
                    # Timeout expired, continue loop to check database again
                    continue

            except Exception as e:
                logger.error(f"Error in upload queue processing: {e}")
                # Continue processing even on errors
                if not self._stop_event.wait(timeout=1):
                    continue
                break

    def _process_pending_uploads(self):
        """Process all pending and failed photo uploads with retry logic."""
        with session_scope(self.SessionLocal) as session:
            # Check for stale pending photos (pending for too long without retry tracking)
            self._handle_stale_pending_photos(session)

            # Get pending photos (never failed before) with row locking to prevent race conditions
            pending_photos = session.query(Photo).filter_by(upload_status='pending').with_for_update().all()

            # Get failed photos that are eligible for retry
            failed_photos = self._get_retryable_failed_photos(session)

            all_photos = pending_photos + failed_photos

            for photo in all_photos:
                try:
                    self._process_single_upload(session, photo)
                except Exception as e:
                    logger.error(f"Failed to upload photo {photo.id}: {e}")
                    self._handle_upload_failure(session, photo, e)

    def _get_retryable_failed_photos(self, session):
        """Get failed photos that are eligible for retry based on backoff logic."""
        current_time = now()

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
        """Handle upload failure with retry tracking.
        
        Ensures that any photo failure (whether from pending or failed status)
        gets proper retry tracking so it can be retried later.
        """
        # Initialize retry_count if it's None or 0 for pending photos
        if photo.retry_count is None or photo.retry_count == 0:
            photo.retry_count = 0
        
        # Increment retry count
        photo.retry_count += 1
        photo.last_retry_at = now()

        if photo.retry_count >= self.max_retries:
            photo.upload_status = 'permanently_failed'
            logger.error(f"Photo {photo.id} permanently failed after {photo.retry_count} attempts: {error}")
        else:
            photo.upload_status = 'failed'
            logger.warning(f"Photo {photo.id} failed (attempt {photo.retry_count}/{self.max_retries}), will retry later: {error}")

        session.commit()

    def _handle_stale_pending_photos(self, session):
        """Convert stale pending photos to failed status for retry logic.
        
        Photos that have been pending for more than 1 hour without any retry tracking
        are considered stale and should be marked as failed so they can be retried.
        """
        # Find pending photos that are older than 1 hour and have no retry tracking
        stale_threshold = now() - timedelta(hours=1)
        stale_photos = session.query(Photo).filter(
            Photo.upload_status == 'pending',
            Photo.created_at < stale_threshold,
            or_(Photo.retry_count == 0, Photo.retry_count.is_(None)),
            Photo.last_retry_at.is_(None)
        ).all()
        
        for photo in stale_photos:
            logger.warning(f"Photo {photo.id} has been pending for over 1 hour, marking as failed for retry")
            photo.upload_status = 'failed'
            photo.retry_count = 0  # Initialize retry count
            photo.last_retry_at = None  # Allow immediate retry
        
        if stale_photos:
            session.commit()
            logger.info(f"Converted {len(stale_photos)} stale pending photos to failed status")

    def _process_single_upload(self, session, photo):
        """Process upload for a single photo."""
        logger.info(f"Processing upload for photo {photo.id}")

        # Check if local file exists
        local_path = self._get_local_photo_path(photo.id)
        if not Path(local_path).exists():
            logger.warning(f"Local photo file not found: {local_path}")
            # Properly handle failure with retry tracking
            self._handle_upload_failure(session, photo, FileNotFoundError(f"Local photo file not found: {local_path}"))
            return

        # Move to processing directory
        processing_path = self._move_to_processing(photo.id)

        try:
            # Generate thumbnail if not exists (outside transaction)
            thumbnail_path = self._ensure_thumbnail(processing_path, photo, session)

            # Upload to cloud - organize by site_id (outside transaction to avoid long-running tx)
            result = self.cloud_storage.upload_photo(
                photo_id=photo.id,
                photo_path=processing_path,
                thumbnail_path=thumbnail_path,
                site_id=photo.site_id
            )

            # Update photo record with cloud URLs in a short transaction
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
        return str(self.cloud_storage.pending_path / f"{photo_id}.jpg")

    def _move_to_processing(self, photo_id):
        """Move photo file to processing directory."""
        pending_path = Path(self._get_local_photo_path(photo_id))
        processing_path = self.cloud_storage.processing_path / f"{photo_id}.jpg"

        if pending_path.exists():
            pending_path.rename(processing_path)
            return str(processing_path)
        else:
            raise FileNotFoundError(f"Pending photo not found: {pending_path}")

    def _move_to_completed(self, photo_id):
        """Move photo file to completed directory."""
        processing_path = self.cloud_storage.processing_path / f"{photo_id}.jpg"
        completed_path = self.cloud_storage.completed_path / f"{photo_id}.jpg"

        if processing_path.exists():
            processing_path.rename(completed_path)

    def _move_to_pending(self, photo_id):
        """Move photo file back to pending directory."""
        processing_path = self.cloud_storage.processing_path / f"{photo_id}.jpg"
        pending_path = Path(self._get_local_photo_path(photo_id))

        if processing_path.exists():
            processing_path.rename(pending_path)

    def _ensure_thumbnail(self, photo_path, photo, session):
        """Ensure thumbnail exists for photo.

        Args:
            photo_path: Path to the photo file
            photo: Photo database object to update if corrupted
            session: Database session for updating photo corruption flag
        """
        thumbnail_path = photo_path.replace('.jpg', '_thumb.jpg')

        if Path(thumbnail_path).exists():
            return thumbnail_path

        # Generate thumbnail from file path to avoid loading large images into memory
        # generate_thumbnail decorator handles most errors, but we need to catch CorruptedImageError
        # to flag corruption in the database
        try:
            thumbnail_data = generate_thumbnail(image_path=photo_path, max_size=200)
            
            if thumbnail_data is None:
                # Non-corruption error (e.g., file not found) - return None
                return None

            with open(thumbnail_path, 'wb') as f:
                f.write(thumbnail_data)

            return thumbnail_path

        except CorruptedImageError as e:
            # Image is corrupted - flag it in database
            logger.error(f"Corrupted image detected for photo {photo.id}: {e}")
            photo.corrupted = True
            session.commit()
            return None

    def queue_photo_for_upload(self, photo_id, photo_data=None, photo_path=None, thumbnail_data=None):
        """
        Queue a photo for upload to cloud storage.

        Args:
            photo_id: Photo identifier
            photo_data: Raw photo bytes (optional if photo_path provided)
            photo_path: Path to photo file (optional if photo_data provided)
            thumbnail_data: Raw thumbnail bytes (optional)
        """
        if photo_data is None and photo_path is None:
            raise ValueError("Either photo_data or photo_path must be provided")

        try:
            # Save photo data locally
            local_photo_path = self._get_local_photo_path(photo_id)

            if photo_path:
                # Copy file from source path
                shutil.copy2(photo_path, local_photo_path)
            else:
                # Write data to file
                with open(local_photo_path, 'wb') as f:
                    f.write(photo_data)

            # Save thumbnail if provided
            if thumbnail_data:
                thumbnail_path = local_photo_path.replace('.jpg', '_thumb.jpg')
                with open(thumbnail_path, 'wb') as f:
                    f.write(thumbnail_data)

            # Add to work queue for immediate processing
            try:
                self._work_queue.put_nowait(photo_id)
            except queue.Full:
                # Queue is full, will be picked up by database polling
                logger.warning(f"Work queue full, photo {photo_id} will be processed during next database poll")

            logger.info(f"Queued photo {photo_id} for upload")

        except Exception as e:
            logger.error(f"Failed to queue photo {photo_id}: {e}")
            raise

    def _process_queued_photo(self, photo_id):
        """Process a single photo from the work queue."""
        with session_scope(self.SessionLocal) as session:
            photo = session.query(Photo).filter_by(id=photo_id).first()
            if not photo:
                logger.warning(f"Photo {photo_id} not found in database")
                return

            # Only process if still pending or failed
            if photo.upload_status in ('pending', 'failed'):
                try:
                    self._process_single_upload(session, photo)
                except Exception as e:
                    logger.error(f"Failed to upload photo {photo_id}: {e}")
                    self._handle_upload_failure(session, photo, e)


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
