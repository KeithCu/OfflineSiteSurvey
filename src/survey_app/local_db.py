from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey
import json
import os
from datetime import datetime
import uuid
import zlib
from appdirs import user_data_dir

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
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
    status = Column(String(50), default='draft')
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
    image_data = Column(LargeBinary)
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    category = Column(String(50), default='general')
    exif_data = Column(Text)  # JSON string of EXIF data
    created_at = Column(DateTime, default=datetime.utcnow)
    crc = Column(Integer)
    # Phase 2 additions
    requirement_id = Column(String)  # Links to photo requirement
    fulfills_requirement = Column(Boolean, default=False)  # Tracks if this fulfills a requirement


class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        """Initialize the local database"""
        self.db_path = db_path
        self.site_id = str(uuid.uuid4())
        self.engine = create_engine(f'sqlite:///{self.db_path}')

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

    def get_photos(self, survey_id=None, category=None, search_term=None):
        session = self.get_session()
        query = session.query(Photo)
        if survey_id:
            query = query.filter_by(survey_id=survey_id)
        if category:
            query = query.filter_by(category=category)
        if search_term:
            query = query.filter(Photo.description.contains(search_term))
        photos = query.order_by(Photo.created_at.desc()).all()
        session.close()
        return photos

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
        session = self.get_session()
        conn = session.connection()
        raw_conn = conn.connection
        cursor = raw_conn.cursor()

        for change in changes:
            cursor.execute(
                "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
            )

        session.commit()
        session.close()

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
