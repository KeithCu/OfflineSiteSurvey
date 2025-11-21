"""Orphan cleanup service for CRDT synchronization."""

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
from shared.models import Project, Site, Survey, SurveyResponse, SurveyTemplate, TemplateField, Photo
from ..utils import get_orphaned_records, safe_db_transaction


logger = logging.getLogger(__name__)


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


class OrphanCleanupService:
    """Background service for detecting and cleaning orphaned records from CRDT sync."""

    def __init__(self, db_uri='sqlite:///instance/backend_main.db', check_interval_hours=6):
        """Initialize orphan cleanup service.

        Args:
            db_uri: Database URI for SQLAlchemy
            check_interval_hours: How often to run cleanup checks (in hours)
        """
        self.db_uri = db_uri
        self.engine = create_engine(db_uri)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.check_interval_hours = check_interval_hours
        self.running = False
        self.thread = None
        self.last_cleanup = None
        self._lock = Lock()

    def start(self):
        """Start the background orphan cleanup service."""
        with self._lock:
            if self.running:
                logger.warning("Orphan cleanup service is already running")
                return

            self.running = True
            self.thread = threading.Thread(target=self._run_cleanup_checks, daemon=True)
            self.thread.start()
            logger.info("Orphan cleanup service started")

    def stop(self):
        """Stop the background orphan cleanup service."""
        with self._lock:
            if not self.running:
                return

            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("Orphan cleanup service stopped")

    def _run_cleanup_checks(self):
        """Main loop for running orphan cleanup checks."""
        logger.info("Orphan cleanup service loop started")

        while self.running:
            try:
                # Run orphan cleanup if enough time has passed
                if self._should_run_cleanup():
                    self._run_orphan_cleanup()

                # Sleep for the check interval
                time.sleep(self.check_interval_hours * 3600)  # Convert hours to seconds

            except Exception as e:
                logger.error(f"Error in orphan cleanup service loop: {e}", exc_info=True)
                time.sleep(300)  # Sleep 5 minutes on error before retrying

        logger.info("Orphan cleanup service loop ended")

    def _should_run_cleanup(self):
        """Determine if orphan cleanup should be run."""
        if self.last_cleanup is None:
            return True

        time_since_last_cleanup = datetime.now() - self.last_cleanup
        return time_since_last_cleanup.total_seconds() >= (self.check_interval_hours * 3600)

    @safe_db_transaction("orphan cleanup")
    def _run_orphan_cleanup(self):
        """Run orphan cleanup for all relationship types."""
        logger.info("Starting orphan cleanup check")

        try:
            with session_scope(self.SessionLocal) as session:
                # Get all orphaned records
                orphaned = get_orphaned_records()
                total_orphaned = sum(len(records) for records in orphaned.values())

                if total_orphaned == 0:
                    logger.info("Orphan cleanup completed: No orphaned records found")
                    self.last_cleanup = datetime.now()
                    return

                logger.warning(f"Found {total_orphaned} orphaned records, starting cleanup")

                # Clean up orphaned records in dependency order (children first)
                cleanup_stats = {}

                # Photos (leaf records)
                if 'photos' in orphaned and orphaned['photos']:
                    photos_deleted = self._cleanup_orphaned_photos(session, orphaned['photos'])
                    cleanup_stats['photos'] = photos_deleted

                # Survey responses (depend on surveys)
                if 'responses' in orphaned and orphaned['responses']:
                    responses_deleted = self._cleanup_orphaned_responses(session, orphaned['responses'])
                    cleanup_stats['responses'] = responses_deleted

                # Surveys (depend on sites)
                if 'surveys' in orphaned and orphaned['surveys']:
                    surveys_deleted = self._cleanup_orphaned_surveys(session, orphaned['surveys'])
                    cleanup_stats['surveys'] = surveys_deleted

                # Template fields (depend on templates)
                if 'template_fields' in orphaned and orphaned['template_fields']:
                    fields_deleted = self._cleanup_orphaned_template_fields(session, orphaned['template_fields'])
                    cleanup_stats['template_fields'] = fields_deleted

                # Sites (depend on projects)
                if 'sites' in orphaned and orphaned['sites']:
                    sites_deleted = self._cleanup_orphaned_sites(session, orphaned['sites'])
                    cleanup_stats['sites'] = sites_deleted

                self.last_cleanup = datetime.now()

                total_cleaned = sum(cleanup_stats.values())
                logger.info(f"Orphan cleanup completed: Cleaned up {total_cleaned} records")
                for record_type, count in cleanup_stats.items():
                    if count > 0:
                        logger.info(f"  {record_type}: {count} records removed")

        except Exception as e:
            logger.error(f"Error during orphan cleanup: {e}", exc_info=True)
            raise

    def _cleanup_orphaned_photos(self, session, photo_ids):
        """Clean up orphaned photos."""
        deleted = 0
        for photo_id in photo_ids:
            try:
                photo = session.query(Photo).filter_by(id=photo_id).first()
                if photo:
                    # Log the cleanup
                    logger.info(f"Removing orphaned photo: {photo_id} (survey_id={photo.survey_id}, site_id={photo.site_id})")

                    # Clean up cloud storage if needed
                    if photo.cloud_url and photo.upload_status == 'completed':
                        try:
                            from .cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            # Extract object name from URL and delete
                            if photo.cloud_url:
                                # This would need URL parsing logic from the existing codebase
                                pass  # Implement cloud cleanup if needed
                        except Exception as e:
                            logger.warning(f"Failed to cleanup cloud storage for orphaned photo {photo_id}: {e}")

                    session.delete(photo)
                    deleted += 1

            except Exception as e:
                logger.error(f"Error cleaning up orphaned photo {photo_id}: {e}")

        return deleted

    def _cleanup_orphaned_responses(self, session, response_ids):
        """Clean up orphaned survey responses."""
        deleted = 0
        for response_id in response_ids:
            try:
                response = session.query(SurveyResponse).filter_by(id=response_id).first()
                if response:
                    logger.info(f"Removing orphaned survey response: {response_id} (survey_id={response.survey_id})")
                    session.delete(response)
                    deleted += 1
            except Exception as e:
                logger.error(f"Error cleaning up orphaned response {response_id}: {e}")

        return deleted

    def _cleanup_orphaned_surveys(self, session, survey_ids):
        """Clean up orphaned surveys."""
        deleted = 0
        for survey_id in survey_ids:
            try:
                survey = session.query(Survey).filter_by(id=survey_id).first()
                if survey:
                    logger.info(f"Removing orphaned survey: {survey_id} (site_id={survey.site_id})")
                    session.delete(survey)  # Cascade will handle responses and photos
                    deleted += 1
            except Exception as e:
                logger.error(f"Error cleaning up orphaned survey {survey_id}: {e}")

        return deleted

    def _cleanup_orphaned_template_fields(self, session, field_ids):
        """Clean up orphaned template fields."""
        deleted = 0
        for field_id in field_ids:
            try:
                field = session.query(TemplateField).filter_by(id=field_id).first()
                if field:
                    logger.info(f"Removing orphaned template field: {field_id} (template_id={field.template_id})")
                    session.delete(field)
                    deleted += 1
            except Exception as e:
                logger.error(f"Error cleaning up orphaned template field {field_id}: {e}")

        return deleted

    def _cleanup_orphaned_sites(self, session, site_ids):
        """Clean up orphaned sites."""
        deleted = 0
        for site_id in site_ids:
            try:
                site = session.query(Site).filter_by(id=site_id).first()
                if site:
                    logger.info(f"Removing orphaned site: {site_id} (project_id={site.project_id})")
                    session.delete(site)  # Cascade will handle surveys, responses, photos
                    deleted += 1
            except Exception as e:
                logger.error(f"Error cleaning up orphaned site {site_id}: {e}")

        return deleted

    def check_orphans_now(self):
        """Manually run orphan check and return results.

        Returns:
            dict: Orphan check results
        """
        try:
            with session_scope(self.SessionLocal) as session:
                orphaned = get_orphaned_records()
                total_orphaned = sum(len(records) for records in orphaned.values())

                return {
                    'total_orphaned': total_orphaned,
                    'orphaned_by_type': {k: len(v) for k, v in orphaned.items()},
                    'orphaned_details': orphaned,
                    'last_cleanup': self.last_cleanup.isoformat() if self.last_cleanup else None
                }

        except Exception as e:
            logger.error(f"Error checking orphans: {e}")
            return {'error': str(e)}


# Global service instance for singleton pattern
_orphan_cleanup_service = None
_orphan_cleanup_lock = Lock()


def get_orphan_cleanup_service(db_uri=None):
    """Get or create orphan cleanup service instance (thread-safe)."""
    global _orphan_cleanup_service
    if _orphan_cleanup_service is None:
        with _orphan_cleanup_lock:
            # Double-check pattern for thread safety
            if _orphan_cleanup_service is None:
                if db_uri is None:
                    # Try to get from environment or use default
                    db_uri = os.getenv('DATABASE_URL', 'sqlite:///instance/backend_main.db')
                _orphan_cleanup_service = OrphanCleanupService(db_uri)
    return _orphan_cleanup_service
