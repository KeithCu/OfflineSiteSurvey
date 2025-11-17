"""Templates blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import json
from ..models import db, SurveyTemplate, TemplateField
from ..utils import should_show_field


bp = Blueprint('templates', __name__, url_prefix='/api')


@bp.route('/templates', methods=['GET'])
def get_templates():
    templates = SurveyTemplate.query.all()
    template_list = []
    for t in templates:
        try:
            section_tags = json.loads(t.section_tags) if t.section_tags else {}
        except json.JSONDecodeError:
            section_tags = {}
        template_list.append({
            'id': t.id,
            'name': t.name,
            'fields': [{'id': f.id, 'question': f.question} for f in t.fields],
            'section_tags': section_tags
        })
    return jsonify(template_list)


@bp.route('/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    template = db.get_or_404(SurveyTemplate, template_id)
    fields = [{'id': f.id, 'field_type': f.field_type, 'question': f.question, 'description': f.description, 'required': f.required, 'options': f.options, 'order_index': f.order_index, 'section': f.section} for f in sorted(template.fields, key=lambda x: x.order_index)]
    try:
        section_tags = json.loads(template.section_tags) if template.section_tags else {}
    except json.JSONDecodeError:
        section_tags = {}
    return jsonify({
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'category': template.category,
        'is_default': template.is_default,
        'fields': fields,
        'section_tags': section_tags
    })


@bp.route('/templates/<int:template_id>/conditional-fields', methods=['GET'])
def get_conditional_fields(template_id):
    """Get template fields with conditional logic information"""
    template = db.get_or_404(SurveyTemplate, template_id)
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
    try:
        section_tags = json.loads(template.section_tags) if template.section_tags else {}
    except json.JSONDecodeError:
        section_tags = {}
    
    return jsonify({
        'template_id': template_id,
        'fields': fields,
        'section_tags': section_tags
    })


@bp.route('/templates/<int:template_id>/section-tags', methods=['PUT'])
def update_section_tags(template_id):
    """Update section tag mappings for a template"""
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request payload must be a JSON object'}), 400

    section_tags = data.get('section_tags')
    if not isinstance(section_tags, dict):
        return jsonify({'error': 'section_tags must be a JSON object'}), 400

    cleaned = {}
    for section, tags in section_tags.items():
        if not isinstance(section, str):
            continue
        if not isinstance(tags, list):
            return jsonify({'error': f'Tags for section {section} must be a list'}), 400
        cleaned[section] = [str(tag).strip() for tag in tags if str(tag).strip()]

    template = db.get_or_404(SurveyTemplate, template_id)
    try:
        template.section_tags = json.dumps(cleaned)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update section tags: {e}'}), 500

    return jsonify({'template_id': template_id, 'section_tags': cleaned})


@bp.route('/surveys/<int:survey_id>/evaluate-conditions', methods=['POST'])
def evaluate_survey_conditions(survey_id):
    """Evaluate which fields should be visible based on current responses"""
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    current_responses = data.get('responses', [])
    if not isinstance(current_responses, list):
        return jsonify({'error': 'responses must be a list'}), 400

    from ..models import Survey
    survey = Survey.query.get_or_404(survey_id)
    
    # Get template fields
    if survey.template_id:
        template = db.session.get(SurveyTemplate, survey.template_id)
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


@bp.route('/surveys/<int:survey_id>/progress', methods=['GET'])
def get_survey_progress(survey_id):
    """Get detailed progress information for a survey"""
    from ..models import Survey, SurveyResponse, Photo
    survey = Survey.query.get_or_404(survey_id)
    
    # Get all responses
    responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
    response_dict = {r.question_id: r.answer for r in responses if r.question_id}
    
    # Get all photos
    photos = Photo.query.filter_by(survey_id=str(survey_id)).all()
    
    # Get template fields if available
    fields = []
    if survey.template_id:
        template = db.session.get(SurveyTemplate, survey.template_id)
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
    
    return jsonify({
        'overall_progress': overall_progress,
        'sections': sections,
        'total_required': total_required,
        'total_completed': total_completed
    })


@bp.route('/surveys/<int:survey_id>/photo-requirements', methods=['GET'])
def get_photo_requirements(survey_id):
    """Get photo requirements for a survey"""
    from ..models import Survey, Photo
    survey = Survey.query.get_or_404(survey_id)
    
    if not survey.template_id:
        return jsonify({'error': 'Survey has no template'}), 400
    
    template = db.session.get(SurveyTemplate, survey.template_id)
    
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