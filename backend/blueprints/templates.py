"""Templates blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import json
from ..models import db, SurveyTemplate, TemplateField
from ..utils import should_show_field
from shared.validation import ValidationError, validate_string_length, sanitize_html
from shared.schemas import (
    SurveyTemplateResponse, TemplateListItem, TemplateFieldDetailResponse,
    TemplateConditionalFieldsResponse, ConditionalFieldResponse,
    SectionTagsUpdateRequest, SectionTagsUpdateResponse,
    SurveyConditionEvaluationRequest, SurveyConditionEvaluationResponse,
    SurveyProgressResponse, SectionProgress, PhotoRequirementsResponse, PhotoRequirementData
)
from pydantic import ValidationError as PydanticValidationError


bp = Blueprint('templates', __name__, url_prefix='/api')


@bp.route('/templates', methods=['GET'])
def get_templates():
    # Pagination parameters with validation
    try:
        page = request.args.get('page', 1, type=int)
        if page < 1:
            return jsonify({'error': 'page must be at least 1'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'page must be an integer'}), 400
    
    try:
        per_page = request.args.get('per_page', 50, type=int)
        if per_page < 1:
            return jsonify({'error': 'per_page must be at least 1'}), 400
        per_page = min(per_page, 100)  # Max 100 per page
    except (ValueError, TypeError):
        return jsonify({'error': 'per_page must be an integer'}), 400

    # Query with pagination
    pagination = SurveyTemplate.query.paginate(page=page, per_page=per_page, error_out=False)
    templates = pagination.items

    template_list = []
    for t in templates:
        try:
            section_tags = json.loads(t.section_tags) if t.section_tags else {}
        except json.JSONDecodeError:
            section_tags = {}
        template_list.append(TemplateListItem(
            id=t.id,
            name=t.name,
            fields=[{'id': f.id, 'question': f.question} for f in t.fields],
            section_tags=section_tags
        ).model_dump(mode='json'))
    
    return jsonify({
        'templates': template_list,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@bp.route('/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    template = db.get_or_404(SurveyTemplate, template_id)
    return jsonify(SurveyTemplateResponse.model_validate(template).model_dump(mode='json'))


@bp.route('/templates/<int:template_id>/conditional-fields', methods=['GET'])
def get_conditional_fields(template_id):
    """Get template fields with conditional logic information"""
    template = db.get_or_404(SurveyTemplate, template_id)
    fields = []
    
    for field in sorted(template.fields, key=lambda x: x.order_index):
        field_data = ConditionalFieldResponse(
            id=field.id,
            field_type=field.field_type,
            question=field.question,
            description=field.description,
            required=field.required,
            options=field.options,
            order_index=field.order_index,
            section=field.section,
            section_weight=field.section_weight,
            conditions=json.loads(field.conditions) if field.conditions else None,
            photo_requirements=json.loads(field.photo_requirements) if field.photo_requirements else None
        )
        fields.append(field_data.model_dump(mode='json'))
    
    try:
        section_tags = json.loads(template.section_tags) if template.section_tags else {}
    except json.JSONDecodeError:
        section_tags = {}
    
    response = TemplateConditionalFieldsResponse(
        template_id=template_id,
        fields=fields,
        section_tags=section_tags
    )
    return jsonify(response.model_dump(mode='json'))


@bp.route('/templates/<int:template_id>/section-tags', methods=['PUT'])
def update_section_tags(template_id):
    """Update section tag mappings for a template"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        request_schema = SectionTagsUpdateRequest(**data)
    except PydanticValidationError as e:
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        return jsonify({'error': '; '.join(errors)}), 400
    except Exception as e:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    template = db.get_or_404(SurveyTemplate, template_id)
    try:
        # Sanitize tags
        cleaned = {}
        for section, tags in request_schema.section_tags.items():
            sanitized_tags = [sanitize_html(tag) for tag in tags]
            cleaned[section] = sanitized_tags
        
        template.section_tags = json.dumps(cleaned)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update section tags: {e}'}), 500

    response = SectionTagsUpdateResponse(
        template_id=template_id,
        section_tags=cleaned
    )
    return jsonify(response.model_dump(mode='json'))


@bp.route('/surveys/<int:survey_id>/evaluate-conditions', methods=['POST'])
def evaluate_survey_conditions(survey_id):
    """Evaluate which fields should be visible based on current responses"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        request_schema = SurveyConditionEvaluationRequest(**data)
    except PydanticValidationError as e:
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        return jsonify({'error': '; '.join(errors)}), 400
    except Exception as e:
        return jsonify({'error': 'Invalid JSON data'}), 400

    from ..models import Survey
    survey = Survey.query.get_or_404(survey_id)
    
    # Get template fields
    if survey.template_id:
        template = db.session.get(SurveyTemplate, survey.template_id)
        all_fields = sorted(template.fields, key=lambda x: x.order_index)
    else:
        return jsonify({'error': 'Survey has no template'}), 400
    
    # Pre-compute response lookup once for all field evaluations
    from shared.utils import build_response_lookup
    response_lookup = build_response_lookup(request_schema.responses)
    
    visible_fields = []
    
    for field in all_fields:
        # Check if field has conditions
        if field.conditions:
            conditions = json.loads(field.conditions)
            if should_show_field(conditions, response_lookup):
                visible_fields.append(field.id)
        else:
            # No conditions, always show
            visible_fields.append(field.id)
    
    response = SurveyConditionEvaluationResponse(
        survey_id=survey_id,
        visible_fields=visible_fields
    )
    return jsonify(response.model_dump(mode='json'))


@bp.route('/surveys/<int:survey_id>/progress', methods=['GET'])
def get_survey_progress(survey_id):
    """Get detailed progress information for a survey"""
    from ..models import Survey, SurveyResponse, Photo
    survey = Survey.query.get_or_404(survey_id)
    
    # Get all responses
    responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
    response_dict = {r.question_id: r.answer for r in responses if r.question_id}
    
    # Get all photos
    photos = Photo.query.filter_by(survey_id=survey_id).all()
    
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
            sections[section] = SectionProgress(
                required=0,
                completed=0,
                photos_required=0,
                photos_taken=0,
                weight=field.section_weight,
                progress=0.0
            )
        
        if field.required:
            sections[section].required += 1
            total_required += 1
            
            # Check if this field has a response
            if field.id in response_dict and response_dict[field.id]:
                sections[section].completed += 1
                total_completed += 1
        
        # Handle photo requirements
        if field.field_type == 'photo':
            if field.required:
                sections[section].photos_required += 1
            
            # Check if photo exists for this field
            photo_exists = any(p for p in photos if p.requirement_id and field.question in p.description)
            if photo_exists:
                sections[section].photos_taken += 1
    
    # Calculate overall progress
    overall_progress = (total_completed / total_required * 100) if total_required > 0 else 0
    
    # Calculate section progress
    sections_dict = {}
    for section_name, section_data in sections.items():
        section_total = section_data.required
        section_completed = section_data.completed
        section_data.progress = (section_completed / section_total * 100) if section_total > 0 else 0
        sections_dict[section_name] = section_data.model_dump(mode='json')
    
    response = SurveyProgressResponse(
        overall_progress=overall_progress,
        sections=sections_dict,
        total_required=total_required,
        total_completed=total_completed
    )
    return jsonify(response.model_dump(mode='json'))


@bp.route('/surveys/<int:survey_id>/photo-requirements', methods=['GET'])
def get_photo_requirements(survey_id):
    """Get photo requirements for a survey"""
    from ..models import Survey, Photo
    survey = Survey.query.get_or_404(survey_id)
    
    if not survey.template_id:
        return jsonify({'error': 'Survey has no template'}), 400
    
    template = db.session.get(SurveyTemplate, survey.template_id)
    
    # Get existing photos
    photos = Photo.query.filter_by(survey_id=survey_id).all()
    existing_photo_requirements = {p.requirement_id: p for p in photos if p.requirement_id}
    
    requirements_by_section = {}
    
    for field in sorted(template.fields, key=lambda x: x.order_index):
        if field.field_type == 'photo' and field.photo_requirements:
            section = field.section or 'General'
            if section not in requirements_by_section:
                requirements_by_section[section] = []
            
            photo_req_data = json.loads(field.photo_requirements)
            requirement = PhotoRequirementData(
                field_id=field.id,
                field_question=field.question,
                taken=field.id in existing_photo_requirements
            )
            # Merge photo_req_data dict with requirement data
            req_dict = requirement.model_dump(mode='json')
            req_dict.update(photo_req_data)
            requirements_by_section[section].append(req_dict)
    
    response = PhotoRequirementsResponse(
        survey_id=survey_id,
        requirements_by_section=requirements_by_section
    )
    return jsonify(response.model_dump(mode='json'))