"""Photo integrity checking service for background corruption detection."""

import json
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from threading import Lock
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, or_
from sqlalchemy.exc import SQLAlchemyError
from shared.models import Photo, now
from shared.utils import compute_photo_hash
from ..utils import safe_db_transaction


logger = logging.getLogger(__name__)

# Global service instance for singleton pattern
_photo_integrity_service = None
_photo_integrity_lock = Lock()


@contextmanager
def session_scope(session_factory):
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


class PhotoIntegrityService:
    """Background service for checking photo integrity and detecting corruption."""

    def __init__(self, db_uri='sqlite:///instance/backend_main.db', check_interval_hours=24):
        """Initialize photo integrity service.

        Args:
            db_uri: Database URI for SQLAlchemy
            check_interval_hours: How often to run full integrity checks (in hours)
        """
        self.db_uri = db_uri
        self.engine = create_engine(db_uri)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.check_interval_hours = check_interval_hours
        self.running = False
        self.thread = None
        self.last_full_check = None
        self._lock = Lock()

    def start(self):
        """Start the background integrity checking service."""
        with self._lock:
            if self.running:
                logger.warning("Photo integrity service is already running")
                return

            self.running = True
            self.thread = threading.Thread(target=self._run_integrity_checks, daemon=True)
            self.thread.start()
            logger.info("Photo integrity service started")

    def stop(self):
        """Stop the background integrity checking service."""
        with self._lock:
            if not self.running:
                return

            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("Photo integrity service stopped")

    def _run_integrity_checks(self):
        """Main loop for running integrity checks."""
        logger.info("Photo integrity service loop started")

        while self.running:
            try:
                # Run incremental check (new/changed photos)
                self._check_recent_photos()

                # Run full integrity check if enough time has passed
                if self._should_run_full_check():
                    self._run_full_integrity_check()

                # Sleep for a reasonable interval (check every hour)
                time.sleep(3600)  # 1 hour

            except Exception as e:
                logger.error(f"Error in photo integrity service loop: {e}", exc_info=True)
                time.sleep(300)  # Sleep 5 minutes on error before retrying

        logger.info("Photo integrity service loop ended")

    def _should_run_full_check(self):
        """Determine if a full integrity check should be run."""
        if self.last_full_check is None:
            return True

        time_since_last_check = datetime.now() - self.last_full_check
        return time_since_last_check.total_seconds() >= (self.check_interval_hours * 3600)

    def _check_recent_photos(self):
        """Check integrity of recently modified photos."""
        try:
            with session_scope(self.SessionLocal) as session:
                # Check photos modified in the last 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                recent_photos = session.query(Photo).filter(
                    Photo.updated_at >= cutoff_time
                ).all()

                if recent_photos:
                    logger.info(f"Checking integrity of {len(recent_photos)} recently modified photos")
                    issues_found = 0

                    for photo in recent_photos:
                        if self._check_single_photo_integrity(photo, session):
                            issues_found += 1

                    if issues_found > 0:
                        logger.warning(f"Found {issues_found} integrity issues in recent photos")

        except Exception as e:
            logger.error(f"Error checking recent photos: {e}", exc_info=True)

    def _run_full_integrity_check(self):
        """Run a full integrity check on all photos."""
        logger.info("Starting full photo integrity check")

        try:
            with session_scope(self.SessionLocal) as session:
                photos = session.query(Photo).all()
                logger.info(f"Checking integrity of all {len(photos)} photos")

                issues_found = 0
                for photo in photos:
                    if self._check_single_photo_integrity(photo, session):
                        issues_found += 1

                self.last_full_check = datetime.now()

                if issues_found > 0:
                    logger.warning(f"Full integrity check completed: Found {issues_found} issues")
                else:
                    logger.info("Full integrity check completed: All photos passed")

        except Exception as e:
            logger.error(f"Error in full integrity check: {e}", exc_info=True)

    def _check_single_photo_integrity(self, photo, session):
        """Check integrity of a single photo and update corrupted flag if needed.

        Args:
            photo: Photo model instance
            session: Database session

        Returns:
            bool: True if integrity issue was found and marked, False otherwise
        """
        try:
            current_hash = None
            actual_size = None
            data_source = None

            # Check local file path first (if available)
            if photo.file_path and os.path.exists(photo.file_path):
                try:
                    current_hash = compute_photo_hash(photo.file_path)
                    actual_size = os.path.getsize(photo.file_path)
                    data_source = 'local'
                except Exception as e:
                    logger.warning(f"Error reading local file for photo {photo.id}: {e}")

            # Check cloud data if no local file or local check failed
            elif photo.cloud_url and photo.upload_status == 'completed':
                try:
                    from .cloud_storage import get_cloud_storage
                    from urllib.parse import urlparse

                    cloud_storage = get_cloud_storage()

                    def extract_object_name_from_url(url):
                        if not url:
                            return None
                        parsed = urlparse(url)
                        path = parsed.path.lstrip('/')
                        return path if path else None

                    object_name = extract_object_name_from_url(photo.cloud_url)
                    if object_name:
                        image_data = cloud_storage.download_photo(object_name)
                        current_hash = compute_photo_hash(image_data)
                        actual_size = len(image_data)
                        data_source = 'cloud'
                except Exception as e:
                    logger.warning(f"Error downloading photo {photo.id} from cloud: {e}")

            # If we have data to check, validate integrity
            if current_hash is not None:
                hash_matches = photo.hash_value == current_hash
                size_matches = photo.size_bytes == actual_size if actual_size is not None else True

                if not hash_matches or not size_matches:
                    # Mark photo as corrupted
                    photo.corrupted = True
                    logger.warning(
                        f"Photo integrity issue detected: photo_id={photo.id}, "
                        f"hash_match={hash_matches}, size_match={size_matches}, "
                        f"source={data_source}"
                    )

                    # Update hash and size if they were wrong
                    if not hash_matches and current_hash:
                        photo.hash_value = current_hash
                        logger.info(f"Updated hash for corrupted photo {photo.id}")

                    if not size_matches and actual_size is not None:
                        photo.size_bytes = actual_size
                        logger.info(f"Updated size for corrupted photo {photo.id}")

                    return True
                else:
                    # Photo is not corrupted, ensure flag is cleared
                    if photo.corrupted:
                        photo.corrupted = False
                        logger.info(f"Cleared corruption flag for photo {photo.id}")

            return False

        except Exception as e:
            logger.error(f"Error checking photo {photo.id} integrity: {e}")
            return False

    def check_photo_now(self, photo_id):
        """Manually check integrity of a specific photo.

        Args:
            photo_id: ID of the photo to check

        Returns:
            dict: Integrity check results
        """
        try:
            with session_scope(self.SessionLocal) as session:
                photo = session.query(Photo).filter_by(id=photo_id).first()
                if not photo:
                    return {'error': f'Photo {photo_id} not found'}

                has_issues = self._check_single_photo_integrity(photo, session)
                return {
                    'photo_id': photo_id,
                    'corrupted': photo.corrupted,
                    'issues_found': has_issues,
                    'hash_value': photo.hash_value,
                    'size_bytes': photo.size_bytes
                }

        except Exception as e:
            logger.error(f"Error checking photo {photo_id}: {e}")
            return {'error': str(e)}


def get_photo_integrity_service(db_uri=None):
    """Get or create photo integrity service instance (thread-safe)."""
    global _photo_integrity_service
    if _photo_integrity_service is None:
        with _photo_integrity_lock:
            # Double-check pattern for thread safety
            if _photo_integrity_service is None:
                if db_uri is None:
                    # Try to get from environment or use default
                    db_uri = os.getenv('DATABASE_URL', 'sqlite:///instance/backend_main.db')
                _photo_integrity_service = PhotoIntegrityService(db_uri)
    return _photo_integrity_service
