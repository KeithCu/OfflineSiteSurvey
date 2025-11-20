from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, IntegrityError
import json
import os
from pathlib import Path
from datetime import datetime
import uuid
import secrets
import zipfile
import tempfile
import shutil
import hashlib
import logging
import io
import requests
import platform
from PIL import Image
from appdirs import user_data_dir

# Import models from the shared library
from shared.models import (
    Base, Project, Site, Survey, SurveyResponse, AppConfig,
    SurveyTemplate, TemplateField, Photo
)
# Keep local enums for now, can be moved to shared later if needed
from shared.enums import ProjectStatus, SurveyStatus, PhotoCategory, PriorityLevel
# Import shared utilities
from shared.utils import compute_photo_hash, generate_thumbnail, should_show_field, build_response_lookup, CorruptedImageError

# Import new services
from .repositories.survey_repository import SurveyRepository
from .services.image_service import ImageService
from .services.sync_service import SyncService


class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        """Initialize the local database"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initializing LocalDatabase with path: {db_path}")
        
        self.db_path = db_path
        self.logger.debug(f"Database path set to: {self.db_path}")

        self.photos_dir = Path(db_path).parent / 'local_photos'
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Photos directory initialized: {self.photos_dir}")
        
        self.site_id = str(uuid.uuid4())
        self.logger.info(f"Generated site_id: {self.site_id}")
        
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self.logger.info(f"SQLAlchemy engine created for database: {self.db_path}")
        self.last_applied_changes = {}

        @event.listens_for(self.engine, "connect")
        def load_crsqlite_extension(db_conn, conn_record):
            # Check environment variable first (for deployment flexibility)
            lib_path = os.getenv('CRSQLITE_LIB_PATH')
            
            if lib_path and Path(lib_path).exists():
                lib_path = Path(lib_path)
                self.logger.debug(f"Using cr-sqlite extension from CRSQLITE_LIB_PATH: {lib_path}")
            else:
                # Fallback to user data directory
                data_dir = user_data_dir("crsqlite", "vlcn.io")
                # Determine extension based on platform
                system = platform.system()
                ext = '.dll' if system == 'Windows' else '.dylib' if system == 'Darwin' else '.so'
                lib_path = Path(data_dir) / f'crsqlite{ext}'

                if not lib_path.exists():
                    # Last resort: relative to project root (development only)
                    lib_path = Path(__file__).parent.parent.parent / 'lib' / f'crsqlite{ext}'
                    self.logger.debug(f"Using fallback cr-sqlite extension path: {lib_path}")
                else:
                    self.logger.debug(f"Using cr-sqlite extension from user data dir: {lib_path}")

            if not lib_path.exists():
                error_msg = (
                    f"cr-sqlite extension not found. "
                    f"Set CRSQLITE_LIB_PATH environment variable or install via setup_crsqlite.sh"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            try:
                db_conn.enable_load_extension(True)
                db_conn.load_extension(str(lib_path))
                self.logger.info("Successfully loaded cr-sqlite extension for CRDT support")
            except Exception as e:
                self.logger.error(f"Failed to load cr-sqlite extension from {lib_path}: {e}", exc_info=True)
                raise

        self.logger.info("Creating database tables")
        Base.metadata.create_all(self.engine)
        self.logger.info("Database tables created successfully")

        self.logger.info("Initializing CRR tables for CRDT synchronization")
        with self.engine.connect() as connection:
            connection.execute(text("PRAGMA foreign_keys = OFF;"))
            self.logger.debug("Foreign keys disabled for CRR setup")
            
            crr_success_count = 0
            for table in Base.metadata.sorted_tables:
                # Use the consistent table name 'app_config'
                if table.name == 'app_config':
                    self.logger.debug(f"Skipping CRR setup for app_config table (server-only)")
                    continue
                try:
                    connection.execute(text(f"SELECT crsql_as_crr('{table.name}');"))
                    crr_success_count += 1
                    self.logger.debug(f"Made table '{table.name}' CRR-enabled")
                except (OperationalError, IntegrityError) as e:
                    # If table is already CRR-enabled, SQLite/CRDT may raise OperationalError
                    error_msg = str(e).lower()
                    if 'already' in error_msg or 'exists' in error_msg or 'duplicate' in error_msg:
                        self.logger.debug(f"Table '{table.name}' is already CRR-enabled")
                        crr_success_count += 1
                    else:
                        self.logger.warning(f"Failed to make {table.name} CRR: {e}")
                        # Continue with other tables
                except Exception as e:
                    # Catch any other unexpected exceptions
                    self.logger.warning(f"Unexpected error making {table.name} CRR: {e}")
                    # Continue with other tables
            
            self.logger.info(f"CRR initialization completed: {crr_success_count} tables configured")

        self.Session = sessionmaker(bind=self.engine)
        self.logger.info("Session maker created and database initialization completed")

        # Initialize services (share last_applied_changes dict with sync_service)
        self.repository = SurveyRepository(self.Session)
        self.image_service = ImageService(self.photos_dir)
        self.sync_service = SyncService(self.Session, self.site_id, self.last_applied_changes)
        self.logger.info("Services initialized: repository, image_service, sync_service")

    def get_session(self):
        return self.Session()

    def _save_photo_file(self, photo_id, image_data, thumbnail_data=None):
        """Save photo data to local filesystem."""
        return self.image_service.save_photo_file(photo_id, image_data, thumbnail_data)

    def get_photo_data(self, photo_id, thumbnail=False):
        """Retrieve photo data from local filesystem."""
        return self.image_service.get_photo_data(photo_id, thumbnail)
            
    def get_photo_path(self, photo_id):
        """Get absolute path to local photo file."""
        return self.image_service.get_photo_path(photo_id)

    def get_surveys(self):
        return self.repository.get_surveys()

    def get_survey(self, survey_id):
        return self.repository.get_survey(survey_id)

    def get_projects(self):
        return self.repository.get_projects()

    def get_sites(self):
        return self.repository.get_sites()

    def get_sites_for_project(self, project_id):
        return self.repository.get_sites_for_project(project_id)

    def save_project(self, project_data):
        return self.repository.save_project(project_data)

    def save_site(self, site_data):
        return self.repository.save_site(site_data)

    def get_surveys_for_site(self, site_id):
        return self.repository.get_surveys_for_site(site_id)

    def save_survey(self, survey_data):
        return self.repository.save_survey(survey_data)

    def get_template_fields(self, template_id):
        return self.repository.get_template_fields(template_id)

    def get_templates(self):
        return self.repository.get_templates()

    def save_template(self, template_data):
        return self.repository.save_template(template_data)

    def update_template_section_tags(self, template_id, section_tags):
        return self.repository.update_template_section_tags(template_id, section_tags)

    def save_photo(self, photo_data):
        """Save a photo with image processing and file I/O."""
        session = self.get_session()
        try:
            image_data = photo_data.pop('image_data', None)
            thumbnail_data = photo_data.pop('thumbnail_data', None)
            
            # Generate photo ID if not provided
            if 'id' not in photo_data or not photo_data['id']:
                survey_id = photo_data.get('survey_id')
                site_id = None
                if survey_id:
                    survey = session.get(Survey, survey_id)
                    if survey:
                        site_id = survey.site_id
                section = photo_data.get('section', 'general')
                
                if image_data:
                    processed = self.image_service.process_photo(
                        image_data,
                        photo_id=None,
                        survey_id=survey_id,
                        site_id=site_id,
                        section=section
                    )
                    photo_data['id'] = processed['id']
                else:
                    # Generate ID without processing if no image data
                    photo_data['id'] = self.image_service._generate_photo_id(
                        survey_id=survey_id,
                        site_id=site_id,
                        section=section
                    )
            else:
                # Process image if ID already exists and we have image data
                processed = {}
                if image_data:
                    processed = self.image_service.process_photo(
                        image_data,
                        photo_id=photo_data['id'],
                        survey_id=photo_data.get('survey_id'),
                        site_id=None,
                        section=photo_data.get('section', 'general')
                    )

            if image_data:
                photo_data['hash_value'] = processed.get('hash_value', compute_photo_hash(image_data))
                photo_data['size_bytes'] = processed.get('size_bytes', len(image_data))
                photo_data['upload_status'] = 'pending'
                photo_data['cloud_url'] = ''
                photo_data['thumbnail_url'] = ''

                # Use processed thumbnail or provided one
                if not thumbnail_data:
                    thumbnail_data = processed.get('thumbnail_data')
                
                # Save to disk
                filename = self.image_service.save_photo_file(photo_data['id'], image_data, thumbnail_data)
                photo_data['file_path'] = filename
                photo_data['corrupted'] = processed.get('corrupted', False)

            return self.repository.save_photo(photo_data)
        finally:
            session.close()

    def save_response(self, response_data):
        return self.repository.save_response(response_data)

    def get_responses_for_survey(self, survey_id):
        return self.repository.get_responses_for_survey(survey_id)

    def save_responses(self, survey_id, responses_dict):
        return self.repository.save_responses(survey_id, responses_dict)

    def get_photos(self, survey_id=None, category=None, search_term=None, page=1, per_page=40):
        return self.repository.get_photos(survey_id, category, search_term, page, per_page)
            
    def get_pending_upload_photos(self):
        """Get list of photos that are pending upload."""
        return self.repository.get_pending_upload_photos()
            
    def mark_photo_uploaded(self, photo_id, cloud_url=None, thumbnail_url=None):
        """Mark a photo as uploaded."""
        return self.repository.mark_photo_uploaded(photo_id, cloud_url, thumbnail_url)

    def get_photo_categories(self):
        return self.repository.get_photo_categories()

    def get_all_unique_tags(self):
        return self.repository.get_all_unique_tags()

    def get_section_for_photo(self, photo_id):
        return self.repository.get_section_for_photo(photo_id)

    def get_tags_for_photo(self, photo_id):
        return self.repository.get_tags_for_photo(photo_id)

    def get_changes_since(self, version):
        return self.sync_service.get_changes_since(version)

    def get_current_version(self):
        return self.sync_service.get_current_version()

    def apply_changes(self, changes):
        return self.sync_service.apply_changes(changes)

    def backup(self, backup_dir=None, include_media=True):
        if not backup_dir:
            backup_dir = Path(self.db_path).parent / 'backups'
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        from shared.models import now
        timestamp = now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.zip'
        backup_path = Path(backup_dir) / backup_filename
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                if Path(self.db_path).exists():
                    # Ensure the database file has .db extension in the backup
                    db_filename = Path(self.db_path).name
                    if not db_filename.endswith('.db'):
                        db_filename = f"{db_filename}.db"
                    backup_zip.write(self.db_path, db_filename)

                # Backup photos if include_media is True
                if include_media and self.photos_dir.exists():
                    for root, _, files in os.walk(self.photos_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = Path('local_photos') / Path(file_path).relative_to(self.photos_dir)
                            backup_zip.write(file_path, str(arcname))

                metadata = {
                    'timestamp': timestamp,
                    'database_path': self.db_path,
                    'version': '1.0'
                }
                backup_zip.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
            self.logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return None

    def restore(self, backup_path, validate_hashes=True):
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                    backup_zip.extractall(temp_dir)
                    metadata_file = Path(temp_dir) / 'backup_metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                    else:
                        metadata = {}
                    if 'timestamp' in metadata:
                        from shared.models import now, APP_TIMEZONE
                        # Parse timestamp and ensure it's timezone-aware
                        backup_time_naive = datetime.strptime(metadata['timestamp'], '%Y%m%d_%H%M%S')
                        # Assume backup timestamps are in application timezone (Eastern Time)
                        backup_time = backup_time_naive.replace(tzinfo=APP_TIMEZONE)
                        age_days = (now() - backup_time).days
                        if age_days > 30:
                            raise ValueError(f"Backup is too old ({age_days} days). Maximum allowed age is 30 days.")
                    
                    # Restore database
                    temp_dir_path = Path(temp_dir)
                    db_files = [f for f in temp_dir_path.iterdir() if f.suffix == '.db']
                    if not db_files:
                        raise ValueError("No database file found in backup")
                    backup_db_path = db_files[0]

                    # Restore photos
                    photos_backup_dir = temp_dir_path / 'local_photos'
                    if photos_backup_dir.exists():
                         if self.photos_dir.exists():
                            shutil.rmtree(self.photos_dir)
                         shutil.copytree(photos_backup_dir, self.photos_dir)
                    
                    if validate_hashes:
                        self._validate_backup_integrity(backup_db_path)
                    if hasattr(self, 'engine'):
                        self.engine.dispose()
                    shutil.copy2(backup_db_path, self.db_path)
                    self.engine = create_engine(f'sqlite:///{self.db_path}')
                    Base.metadata.create_all(self.engine)
                    self.Session = sessionmaker(bind=self.engine)
                    self.logger.info(f"Successfully restored from backup: {backup_path}")
                    return True
            except Exception as e:
                self.logger.error(f"Restore failed: {e}")
                raise

    def _validate_backup_integrity(self, backup_db_path):
        backup_engine = create_engine(f'sqlite:///{backup_db_path}')
        try:
            from sqlalchemy.orm import sessionmaker
            BackupSession = sessionmaker(bind=backup_engine)
            backup_session = BackupSession()
            backup_photos = backup_session.query(Photo).all()
            integrity_issues = []
            for photo in backup_photos:
                # Check local file for integrity
                photo_path = self.photos_dir / f"{photo.id}.jpg"
                if photo_path.exists() and photo.hash_value:
                     with open(photo_path, 'rb') as f:
                        current_hash = compute_photo_hash(f.read())
                     if current_hash != photo.hash_value:
                        integrity_issues.append(f"Photo {photo.id}: hash mismatch")
            backup_session.close()
            if integrity_issues:
                raise ValueError(f"Backup integrity validation failed: {integrity_issues}")
        finally:
            backup_engine.dispose()

    def cleanup_old_backups(self, backup_dir=None, max_backups=10):
        if not backup_dir:
            backup_dir = Path(self.db_path).parent / 'backups'
        backup_dir_path = Path(backup_dir)
        if not backup_dir_path.exists():
            return
        backup_files = [f for f in backup_dir_path.iterdir() if f.name.startswith('backup_') and f.suffix == '.zip']
        if len(backup_files) <= max_backups:
            return
        backup_files.sort(key=lambda x: x.stem.split('_')[1], reverse=True)
        for old_backup in backup_files[max_backups:]:
            try:
                old_backup.unlink()
                self.logger.info(f"Removed old backup: {old_backup.name}")
            except Exception as e:
                self.logger.warning(f"Failed to remove old backup {old_backup.name}: {e}")

    def get_conditional_fields(self, template_id):
        return self.repository.get_conditional_fields(template_id)

    def evaluate_conditions(self, survey_id, current_responses):
        session = self.get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey or not survey.template_id:
                return []
            template = session.get(SurveyTemplate, survey.template_id)
            all_fields = sorted(template.fields, key=lambda x: x.order_index)
            
            # Pre-compute response lookup once for all field evaluations
            response_lookup = build_response_lookup(current_responses)
            
            visible_fields = []
            for field in all_fields:
                if field.conditions:
                    conditions = json.loads(field.conditions)
                    if self.should_show_field(conditions, response_lookup):
                        visible_fields.append(field.id)
                else:
                    visible_fields.append(field.id)
            return visible_fields
        finally:
            session.close()

    def should_show_field(self, conditions, response_lookup):
        """Optimized version using response lookup dictionary for O(1) access."""
        return should_show_field(conditions, response_lookup)

    def get_survey_progress(self, survey_id):
        return self.repository.get_survey_progress(survey_id)

    def get_photo_requirements(self, survey_id):
        return self.repository.get_photo_requirements(survey_id)

    def check_photo_integrity(self):
        """Check integrity of all photos in the database.
        Returns the number of integrity issues found."""
        session = self.get_session()
        try:
            photos = session.query(Photo).all()
            issues = 0
            for photo in photos:
                current_hash = None

                # Check local data first
                photo_path = self.photos_dir / f"{photo.id}.jpg"
                if photo_path.exists():
                    with open(photo_path, 'rb') as f:
                        current_hash = compute_photo_hash(f.read())
                # Check cloud data if no local data but has cloud URL
                elif photo.cloud_url and photo.upload_status == 'completed':
                     pass # Cannot check cloud integrity here without downloading
                else:
                    # No data available to check, skip
                    continue

                if not photo.hash_value:
                    issues += 1
                    continue

                if photo.hash_value != current_hash:
                    issues += 1
                    continue

            return issues
        finally:
            session.close()

    def mark_requirement_fulfillment(self, photo_id, requirement_id, fulfills=True):
        return self.repository.mark_requirement_fulfillment(photo_id, requirement_id, fulfills)

    def close(self):
        """Close the database connection and dispose of the engine."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            self.logger.info("Database engine disposed")
