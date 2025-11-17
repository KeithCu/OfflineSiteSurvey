from flask import Flask, jsonify, request, g
import sqlite3
import json
import datetime
import enum
import os
import hashlib
from appdirs import user_data_dir
from store_survey_template import STORE_SURVEY_TEMPLATE
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import click

app = Flask(__name__)

DB_NAME = 'backend_main.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Load the cr-sqlite extension
def load_crsqlite_extension(db_conn, conn_record):
    # Look for the library in the user data directory
    data_dir = user_data_dir("crsqlite", "vlcn.io")
    lib_path = os.path.join(data_dir, 'crsqlite.so')

    if not os.path.exists(lib_path):
        # As a fallback for development, check the project's lib directory
        lib_path = os.path.join(os.path.dirname(__file__), 'lib', 'crsqlite.so')

    db_conn.enable_load_extension(True)
    db_conn.load_extension(lib_path)

event.listen(Engine, "connect", load_crsqlite_extension)


class SurveyStatus(enum.Enum):
    DRAFT = 'draft'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'

class ProjectStatus(enum.Enum):
    DRAFT = 'draft'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, server_default="Untitled")
    address = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, server_default="Untitled Survey")
    description = db.Column(db.Text)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False, server_default="1")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = db.Column(db.Enum(SurveyStatus), default=SurveyStatus.DRAFT)
    template_id = db.Column(db.Integer, db.ForeignKey('survey_template.id'), nullable=True)
    template = db.relationship('SurveyTemplate', backref='surveys', lazy=True)
    responses = db.relationship('SurveyResponse', backref='survey', lazy=True)

class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text)
    response_type = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # Phase 2 additions
    question_id = db.Column(db.Integer)  # Links to template field ID for conditional logic
    field_type = db.Column(db.String(50))  # Stores the field type from template

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(300))
    category = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class SurveyTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, server_default="Untitled Template")
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    fields = db.relationship('TemplateField', backref='template', lazy=True, cascade='all, delete-orphan')

class TemplateField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('survey_template.id'), nullable=False, server_default="1")
    field_type = db.Column(db.String(50))
    question = db.Column(db.String(500), nullable=False, server_default="")
    description = db.Column(db.Text)
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    section = db.Column(db.String(100))
    # Phase 2 additions
    conditions = db.Column(db.Text)  # JSON format for conditional logic
    photo_requirements = db.Column(db.Text)  # JSON format for photo requirements
    section_weight = db.Column(db.Integer, default=1)  # For weighted progress calculation

class Photo(db.Model):
    id = db.Column(db.String, primary_key=True)
    survey_id = db.Column(db.String, db.ForeignKey('survey.id'))
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'))  # For site overview photos
    image_data = db.Column(db.LargeBinary)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # Phase 4: Enhanced photo integrity
    hash_algo = db.Column(db.String(10), default='sha256')  # Hash algorithm used
    hash_value = db.Column(db.String(128))  # Cryptographic hash of image data
    size_bytes = db.Column(db.Integer)  # Size of image data in bytes
    # Phase 4: Performance optimizations
    thumbnail_data = db.Column(db.LargeBinary)  # Cached 200px thumbnail
    file_path = db.Column(db.String(500))  # File path for large photos (future use)
    # Phase 2 additions
    requirement_id = db.Column(db.String)  # Links to photo requirement
    fulfills_requirement = db.Column(db.Boolean, default=False)  # Tracks if this fulfills a requirement


def create_crr_tables(target, connection, **kw):
    crr_tables = ['projects', 'site', 'survey', 'survey_response', 'survey_template', 'template_field', 'photo']
    for table_name in crr_tables:
        connection.execute(text(f"SELECT crsql_as_crr('{table_name}');"))

event.listen(db.metadata, 'after_create', create_crr_tables)

def compute_photo_hash(image_data, algo='sha256'):
    """Compute cryptographic hash of image data"""
    if isinstance(image_data, bytes):
        return hashlib.new(algo, image_data).hexdigest()
    return None

@app.cli.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    with app.app_context():
        db.create_all()

        # Seed initial data
        if not AppConfig.query.filter_by(key='image_compression_quality').first():
            config = AppConfig(key='image_compression_quality', value='75')
            db.session.add(config)

        if not SurveyTemplate.query.filter_by(is_default=True).first():
            template = SurveyTemplate(name=STORE_SURVEY_TEMPLATE['name'], description=STORE_SURVEY_TEMPLATE['description'], category=STORE_SURVEY_TEMPLATE['category'], is_default=True)
            db.session.add(template)
            db.session.flush()
            for field_data in STORE_SURVEY_TEMPLATE['fields']:
                field = TemplateField(template_id=template.id, **field_data)
                db.session.add(field)

        db.session.commit()
    click.echo('Initialized the database.')

@app.cli.command('check-photo-integrity')
@click.option('--fix', is_flag=True, help='Attempt to fix integrity issues by re-computing hashes')
def check_photo_integrity_command(fix):
    """Check integrity of all photos in the database"""
    with app.app_context():
        photos = Photo.query.all()
        issues_found = 0
        fixed = 0

        for photo in photos:
            if not photo.image_data:
                continue

            current_hash = compute_photo_hash(photo.image_data, photo.hash_algo)
            size_matches = photo.size_bytes == len(photo.image_data)

            if photo.hash_value != current_hash or not size_matches:
                issues_found += 1
                click.echo(f"Integrity issue with photo {photo.id}:")
                if photo.hash_value != current_hash:
                    click.echo(f"  Hash mismatch: stored={photo.hash_value}, computed={current_hash}")
                if not size_matches:
                    click.echo(f"  Size mismatch: stored={photo.size_bytes}, actual={len(photo.image_data)}")

                if fix:
                    photo.hash_value = current_hash
                    photo.size_bytes = len(photo.image_data)
                    db.session.commit()
                    fixed += 1
                    click.echo(f"  Fixed photo {photo.id}")

        if issues_found == 0:
            click.echo("All photos passed integrity check")
        else:
            click.echo(f"Found {issues_found} integrity issues")
            if fix:
                click.echo(f"Fixed {fixed} photos")

@app.route('/api/surveys', methods=['GET'])
def get_surveys():
    surveys = Survey.query.all()
    return jsonify([{
        'id': s.id,
        'title': s.title,
        'description': s.description,
        'template_id': s.template_id,
        'status': s.status.value,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat()
    } for s in surveys])

@app.route('/api/surveys/<int:survey_id>', methods=['GET'])
def get_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    responses = [{
        'id': r.id,
        'question': r.question,
        'answer': r.answer,
        'response_type': r.response_type,
        'latitude': r.latitude,
        'longitude': r.longitude,
        'created_at': r.created_at.isoformat()
    } for r in survey.responses]

    return jsonify({
        'id': survey.id,
        'title': survey.title,
        'description': survey.description,
        'template_id': survey.template_id,
        'status': survey.status.value,
        'created_at': survey.created_at.isoformat(),
        'updated_at': survey.updated_at.isoformat(),
        'responses': responses
    })

@app.route('/api/surveys', methods=['POST'])
def create_survey():
    data = request.get_json()

    survey = Survey(
        title=data['title'],
        description=data.get('description'),
        site_id=data.get('site_id'),
        template_id=data.get('template_id'),
        status=SurveyStatus(data.get('status', 'draft'))
    )

    db.session.add(survey)
    db.session.commit()
    return jsonify({
        'id': survey.id,
        'template_id': survey.template_id,
        'message': 'Survey created successfully'
    }), 201

@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'status': p.status,
        'client_info': p.client_info,
        'due_date': p.due_date.isoformat() if p.due_date else None,
        'priority': p.priority,
        'created_at': p.created_at.isoformat(),
        'updated_at': p.updated_at.isoformat()
    } for p in projects])

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    project = Project(
        name=data['name'],
        description=data.get('description'),
        status=data.get('status', 'draft'),
        client_info=data.get('client_info'),
        due_date=datetime.datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        priority=data.get('priority', 'medium')
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({
        'id': project.id,
        'message': 'Project created successfully'
    }), 201

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    project.client_info = data.get('client_info', project.client_info)
    project.due_date = datetime.datetime.fromisoformat(data['due_date']) if data.get('due_date') else project.due_date
    project.priority = data.get('priority', project.priority)
    db.session.commit()
    return jsonify({'message': 'Project updated successfully'})

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'})

@app.route('/api/sites', methods=['GET'])
def get_sites():
    sites = Site.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'address': s.address,
        'latitude': s.latitude,
        'longitude': s.longitude,
        'notes': s.notes,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat()
    } for s in sites])

@app.route('/api/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = Site.query.get_or_404(site_id)
    return jsonify({
        'id': site.id,
        'name': site.name,
        'address': site.address,
        'latitude': site.latitude,
        'longitude': site.longitude,
        'notes': site.notes,
        'created_at': site.created_at.isoformat(),
        'updated_at': site.updated_at.isoformat()
    })

@app.route('/api/sites', methods=['POST'])
def create_site():
    data = request.get_json()
    site = Site(
        name=data['name'],
        address=data.get('address'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        notes=data.get('notes')
    )
    db.session.add(site)
    db.session.commit()
    return jsonify({'id': site.id}), 201

@app.route('/api/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    site = Site.query.get_or_404(site_id)
    data = request.get_json()
    site.name = data.get('name', site.name)
    site.address = data.get('address', site.address)
    site.latitude = data.get('latitude', site.latitude)
    site.longitude = data.get('longitude', site.longitude)
    site.notes = data.get('notes', site.notes)
    db.session.commit()
    return jsonify({'message': 'Site updated successfully'})

@app.route('/api/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    site = Site.query.get_or_404(site_id)
    db.session.delete(site)
    db.session.commit()
    return jsonify({'message': 'Site deleted successfully'})

@app.route('/api/templates', methods=['GET'])
def get_templates():
    templates = SurveyTemplate.query.all()
    return jsonify([{'id': t.id, 'name': t.name, 'fields': [{'id': f.id, 'question': f.question} for f in t.fields]} for t in templates])

@app.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    template = SurveyTemplate.query.get_or_404(template_id)
    fields = [{'id': f.id, 'field_type': f.field_type, 'question': f.question, 'description': f.description, 'required': f.required, 'options': f.options, 'order_index': f.order_index, 'section': f.section} for f in sorted(template.fields, key=lambda x: x.order_index)]
    return jsonify({
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'category': template.category,
        'is_default': template.is_default,
        'fields': fields
    })

@app.route('/api/changes', methods=['POST'])
def apply_changes():
    changes = request.get_json()
    conn = db.engine.raw_connection()
    cursor = conn.cursor()

    integrity_issues = []

    for change in changes:
        # Verify photo integrity if this is a photo table change
        if change['table'] == 'photo' and change['cid'] == 'image_data' and change['val']:
            # Extract photo ID from pk (format: '{"id":"photo_id"}')
            try:
                pk_data = json.loads(change['pk'])
                photo_id = pk_data.get('id')

                # Check if we have existing photo data to compare
                existing_photo = Photo.query.get(photo_id)
                if existing_photo and existing_photo.hash_value:
                    # Verify the incoming data matches expected hash
                    incoming_hash = compute_photo_hash(change['val'], existing_photo.hash_algo)
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

        cursor.execute(
            "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
        )

    conn.commit()
    conn.close()

    response = {'message': 'Changes applied successfully'}
    if integrity_issues:
        response['integrity_issues'] = integrity_issues
        response['message'] = 'Changes applied with integrity issues'

    return jsonify(response)

@app.route('/api/changes', methods=['GET'])
def get_changes():
    version = request.args.get('version', 0)
    site_id = request.args.get('site_id')

    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row

    cursor.execute(
        "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id != ?",
        (version, site_id)
    )

    changes = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in changes])

# Phase 2 API Endpoints

@app.route('/api/templates/<int:template_id>/conditional-fields', methods=['GET'])
def get_conditional_fields(template_id):
    """Get template fields with conditional logic information"""
    template = SurveyTemplate.query.get_or_404(template_id)
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
    
    return jsonify({
        'template_id': template_id,
        'fields': fields
    })

@app.route('/api/surveys/<int:survey_id>/evaluate-conditions', methods=['POST'])
def evaluate_survey_conditions(survey_id):
    """Evaluate which fields should be visible based on current responses"""
    survey = Survey.query.get_or_404(survey_id)
    data = request.get_json()
    current_responses = data.get('responses', [])
    
    # Get template fields
    if survey.template_id:
        template = SurveyTemplate.query.get(survey.template_id)
        all_fields = sorted(template.fields, key=lambda x: x.order_index)
    else:
        return jsonify({'error': 'Survey has no template'}), 400
    
    visible_fields = []
    
    for field in all_fields:
        # Check if field has conditions
        if field.conditions:
            conditions = json.loads(field.conditions)
            if should_show_field(conditions, current_responses):
                visible_fields.append(field.id)
        else:
            # No conditions, always show
            visible_fields.append(field.id)
    
    return jsonify({
        'survey_id': survey_id,
        'visible_fields': visible_fields
    })

@app.route('/api/surveys/<int:survey_id>/progress', methods=['GET'])
def get_survey_progress(survey_id):
    """Get detailed progress information for a survey"""
    survey = Survey.query.get_or_404(survey_id)
    
    # Get all responses
    responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
    response_dict = {r.question_id: r.answer for r in responses if r.question_id}
    
    # Get all photos
    photos = Photo.query.filter_by(survey_id=str(survey_id)).all()
    
    # Get template fields if available
    if survey.template_id:
        template = SurveyTemplate.query.get(survey.template_id)
        fields = template.fields
    else:
        fields = []
    
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
    
    return jsonify({
        'overall_progress': overall_progress,
        'sections': sections,
        'total_required': total_required,
        'total_completed': total_completed
    })

@app.route('/api/surveys/<int:survey_id>/photo-requirements', methods=['GET'])
def get_photo_requirements(survey_id):
    """Get photo requirements for a survey"""
    survey = Survey.query.get_or_404(survey_id)
    
    if not survey.template_id:
        return jsonify({'error': 'Survey has no template'}), 400
    
    template = SurveyTemplate.query.get(survey.template_id)
    
    # Get existing photos
    photos = Photo.query.filter_by(survey_id=str(survey_id)).all()
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
    
    return jsonify({
        'survey_id': survey_id,
        'requirements_by_section': requirements_by_section
    })

@app.route('/api/photos/requirement-fulfillment', methods=['POST'])
def mark_requirement_fulfillment():
    """Mark a photo as fulfilling a requirement"""
    data = request.get_json()
    photo_id = data.get('photo_id')
    requirement_id = data.get('requirement_id')
    fulfills = data.get('fulfills', True)

    photo = Photo.query.get_or_404(photo_id)
    photo.requirement_id = requirement_id
    photo.fulfills_requirement = fulfills
    db.session.commit()

    return jsonify({
        'photo_id': photo_id,
        'requirement_id': requirement_id,
        'fulfills': fulfills,
        'message': 'Photo requirement fulfillment updated'
    })

@app.route('/api/photos/<photo_id>/integrity', methods=['GET'])
def get_photo_integrity(photo_id):
    """Get integrity information for a photo"""
    photo = Photo.query.get_or_404(photo_id)

    # Compute current hash of stored image data
    current_hash = compute_photo_hash(photo.image_data, photo.hash_algo)

    integrity_status = {
        'photo_id': photo_id,
        'stored_hash': photo.hash_value,
        'current_hash': current_hash,
        'hash_matches': photo.hash_value == current_hash,
        'size_bytes': photo.size_bytes,
        'actual_size': len(photo.image_data) if photo.image_data else 0,
        'size_matches': photo.size_bytes == len(photo.image_data) if photo.image_data else False
    }

    return jsonify(integrity_status)

def should_show_field(conditions, responses):
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

if __name__ == '__main__':
    app.run(debug=True)
