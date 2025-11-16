from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import datetime
import enum
import json
from store_survey_template import STORE_SURVEY_TEMPLATE

app = Flask(__name__)

# For simplicity, we'll use a file-based SQLite database for the backend.
# In production, you would change this to PostgreSQL or another robust DB.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///backend_main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class SurveyStatus(enum.Enum):
    DRAFT = 'draft'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    store_name = db.Column(db.String(100))
    store_address = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = db.Column(db.Enum(SurveyStatus), default=SurveyStatus.DRAFT)
    responses = db.relationship('SurveyResponse', backref='survey', lazy=True)

class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text)
    response_type = db.Column(db.String(50))  # text, photo, measurement, etc.
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)  # JSON string for complex values
    description = db.Column(db.String(300))
    category = db.Column(db.String(50))  # 'image', 'sync', 'ui', etc.
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class SurveyTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'store', 'office', 'warehouse', etc.
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    fields = db.relationship('TemplateField', backref='template', lazy=True, cascade='all, delete-orphan')

class TemplateField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('survey_template.id'), nullable=False)
    field_type = db.Column(db.String(50))  # 'text', 'photo', 'yesno', 'rating', 'measurement'
    question = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.Text)  # JSON string for multiple choice options
    order_index = db.Column(db.Integer, default=0)
    section = db.Column(db.String(100))  # Group fields into sections

# Create tables and initialize default data
with app.app_context():
    db.create_all()

    # Initialize default configuration
    if not AppConfig.query.filter_by(key='image_compression_quality').first():
        config = AppConfig(
            key='image_compression_quality',
            value='75',
            description='Image compression quality (1-100, higher = better quality but larger files)',
            category='image'
        )
        db.session.add(config)

    if not AppConfig.query.filter_by(key='auto_sync_interval').first():
        config = AppConfig(
            key='auto_sync_interval',
            value='300',  # 5 minutes
            description='Auto-sync interval in seconds (0 = disabled)',
            category='sync'
        )
        db.session.add(config)

    if not AppConfig.query.filter_by(key='max_offline_days').first():
        config = AppConfig(
            key='max_offline_days',
            value='30',
            description='Maximum days to keep data offline before requiring sync',
            category='sync'
        )
        db.session.add(config)

    # Initialize default store survey template
    if not SurveyTemplate.query.filter_by(is_default=True).first():
        template = SurveyTemplate(
            name=STORE_SURVEY_TEMPLATE['name'],
            description=STORE_SURVEY_TEMPLATE['description'],
            category=STORE_SURVEY_TEMPLATE['category'],
            is_default=STORE_SURVEY_TEMPLATE['is_default']
        )
        db.session.add(template)
        db.session.flush()  # Get the template ID

        # Add template fields from the external template file
        for field_data in STORE_SURVEY_TEMPLATE['fields']:
            field = TemplateField(
                template_id=template.id,
                field_type=field_data['field_type'],
                question=field_data['question'],
                description=field_data.get('description'),
                required=field_data.get('required', False),
                options=json.dumps(field_data.get('options')) if field_data.get('options') else None,
                order_index=field_data['order_index'],
                section=field_data['section']
            )
            db.session.add(field)

    db.session.commit()

@app.route('/api/surveys', methods=['GET'])
def get_surveys():
    """Get all surveys"""
    surveys = Survey.query.all()
    return jsonify([{
        'id': s.id,
        'title': s.title,
        'description': s.description,
        'store_name': s.store_name,
        'store_address': s.store_address,
        'status': s.status.value,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat()
    } for s in surveys])

@app.route('/api/surveys/<int:survey_id>', methods=['GET'])
def get_survey(survey_id):
    """Get a specific survey"""
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
        'store_name': survey.store_name,
        'store_address': survey.store_address,
        'status': survey.status.value,
        'created_at': survey.created_at.isoformat(),
        'updated_at': survey.updated_at.isoformat(),
        'responses': responses
    })

@app.route('/api/surveys', methods=['POST'])
def create_survey():
    """Create a new survey"""
    data = request.get_json()

    survey = Survey(
        title=data['title'],
        description=data.get('description'),
        store_name=data.get('store_name'),
        store_address=data.get('store_address'),
        status=SurveyStatus(data.get('status', 'draft'))
    )

    db.session.add(survey)
    db.session.commit()

    return jsonify({
        'id': survey.id,
        'message': 'Survey created successfully'
    }), 201

@app.route('/api/surveys/<int:survey_id>/responses', methods=['POST'])
def add_response(survey_id):
    """Add a response to a survey"""
    survey = Survey.query.get_or_404(survey_id)
    data = request.get_json()

    response = SurveyResponse(
        survey_id=survey_id,
        question=data['question'],
        answer=data.get('answer'),
        response_type=data.get('response_type', 'text'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )

    db.session.add(response)
    db.session.commit()

    return jsonify({
        'id': response.id,
        'message': 'Response added successfully'
    }), 201

@app.route('/api/surveys/<int:survey_id>/sync', methods=['POST'])
def sync_survey_responses(survey_id):
    """Sync multiple responses from the frontend (for offline functionality)"""
    survey = Survey.query.get_or_404(survey_id)
    data = request.get_json()

    responses = []
    for response_data in data.get('responses', []):
        # Compress images if present
        answer = response_data.get('answer')
        if response_data.get('response_type') == 'photo' and answer:
            # Note: Image compression will be handled by the frontend app
            # This endpoint just stores the already compressed data
            pass

        response = SurveyResponse(
            survey_id=survey_id,
            question=response_data['question'],
            answer=answer,
            response_type=response_data.get('response_type', 'text'),
            latitude=response_data.get('latitude'),
            longitude=response_data.get('longitude')
        )
        responses.append(response)
        db.session.add(response)

    db.session.commit()

    return jsonify({
        'message': f'Synced {len(responses)} responses successfully'
    })

# Configuration endpoints
@app.route('/api/config', methods=['GET'])
def get_config():
    """Get all configuration options"""
    configs = AppConfig.query.all()
    config_dict = {}
    for config in configs:
        try:
            # Try to parse as JSON
            config_dict[config.key] = json.loads(config.value)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, return as string
            config_dict[config.key] = config.value

    return jsonify(config_dict)

@app.route('/api/config/<key>', methods=['GET'])
def get_config_value(key):
    """Get a specific configuration value"""
    config = AppConfig.query.filter_by(key=key).first()
    if not config:
        return jsonify({'error': 'Configuration not found'}), 404

    try:
        value = json.loads(config.value)
    except (json.JSONDecodeError, TypeError):
        value = config.value

    return jsonify({
        'key': config.key,
        'value': value,
        'description': config.description,
        'category': config.category
    })

@app.route('/api/config/<key>', methods=['PUT'])
def set_config_value(key):
    """Set a configuration value"""
    data = request.get_json()
    value = data.get('value')

    if value is None:
        return jsonify({'error': 'Value is required'}), 400

    # Convert to JSON string if it's a complex value
    if isinstance(value, (dict, list)):
        value_str = json.dumps(value)
    else:
        value_str = str(value)

    config = AppConfig.query.filter_by(key=key).first()
    if config:
        config.value = value_str
        config.updated_at = datetime.datetime.utcnow()
    else:
        # Create new config
        config = AppConfig(
            key=key,
            value=value_str,
            description=data.get('description', ''),
            category=data.get('category', 'general')
        )
        db.session.add(config)

    db.session.commit()
    return jsonify({'message': 'Configuration updated successfully'})

# Template endpoints
@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all survey templates"""
    templates = SurveyTemplate.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'category': t.category,
        'is_default': t.is_default,
        'field_count': len(t.fields),
        'created_at': t.created_at.isoformat(),
        'updated_at': t.updated_at.isoformat()
    } for t in templates])

@app.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Get a specific template with all fields"""
    template = SurveyTemplate.query.get_or_404(template_id)
    fields = [{
        'id': f.id,
        'field_type': f.field_type,
        'question': f.question,
        'description': f.description,
        'required': f.required,
        'options': json.loads(f.options) if f.options else None,
        'order_index': f.order_index,
        'section': f.section
    } for f in sorted(template.fields, key=lambda x: x.order_index)]

    return jsonify({
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'category': template.category,
        'is_default': template.is_default,
        'fields': fields,
        'created_at': template.created_at.isoformat(),
        'updated_at': template.updated_at.isoformat()
    })

@app.route('/api/templates', methods=['POST'])
def create_template():
    """Create a new survey template"""
    data = request.get_json()

    template = SurveyTemplate(
        name=data['name'],
        description=data.get('description'),
        category=data.get('category', 'general'),
        is_default=data.get('is_default', False)
    )

    # Add fields if provided
    for field_data in data.get('fields', []):
        field = TemplateField(
            field_type=field_data['field_type'],
            question=field_data['question'],
            description=field_data.get('description'),
            required=field_data.get('required', False),
            options=json.dumps(field_data.get('options')) if field_data.get('options') else None,
            order_index=field_data.get('order_index', 0),
            section=field_data.get('section')
        )
        template.fields.append(field)

    db.session.add(template)
    db.session.commit()

    return jsonify({
        'id': template.id,
        'message': 'Template created successfully'
    }), 201

@app.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """Update a survey template"""
    template = SurveyTemplate.query.get_or_404(template_id)
    data = request.get_json()

    template.name = data.get('name', template.name)
    template.description = data.get('description', template.description)
    template.category = data.get('category', template.category)
    template.is_default = data.get('is_default', template.is_default)
    template.updated_at = datetime.datetime.utcnow()

    # Update fields if provided
    if 'fields' in data:
        # Remove existing fields
        TemplateField.query.filter_by(template_id=template_id).delete()

        # Add new fields
        for field_data in data['fields']:
            field = TemplateField(
                template_id=template_id,
                field_type=field_data['field_type'],
                question=field_data['question'],
                description=field_data.get('description'),
                required=field_data.get('required', False),
                options=json.dumps(field_data.get('options')) if field_data.get('options') else None,
                order_index=field_data.get('order_index', 0),
                section=field_data.get('section')
            )
            db.session.add(field)

    db.session.commit()

    return jsonify({'message': 'Template updated successfully'})

@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a survey template"""
    template = SurveyTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()

    return jsonify({'message': 'Template deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True)
