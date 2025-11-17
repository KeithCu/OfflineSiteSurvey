from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey, Enum
from .enums import ProjectStatus, SurveyStatus, PhotoCategory, PriorityLevel
import json
import os
from datetime import datetime
import uuid
import zlib
import hashlib
import zipfile
import tempfile
import shutil
from appdirs import user_data_dir

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    client_info = Column(Text)
    due_date = Column(DateTime)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    notes = Column(Text)
    project_id = Column(Integer, ForeignKey('projects.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Survey(Base):
    __tablename__ = 'surveys'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(Enum(SurveyStatus), default=SurveyStatus.DRAFT)
    template_id = Column(Integer, ForeignKey('templates.id'))

class SurveyResponse(Base):
    __tablename__ = 'responses'
    id = Column(Integer, primary_key=True)
    survey_id = Column(Integer, ForeignKey('surveys.id'), nullable=False)
    question = Column(String(500), nullable=False)
    answer = Column(Text)
    response_type = Column(String(50))
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Phase 2 additions
    question_id = Column(Integer)  # Links to template field ID for conditional logic
    field_type = Column(String(50))  # Stores field type from template

class AppConfig(Base):
    __tablename__ = 'config'
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(String(300))
    category = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SurveyTemplate(Base):
    __tablename__ = 'templates'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TemplateField(Base):
    __tablename__ = 'template_fields'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('templates.id'), nullable=False)
    field_type = Column(String(50))
    question = Column(String(500), nullable=False)
    description = Column(Text)
    required = Column(Boolean, default=False)
    options = Column(Text)
    order_index = Column(Integer, default=0)
    section = Column(String(100))
    # Phase 2 additions
    conditions = Column(Text)  # JSON format for conditional logic
    photo_requirements = Column(Text)  # JSON format for photo requirements
    section_weight = Column(Integer, default=1)  # For weighted progress calculation

class Photo(Base):
    __tablename__ = 'photos'
    id = Column(String, primary_key=True)
    survey_id = Column(String, ForeignKey('surveys.id'))
    site_id = Column(Integer, ForeignKey('sites.id'))  # For site overview photos
    image_data = Column(LargeBinary)
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    category = Column(Enum(PhotoCategory), default=PhotoCategory.GENERAL)
    exif_data = Column(Text)  # JSON string of EXIF data
    created_at = Column(DateTime, default=datetime.utcnow)
    # Phase 4: Enhanced photo integrity
    hash_algo = Column(String(10), default='sha256')  # Hash algorithm used
    hash_value = Column(String(128))  # Cryptographic hash of image data
    size_bytes = Column(Integer)  # Size of image data in bytes
    # Phase 4: Performance optimizations
    thumbnail_data = Column(LargeBinary)  # Cached 200px thumbnail
    file_path = Column(String(500))  # File path for large photos (future use)
    # Phase 2 additions
    requirement_id = Column(String)  # Links to photo requirement
    fulfills_requirement = Column(Boolean, default=False)  # Tracks if this fulfills a requirement


class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        """Initialize the local database"""
        self.db_path = db_path
        self.site_id = str(uuid.uuid4())
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        # Phase 4: Track last applied changes per table for retry logic
        self.last_applied_changes = {}  # table -> db_version

        @event.listens_for(self.engine, "connect")
        def load_crsqlite_extension(db_conn, conn_record):
            data_dir = user_data_dir("crsqlite", "vlcn.io")
            lib_path = os.path.join(data_dir, 'crsqlite.so')

            if not os.path.exists(lib_path):
                lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'lib', 'crsqlite.so')

            db_conn.enable_load_extension(True)
            db_conn.load_extension(lib_path)

        Base.metadata.create_all(self.engine)

        with self.engine.connect() as connection:
            for table in Base.metadata.sorted_tables:
                if table.name == 'config':
                    continue
                connection.execute(text(f"SELECT crsql_as_crr('{table.name}');"))

        self.Session = sessionmaker(bind=self.engine)

    def _compute_photo_hash(self, image_data):
        """Compute SHA-256 hash of image data for integrity verification"""
        if isinstance(image_data, bytes):
            return hashlib.sha256(image_data).hexdigest()
        return None

    def _generate_thumbnail(self, image_data, max_size=200):
        """Generate a thumbnail from image data, maintaining aspect ratio"""
        if not image_data:
            return None

        try:
            from PIL import Image
            import io

            # Open image from bytes
            img = Image.open(io.BytesIO(image_data))

            # Calculate thumbnail size maintaining aspect ratio
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Save thumbnail to bytes
            thumb_buffer = io.BytesIO()
            img.save(thumb_buffer, format='JPEG', quality=85)
            return thumb_buffer.getvalue()
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None

    def get_session(self):
        return self.Session()

    def get_surveys(self):
        session = self.get_session()
        surveys = session.query(Survey).all()
        session.close()
        return surveys

    def get_survey(self, survey_id):
        session = self.get_session()
        survey = session.query(Survey).get(survey_id)
        session.close()
        return survey

    def get_projects(self):
        session = self.get_session()
        projects = session.query(Project).all()
        session.close()
        return projects

    def get_sites(self):
        session = self.get_session()
        sites = session.query(Site).all()
        session.close()
        return sites

    def get_sites_for_project(self, project_id):
        session = self.get_session()
        sites = session.query(Site).filter_by(project_id=project_id).all()
        session.close()
        return sites

    def save_project(self, project_data):
        session = self.get_session()
        project = Project(**project_data)
        session.add(project)
        session.commit()
        session.close()

    def save_site(self, site_data):
        session = self.get_session()
        site = Site(**site_data)
        session.add(site)
        session.commit()
        session.close()

    def get_surveys_for_site(self, site_id):
        session = self.get_session()
        surveys = session.query(Survey).filter_by(site_id=site_id).all()
        session.close()
        return surveys

    def save_survey(self, survey_data):
        session = self.get_session()
        survey = Survey(**survey_data)
        session.add(survey)
        session.commit()
        session.close()

    def get_template_fields(self, template_id):
        session = self.get_session()
        fields = session.query(TemplateField).filter_by(template_id=template_id).order_by(TemplateField.order_index).all()
        session.close()
        return fields

    def get_templates(self):
        session = self.get_session()
        templates = session.query(SurveyTemplate).all()
        session.close()
        return templates

    def save_template(self, template_data):
        session = self.get_session()
        # a bit of a hack to deal with the fields relationship
        fields = template_data.pop('fields', [])
        template = SurveyTemplate(**template_data)
        session.merge(template)
        for field_data in fields:
            field = TemplateField(**field_data)
            session.merge(field)
        session.commit()
        session.close()

    def save_photo(self, photo_data):
        session = self.get_session()

        # Compute hash and size for photo integrity
        image_data = photo_data.get('image_data')
        if image_data:
            photo_data['hash_value'] = self._compute_photo_hash(image_data)
            photo_data['size_bytes'] = len(image_data)
            photo_data['hash_algo'] = 'sha256'

            # Generate and cache thumbnail for performance
            if not photo_data.get('thumbnail_data'):
                photo_data['thumbnail_data'] = self._generate_thumbnail(image_data)

        photo = Photo(**photo_data)
        session.add(photo)
        session.commit()
        session.close()

    def save_response(self, response_data):
        session = self.get_session()
        response = SurveyResponse(**response_data)
        session.add(response)
        session.commit()
        session.close()

    def get_photos(self, survey_id=None, category=None, search_term=None, page=1, per_page=40):
        """Get photos with pagination support for performance"""
        session = self.get_session()
        query = session.query(Photo)

        if survey_id:
            query = query.filter_by(survey_id=survey_id)
        if category:
            query = query.filter_by(category=category)
        if search_term:
            query = query.filter(Photo.description.contains(search_term))

        # Get total count for pagination info
        total_count = query.count()

        # Apply pagination
        photos = query.order_by(Photo.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        session.close()

        return {
            'photos': photos,
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        }

    def get_photo_categories(self):
        session = self.get_session()
        categories = session.query(Photo.category).distinct().all()
        session.close()
        return [c[0] for c in categories if c[0]]

    def get_changes_since(self, version):
        session = self.get_session()
        conn = session.connection()
        # We need the raw connection to get the cursor
        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        cursor.execute(
            "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id = ?",
            (version, self.site_id)
        )
        changes = cursor.fetchall()
        # We need to convert the rows to dicts
        changes = [dict(zip([c[0] for c in cursor.description], row)) for row in changes]
        session.close()
        return changes

    def get_current_version(self):
        """Get the current CRDT database version"""
        session = self.get_session()
        conn = session.connection()
        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        cursor.execute("SELECT crsql_dbversion()")
        version = cursor.fetchone()[0]
        session.close()
        return version

    def apply_changes(self, changes):
        """Apply changes with integrity verification and retry tracking"""
        session = self.get_session()
        conn = session.connection()
        raw_conn = conn.connection
        cursor = raw_conn.cursor()

        integrity_issues = []
        applied_changes = {}

        for change in changes:
            table_name = change['table']
            change_version = change['db_version']

            # Check if we've already applied this change (idempotent retry)
            last_applied = self.last_applied_changes.get(table_name, 0)
            if change_version <= last_applied:
                continue  # Already applied, skip

            # Verify photo integrity if this is a photo table change
            if table_name == 'photos' and change['cid'] == 'image_data' and change['val']:
                # Extract photo ID from pk (format: '{"id":"photo_id"}')
                import json
                try:
                    pk_data = json.loads(change['pk'])
                    photo_id = pk_data.get('id')

                    # Check if we have existing photo data to compare
                    existing_photo = session.query(Photo).get(photo_id)
                    if existing_photo and existing_photo.hash_value:
                        # Verify the incoming data matches expected hash
                        incoming_hash = self._compute_photo_hash(change['val'])
                        if incoming_hash != existing_photo.hash_value:
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'expected_hash': existing_photo.hash_value,
                                'received_hash': incoming_hash,
                                'action': 'rejected'
                            })
                            continue  # Skip this change
                except (json.JSONDecodeError, AttributeError):
                    pass  # Continue with change if we can't parse

            try:
                cursor.execute(
                    "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (table_name, change['pk'], change['cid'], change['val'], change['col_version'], change_version, change['site_id'])
                )

                # Track successful application
                if table_name not in applied_changes or change_version > applied_changes[table_name]:
                    applied_changes[table_name] = change_version

            except Exception as e:
                print(f"Failed to apply change for table {table_name}: {e}")
                # In production, would queue for retry
                continue

        session.commit()
        session.close()

        # Update tracking of last applied changes
        for table_name, version in applied_changes.items():
            self.last_applied_changes[table_name] = max(
                self.last_applied_changes.get(table_name, 0),
                version
            )

        # Log integrity issues if any
        if integrity_issues:
            print(f"Photo integrity issues detected: {integrity_issues}")
            # In a production system, this would trigger re-sync or alert

    def backup(self, backup_dir=None, include_media=True):
        """Create a timestamped backup of the database and media files"""
        if not backup_dir:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')

        os.makedirs(backup_dir, exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                # Add database file
                if os.path.exists(self.db_path):
                    backup_zip.write(self.db_path, os.path.basename(self.db_path))

                # Add media directory if requested
                if include_media:
                    media_dir = os.path.join(os.path.dirname(self.db_path), 'media')
                    if os.path.exists(media_dir):
                        for root, dirs, files in os.walk(media_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.path.dirname(media_dir))
                                backup_zip.write(file_path, arcname)

                # Add backup metadata
                metadata = {
                    'timestamp': timestamp,
                    'database_path': self.db_path,
                    'include_media': include_media,
                    'version': '1.0'
                }
                backup_zip.writestr('backup_metadata.json', json.dumps(metadata, indent=2))

            print(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            print(f"Backup failed: {e}")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return None

    def restore(self, backup_path, validate_hashes=True):
        """Restore from a backup archive with optional hash validation"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Extract backup
                with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                    backup_zip.extractall(temp_dir)

                    # Read metadata
                    metadata_file = os.path.join(temp_dir, 'backup_metadata.json')
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                    else:
                        metadata = {}

                    # Validate backup age (refuse backups older than 30 days)
                    if 'timestamp' in metadata:
                        backup_time = datetime.strptime(metadata['timestamp'], '%Y%m%d_%H%M%S')
                        age_days = (datetime.now() - backup_time).days
                        if age_days > 30:
                            raise ValueError(f"Backup is too old ({age_days} days). Maximum allowed age is 30 days.")

                    # Find database file in backup
                    db_files = [f for f in os.listdir(temp_dir) if f.endswith('.db')]
                    if not db_files:
                        raise ValueError("No database file found in backup")

                    backup_db_path = os.path.join(temp_dir, db_files[0])

                    # Validate photo integrity if requested
                    if validate_hashes:
                        self._validate_backup_integrity(backup_db_path)

                    # Close current database connections
                    if hasattr(self, 'engine'):
                        self.engine.dispose()

                    # Replace current database with backup
                    shutil.copy2(backup_db_path, self.db_path)

                    # Restore media files if present
                    media_dir = os.path.join(os.path.dirname(self.db_path), 'media')
                    backup_media_dir = os.path.join(temp_dir, 'media')
                    if os.path.exists(backup_media_dir):
                        if os.path.exists(media_dir):
                            shutil.rmtree(media_dir)
                        shutil.copytree(backup_media_dir, media_dir)

                    # Reinitialize database connection
                    self.engine = create_engine(f'sqlite:///{self.db_path}')
                    Base.metadata.create_all(self.engine)
                    self.Session = sessionmaker(bind=self.engine)

                    print(f"Successfully restored from backup: {backup_path}")
                    return True

            except Exception as e:
                print(f"Restore failed: {e}")
                raise

    def _validate_backup_integrity(self, backup_db_path):
        """Validate photo integrity in backup database"""
        backup_engine = create_engine(f'sqlite:///{backup_db_path}')

        try:
            from sqlalchemy.orm import sessionmaker
            BackupSession = sessionmaker(bind=backup_engine)
            backup_session = BackupSession()

            # Get all photos from backup
            backup_photos = backup_session.query(Photo).all()
            integrity_issues = []

            for photo in backup_photos:
                if photo.image_data and photo.hash_value:
                    current_hash = self._compute_photo_hash(photo.image_data)
                    if current_hash != photo.hash_value:
                        integrity_issues.append(f"Photo {photo.id}: hash mismatch")

            backup_session.close()

            if integrity_issues:
                raise ValueError(f"Backup integrity validation failed: {integrity_issues}")

        finally:
            backup_engine.dispose()

    def cleanup_old_backups(self, backup_dir=None, max_backups=10):
        """Clean up old backups, keeping only the most recent ones"""
        if not backup_dir:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')

        if not os.path.exists(backup_dir):
            return

        # Get all backup files
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('backup_') and f.endswith('.zip')]

        if len(backup_files) <= max_backups:
            return

        # Sort by timestamp (newest first)
        backup_files.sort(key=lambda x: x.split('_')[1].split('.')[0], reverse=True)

        # Remove old backups
        for old_backup in backup_files[max_backups:]:
            backup_path = os.path.join(backup_dir, old_backup)
            try:
                os.remove(backup_path)
                print(f"Removed old backup: {old_backup}")
            except Exception as e:
                print(f"Failed to remove old backup {old_backup}: {e}")

    # Phase 2 methods for conditional logic and progress tracking
    
    def get_conditional_fields(self, template_id):
        """Get template fields with conditional logic information"""
        session = self.get_session()
        template = session.query(SurveyTemplate).get(template_id)
        if not template:
            session.close()
            return []
        
        fields = []
        for field in sorted(template.fields, key=lambda x: x.order_index):
            field_data = {
                'id': field.id,
                'field_type': field.field_type,
                'question': field.question,
                'description': field.description,
                'required': field.required,
                'options': field.options,
                'order_index': field.order_index,
                'section': field.section,
                'section_weight': field.section_weight,
                'conditions': json.loads(field.conditions) if field.conditions else None,
                'photo_requirements': json.loads(field.photo_requirements) if field.photo_requirements else None
            }
            fields.append(field_data)
        
        session.close()
        return fields
    
    def evaluate_conditions(self, survey_id, current_responses):
        """Evaluate which fields should be visible based on current responses"""
        session = self.get_session()
        survey = session.query(Survey).get(survey_id)
        if not survey or not survey.template_id:
            session.close()
            return []
        
        template = session.query(SurveyTemplate).get(survey.template_id)
        all_fields = sorted(template.fields, key=lambda x: x.order_index)
        
        visible_fields = []
        
        for field in all_fields:
            # Check if field has conditions
            if field.conditions:
                conditions = json.loads(field.conditions)
                if self.should_show_field(conditions, current_responses):
                    visible_fields.append(field.id)
            else:
                # No conditions, always show
                visible_fields.append(field.id)
        
        session.close()
        return visible_fields
    
    def should_show_field(self, conditions, responses):
        """Evaluate if a field should be shown based on current responses"""
        if not conditions:
            return True
        
        condition_list = conditions.get('conditions', [])
        logic = conditions.get('logic', 'AND')
        
        results = []
        for condition in condition_list:
            question_id = condition['question_id']
            operator = condition['operator']
            expected_value = condition['value']
            
            # Find response for this question
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
        """Get detailed progress information for a survey"""
        session = self.get_session()
        survey = session.query(Survey).get(survey_id)
        if not survey:
            session.close()
            return {}
        
        # Get all responses
        responses = session.query(SurveyResponse).filter_by(survey_id=survey_id).all()
        response_dict = {r.question_id: r.answer for r in responses if r.question_id}
        
        # Get all photos
        photos = session.query(Photo).filter_by(survey_id=str(survey_id)).all()
        
        # Get template fields if available
        fields = []
        if survey.template_id:
            template = session.query(SurveyTemplate).get(survey.template_id)
            fields = template.fields
        
        # Calculate progress by section
        sections = {}
        total_required = 0
        total_completed = 0
        
        for field in fields:
            section = field.section or 'General'
            if section not in sections:
                sections[section] = {
                    'required': 0,
                    'completed': 0,
                    'photos_required': 0,
                    'photos_taken': 0,
                    'weight': field.section_weight
                }
            
            if field.required:
                sections[section]['required'] += 1
                total_required += 1
                
                # Check if this field has a response
                if field.id in response_dict and response_dict[field.id]:
                    sections[section]['completed'] += 1
                    total_completed += 1
            
            # Handle photo requirements
            if field.field_type == 'photo':
                if field.required:
                    sections[section]['photos_required'] += 1
                
                # Check if photo exists for this field
                photo_exists = any(p for p in photos if p.requirement_id and field.question in p.description)
                if photo_exists:
                    sections[section]['photos_taken'] += 1
        
        # Calculate overall progress
        overall_progress = (total_completed / total_required * 100) if total_required > 0 else 0
        
        # Calculate section progress
        for section_name, section_data in sections.items():
            section_total = section_data['required']
            section_completed = section_data['completed']
            section_data['progress'] = (section_completed / section_total * 100) if section_total > 0 else 0
        
        session.close()
        
        return {
            'overall_progress': overall_progress,
            'sections': sections,
            'total_required': total_required,
            'total_completed': total_completed
        }
    
    def get_photo_requirements(self, survey_id):
        """Get photo requirements for a survey"""
        session = self.get_session()
        survey = session.query(Survey).get(survey_id)
        if not survey or not survey.template_id:
            session.close()
            return {}
        
        template = session.query(SurveyTemplate).get(survey.template_id)
        
        # Get existing photos
        photos = session.query(Photo).filter_by(survey_id=str(survey_id)).all()
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
        
        session.close()
        return {
            'survey_id': survey_id,
            'requirements_by_section': requirements_by_section
        }
    
    def mark_requirement_fulfillment(self, photo_id, requirement_id, fulfills=True):
        """Mark a photo as fulfilling a requirement"""
        session = self.get_session()
        photo = session.query(Photo).get(photo_id)
        if photo:
            photo.requirement_id = requirement_id
            photo.fulfills_requirement = fulfills
            session.commit()
        
        session.close()
