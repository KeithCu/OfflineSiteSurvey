from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
import json
import os
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
from shared.utils import compute_photo_hash, generate_thumbnail


class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        """Initialize the local database"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db_path = db_path
        self.photos_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), 'local_photos')
        os.makedirs(self.photos_dir, exist_ok=True)
        
        self.site_id = str(uuid.uuid4())
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self.last_applied_changes = {}

        @event.listens_for(self.engine, "connect")
        def load_crsqlite_extension(db_conn, conn_record):
            data_dir = user_data_dir("crsqlite", "vlcn.io")
            lib_path = os.path.join(data_dir, 'crsqlite.so')

            if not os.path.exists(lib_path):
                # Adjust path for local development if extension is not installed system-wide
                lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'lib', 'crsqlite.so')

            db_conn.enable_load_extension(True)
            db_conn.load_extension(lib_path)

        Base.metadata.create_all(self.engine)

        with self.engine.connect() as connection:
            connection.execute(text("PRAGMA foreign_keys = OFF;"))
            for table in Base.metadata.sorted_tables:
                # Use the consistent table name 'app_config'
                if table.name == 'app_config':
                    continue
                try:
                    connection.execute(text(f"SELECT crsql_as_crr('{table.name}');"))
                except Exception as e:
                    self.logger.warning(f"Failed to make {table.name} CRR: {e}")
                    # Continue with other tables

        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def _save_photo_file(self, photo_id, image_data, thumbnail_data=None):
        """Save photo data to local filesystem."""
        try:
            photo_filename = f"{photo_id}.jpg"
            photo_path = os.path.join(self.photos_dir, photo_filename)
            
            with open(photo_path, 'wb') as f:
                f.write(image_data)
            
            if thumbnail_data:
                thumb_filename = f"{photo_id}_thumb.jpg"
                thumb_path = os.path.join(self.photos_dir, thumb_filename)
                with open(thumb_path, 'wb') as f:
                    f.write(thumbnail_data)
                    
            return photo_filename
        except Exception as e:
            self.logger.error(f"Failed to save local photo file for {photo_id}: {e}")
            raise

    def get_photo_data(self, photo_id, thumbnail=False):
        """Retrieve photo data from local filesystem."""
        try:
            filename = f"{photo_id}_thumb.jpg" if thumbnail else f"{photo_id}.jpg"
            photo_path = os.path.join(self.photos_dir, filename)
            
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            self.logger.error(f"Failed to read local photo file for {photo_id}: {e}")
            return None
            
    def get_photo_path(self, photo_id):
        """Get absolute path to local photo file."""
        photo_path = os.path.join(self.photos_dir, f"{photo_id}.jpg")
        if os.path.exists(photo_path):
            return photo_path
        return None

    def get_surveys(self):
        session = self.get_session()
        try:
            surveys = session.query(Survey).all()
            return surveys
        finally:
            session.close()

    def get_survey(self, survey_id):
        session = self.get_session()
        try:
            survey = session.get(Survey, survey_id)
            return survey
        finally:
            session.close()

    def get_projects(self):
        session = self.get_session()
        try:
            projects = session.query(Project).all()
            return projects
        finally:
            session.close()

    def get_sites(self):
        session = self.get_session()
        try:
            sites = session.query(Site).all()
            return sites
        finally:
            session.close()

    def get_sites_for_project(self, project_id):
        session = self.get_session()
        try:
            sites = session.query(Site).filter_by(project_id=project_id).all()
            return sites
        finally:
            session.close()

    def save_project(self, project_data):
        session = self.get_session()
        try:
            project = Project(**project_data)
            session.add(project)
            session.commit()
            session.refresh(project)  # Refresh to load generated ID
            return project
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_site(self, site_data):
        session = self.get_session()
        try:
            site = Site(**site_data)
            session.add(site)
            session.commit()
            session.refresh(site)  # Refresh to load generated ID
            return site
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_surveys_for_site(self, site_id):
        session = self.get_session()
        try:
            surveys = session.query(Survey).filter_by(site_id=site_id).all()
            return surveys
        finally:
            session.close()

    def save_survey(self, survey_data):
        session = self.get_session()
        try:
            survey = Survey(**survey_data)
            session.add(survey)
            session.commit()
            session.refresh(survey)  # Refresh to load generated ID
            return survey
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_template_fields(self, template_id):
        session = self.get_session()
        try:
            fields = session.query(TemplateField).filter_by(template_id=template_id).order_by(TemplateField.order_index).all()
            return fields
        finally:
            session.close()

    def get_templates(self):
        session = self.get_session()
        try:
            templates = session.query(SurveyTemplate).all()
            return templates
        finally:
            session.close()

    def save_template(self, template_data):
        session = self.get_session()
        try:
            fields = template_data.pop('fields', [])
            section_tags = template_data.pop('section_tags', None)
            template = SurveyTemplate(**template_data)
            if section_tags is not None:
                template.section_tags = json.dumps(section_tags) if isinstance(section_tags, dict) else section_tags
            template = session.merge(template)
            for field_data in fields:
                field = TemplateField(**field_data)
                session.merge(field)
            session.commit()
            session.refresh(template)  # Refresh to load any generated fields
            return template
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_template_section_tags(self, template_id, section_tags):
        session = self.get_session()
        try:
            template = session.get(SurveyTemplate, template_id)
            if not template:
                return False
            template.section_tags = json.dumps(section_tags)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_photo(self, photo_data):
        session = self.get_session()
        try:
            image_data = photo_data.pop('image_data', None)
            thumbnail_data = photo_data.pop('thumbnail_data', None)
            
            # Generate photo ID if not provided
            if 'id' not in photo_data or not photo_data['id']:
                # Generate ID in format: {site_id}-{section_name}-{random_string}
                survey_id = photo_data.get('survey_id')
                if survey_id:
                    # Get survey to access site_id
                    survey = session.get(Survey, survey_id)
                    if survey:
                        site_id = survey.site_id
                        section_name = photo_data.get('section', 'general').lower().replace(" ", "_")
                        random_string = secrets.token_hex(4)
                        photo_data['id'] = f"{site_id}-{section_name}-{random_string}"
                    else:
                        # Fallback to UUID if survey not found
                        photo_data['id'] = str(uuid.uuid4())
                else:
                    # Fallback to UUID if no survey_id
                    photo_data['id'] = str(uuid.uuid4())

            if image_data:
                # Use utility function for hashing
                photo_data['hash_value'] = compute_photo_hash(image_data)
                photo_data['size_bytes'] = len(image_data)
                photo_data['hash_algo'] = 'sha256'
                photo_data['upload_status'] = 'pending'  # Initially pending upload
                photo_data['cloud_url'] = ''  # Will be set after upload
                photo_data['thumbnail_url'] = ''  # Will be set after upload

                # Generate thumbnail for local storage if not provided
                if not thumbnail_data:
                    thumbnail_data = generate_thumbnail(image_data, max_size=200)

                # Save to disk
                filename = self._save_photo_file(photo_data['id'], image_data, thumbnail_data)
                photo_data['file_path'] = filename

            tags = photo_data.get('tags')
            if tags is None:
                tags = []
            if isinstance(tags, (list, tuple)):
                photo_data['tags'] = json.dumps(list(tags))
            elif isinstance(tags, str):
                photo_data['tags'] = tags
            else:
                photo_data['tags'] = json.dumps([])

            photo = Photo(**photo_data)
            # Do NOT try to set image_data/thumbnail_data attributes as they don't exist in schema
            
            session.add(photo)
            session.commit()
            session.refresh(photo)  # Refresh to load generated ID
            return photo
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_response(self, response_data):
        session = self.get_session()
        try:
            response = SurveyResponse(**response_data)
            session.add(response)
            session.commit()
            session.refresh(response)  # Refresh to load generated ID
            return response
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_photos(self, survey_id=None, category=None, search_term=None, page=1, per_page=40):
        session = self.get_session()
        try:
            query = session.query(Photo)
            if survey_id:
                query = query.filter_by(survey_id=survey_id)
            if category:
                query = query.filter_by(category=category)
            if search_term:
                query = query.filter(Photo.description.contains(search_term))
            total_count = query.count()
            photos = query.order_by(Photo.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
            
            # No need to inject image data here, the UI will request it via get_photo_data or on-demand
            
            return {
                'photos': photos,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        finally:
            session.close()
            
    def get_pending_upload_photos(self):
        """Get list of photos that are pending upload."""
        session = self.get_session()
        try:
            return session.query(Photo).filter_by(upload_status='pending').all()
        finally:
            session.close()
            
    def mark_photo_uploaded(self, photo_id, cloud_url=None, thumbnail_url=None):
        """Mark a photo as uploaded."""
        session = self.get_session()
        try:
            photo = session.get(Photo, photo_id)
            if photo:
                photo.upload_status = 'uploaded'  # Local state indicating sent to server
                if cloud_url:
                    photo.cloud_url = cloud_url
                if thumbnail_url:
                    photo.thumbnail_url = thumbnail_url
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_photo_categories(self):
        session = self.get_session()
        try:
            categories = session.query(Photo.category).distinct().all()
            return [c[0] for c in categories if c[0]]
        finally:
            session.close()

    def get_all_unique_tags(self):
        session = self.get_session()
        try:
            all_tags = []
            photos = session.query(Photo.tags).filter(Photo.tags.isnot(None)).all()
            unique_tags = set()
            for photo_tags in photos:
                try:
                    tags = json.loads(photo_tags[0])
                    for tag in tags:
                        unique_tags.add(tag)
                except (json.JSONDecodeError, TypeError):
                    continue
            return [{'name': tag} for tag in sorted(list(unique_tags))]
        finally:
            session.close()

    def get_section_for_photo(self, photo_id):
        session = self.get_session()
        try:
            photo = session.query(Photo).filter_by(id=photo_id).first()
            if not photo or not photo.question_id:
                return None

            field = session.query(TemplateField).filter_by(id=photo.question_id).first()
            if field:
                return field.section
            return None
        finally:
            session.close()

    def get_tags_for_photo(self, photo_id):
        session = self.get_session()
        try:
            photo = session.query(Photo).filter_by(id=photo_id).first()
            if photo and photo.tags:
                try:
                    return json.loads(photo.tags)
                except (json.JSONDecodeError, TypeError):
                    return []
            return []
        finally:
            session.close()

    def get_changes_since(self, version):
        session = self.get_session()
        try:
            conn = session.connection()
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            cursor.execute(
                "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id != ?",
                (version, self.site_id)
            )
            changes = cursor.fetchall()
            return [dict(zip([c[0] for c in cursor.description], row)) for row in changes]
        finally:
            session.close()

    def get_current_version(self):
        session = self.get_session()
        try:
            conn = session.connection()
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            cursor.execute("SELECT crsql_dbversion()")
            version = cursor.fetchone()[0]
            return version
        finally:
            session.close()

    def apply_changes(self, changes):
        session = self.get_session()
        try:
            conn = session.connection()
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            integrity_issues = []
            applied_changes = {}
            for change in changes:
                table_name = change['table']
                change_version = change['db_version']
                last_applied = self.last_applied_changes.get(table_name, 0)
                if change_version <= last_applied:
                    continue
                if table_name == 'photo' and change['cid'] == 'cloud_url' and change['val']:
                    try:
                        pk_data = json.loads(change['pk'])
                        photo_id = pk_data.get('id')
                        existing_photo = session.get(Photo, photo_id)
                        if existing_photo and existing_photo.hash_value and existing_photo.upload_status == 'completed':
                            # Download photo from cloud and verify hash
                            try:
                                # We don't have direct cloud storage access in frontend (usually)
                                # In a real app, we'd use the API to download or a configured cloud client
                                # For this implementation, we'll skip direct cloud download in apply_changes
                                # and rely on lazy loading or a separate sync process for binaries
                                pass 
                            except Exception as e:
                                pass
                    except (json.JSONDecodeError, AttributeError, TypeError):
                        pass
                try:
                    cursor.execute(
                        "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (table_name, change['pk'], change['cid'], change['val'], change['col_version'], change_version, change['site_id'])
                    )
                    if table_name not in applied_changes or change_version > applied_changes[table_name]:
                        applied_changes[table_name] = change_version
                except Exception as e:
                    self.logger.error(f"Failed to apply change for table {table_name}: {e}")
                    continue
            session.commit()
            for table_name, version in applied_changes.items():
                self.last_applied_changes[table_name] = max(
                    self.last_applied_changes.get(table_name, 0),
                    version
                )
            if integrity_issues:
                self.logger.warning(f"Photo integrity issues detected: {integrity_issues}")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def backup(self, backup_dir=None):
        if not backup_dir:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        from shared.models import utc_now
        timestamp = utc_now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                if os.path.exists(self.db_path):
                    # Ensure the database file has .db extension in the backup
                    db_filename = os.path.basename(self.db_path)
                    if not db_filename.endswith('.db'):
                        db_filename = f"{db_filename}.db"
                    backup_zip.write(self.db_path, db_filename)
                
                # Backup photos
                if os.path.exists(self.photos_dir):
                    for root, _, files in os.walk(self.photos_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join('local_photos', os.path.relpath(file_path, self.photos_dir))
                            backup_zip.write(file_path, arcname)
                
                metadata = {
                    'timestamp': timestamp,
                    'database_path': self.db_path,
                    'version': '1.0'
                }
                backup_zip.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return None

    def restore(self, backup_path, validate_hashes=True):
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                    backup_zip.extractall(temp_dir)
                    metadata_file = os.path.join(temp_dir, 'backup_metadata.json')
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                    else:
                        metadata = {}
                    if 'timestamp' in metadata:
                        backup_time = datetime.strptime(metadata['timestamp'], '%Y%m%d_%H%M%S')
                        from shared.models import utc_now
                        age_days = (utc_now() - backup_time.replace(tzinfo=utc_now().tzinfo)).days
                        if age_days > 30:
                            raise ValueError(f"Backup is too old ({age_days} days). Maximum allowed age is 30 days.")
                    
                    # Restore database
                    db_files = [f for f in os.listdir(temp_dir) if f.endswith('.db')]
                    if not db_files:
                        raise ValueError("No database file found in backup")
                    backup_db_path = os.path.join(temp_dir, db_files[0])
                    
                    # Restore photos
                    photos_backup_dir = os.path.join(temp_dir, 'local_photos')
                    if os.path.exists(photos_backup_dir):
                         if os.path.exists(self.photos_dir):
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
                photo_path = os.path.join(self.photos_dir, f"{photo.id}.jpg")
                if os.path.exists(photo_path) and photo.hash_value:
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
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
        if not os.path.exists(backup_dir):
            return
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('backup_') and f.endswith('.zip')]
        if len(backup_files) <= max_backups:
            return
        backup_files.sort(key=lambda x: x.split('_')[1].split('.')[0], reverse=True)
        for old_backup in backup_files[max_backups:]:
            backup_path = os.path.join(backup_dir, old_backup)
            try:
                os.remove(backup_path)
                self.logger.info(f"Removed old backup: {old_backup}")
            except Exception as e:
                self.logger.warning(f"Failed to remove old backup {old_backup}: {e}")

    def get_conditional_fields(self, template_id):
        session = self.get_session()
        try:
            template = session.get(SurveyTemplate, template_id)
            if not template:
                return {'fields': [], 'section_tags': {}}
            fields = []
            for field in sorted(template.fields, key=lambda x: x.order_index):
                field_data = {
                    'id': field.id, 'field_type': field.field_type, 'question': field.question,
                    'description': field.description, 'required': field.required, 'options': field.options,
                    'order_index': field.order_index, 'section': field.section, 'section_weight': field.section_weight,
                    'conditions': json.loads(field.conditions) if field.conditions else None,
                    'photo_requirements': json.loads(field.photo_requirements) if field.photo_requirements else None
                }
                fields.append(field_data)
            try:
                section_tags = json.loads(template.section_tags) if template.section_tags else {}
            except json.JSONDecodeError:
                section_tags = {}
            return {'fields': fields, 'section_tags': section_tags}
        finally:
            session.close()

    def evaluate_conditions(self, survey_id, current_responses):
        session = self.get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey or not survey.template_id:
                return []
            template = session.get(SurveyTemplate, survey.template_id)
            all_fields = sorted(template.fields, key=lambda x: x.order_index)
            visible_fields = []
            for field in all_fields:
                if field.conditions:
                    conditions = json.loads(field.conditions)
                    if self.should_show_field(conditions, current_responses):
                        visible_fields.append(field.id)
                else:
                    visible_fields.append(field.id)
            return visible_fields
        finally:
            session.close()

    def should_show_field(self, conditions, responses):
        if not conditions:
            return True
        condition_list = conditions.get('conditions', [])
        logic = conditions.get('logic', 'AND')
        results = []
        for condition in condition_list:
            question_id = condition['question_id']
            operator = condition['operator']
            expected_value = condition['value']
            response = next((r for r in responses if r.get('question_id') == question_id), None)
            if not response:
                results.append(False)
                continue
            actual_value = response.get('answer')
            if operator == 'equals':
                results.append(str(actual_value) == str(expected_value))
            elif operator == 'not_equals':
                results.append(str(actual_value) != str(expected_value))
            elif operator == 'in':
                results.append(str(actual_value) in [str(v) for v in expected_value])
            elif operator == 'not_in':
                results.append(str(actual_value) not in [str(v) for v in expected_value])
        return all(results) if logic == 'AND' else any(results)

    def get_survey_progress(self, survey_id):
        session = self.get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey:
                return {}
            responses = session.query(SurveyResponse).filter_by(survey_id=survey_id).all()
            response_dict = {r.question_id: r.answer for r in responses if r.question_id}
            photos = session.query(Photo).filter_by(survey_id=survey_id).all()
            fields = []
            if survey.template_id:
                template = session.get(SurveyTemplate, survey.template_id)
                fields = template.fields
            sections = {}
            total_required = 0
            total_completed = 0
            for field in fields:
                section = field.section or 'General'
                if section not in sections:
                    sections[section] = {
                        'required': 0, 'completed': 0, 'photos_required': 0,
                        'photos_taken': 0, 'weight': field.section_weight
                    }
                if field.required:
                    sections[section]['required'] += 1
                    total_required += 1
                    if field.id in response_dict and response_dict[field.id]:
                        sections[section]['completed'] += 1
                        total_completed += 1
                if field.field_type == 'photo':
                    if field.required:
                        sections[section]['photos_required'] += 1
                    photo_exists = any(p for p in photos if p.requirement_id and field.question in p.description)
                    if photo_exists:
                        sections[section]['photos_taken'] += 1
            overall_progress = (total_completed / total_required * 100) if total_required > 0 else 0
            for section_name, section_data in sections.items():
                section_total = section_data['required']
                section_completed = section_data['completed']
                section_data['progress'] = (section_completed / section_total * 100) if section_total > 0 else 0
            return {
                'overall_progress': overall_progress, 'sections': sections,
                'total_required': total_required, 'total_completed': total_completed
            }
        finally:
            session.close()

    def get_photo_requirements(self, survey_id):
        session = self.get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey or not survey.template_id:
                return {}
            template = session.get(SurveyTemplate, survey.template_id)
            photos = session.query(Photo).filter_by(survey_id=survey_id).all()
            existing_photo_requirements = {p.requirement_id: p for p in photos if p.requirement_id}
            requirements_by_section = {}
            for field in sorted(template.fields, key=lambda x: x.order_index):
                if field.field_type == 'photo' and field.photo_requirements:
                    section = field.section or 'General'
                    if section not in requirements_by_section:
                        requirements_by_section[section] = []
                    photo_req_data = json.loads(field.photo_requirements)
                    photo_req_data['field_id'] = field.id
                    photo_req_data['field_question'] = field.question
                    photo_req_data['taken'] = field.id in existing_photo_requirements
                    requirements_by_section[section].append(photo_req_data)
            return {
                'survey_id': survey_id,
                'requirements_by_section': requirements_by_section
            }
        finally:
            session.close()

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
                photo_path = os.path.join(self.photos_dir, f"{photo.id}.jpg")
                if os.path.exists(photo_path):
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
        session = self.get_session()
        try:
            photo = session.get(Photo, photo_id)
            if photo:
                photo.requirement_id = requirement_id
                photo.fulfills_requirement = fulfills
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
