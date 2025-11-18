"""Surveys blueprint for Flask API."""
from flask import Blueprint, jsonify, request
from ..models import db, Survey, SurveyResponse, SurveyStatus


bp = Blueprint('surveys', __name__, url_prefix='/api')


@bp.route('/surveys', methods=['GET'])
def get_surveys():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)  # Max 100 per page

    # Query with pagination
    pagination = Survey.query.paginate(page=page, per_page=per_page, error_out=False)
    surveys = pagination.items

    return jsonify({
        'surveys': [{
            'id': s.id,
            'title': s.title,
            'description': s.description,
            'template_id': s.template_id,
            'status': s.status,
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat()
        } for s in surveys],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@bp.route('/surveys/<int:survey_id>', methods=['GET'])
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
        'status': survey.status,
        'created_at': survey.created_at.isoformat(),
        'updated_at': survey.updated_at.isoformat(),
        'responses': responses
    })


@bp.route('/surveys', methods=['POST'])
def create_survey():
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    # Validate required fields
    if 'title' not in data:
        return jsonify({'error': 'title field is required'}), 400

    title = data['title']
    if not isinstance(title, str) or not title.strip():
        return jsonify({'error': 'title must be a non-empty string'}), 400

    # Validate optional fields
    description = data.get('description')
    if description is not None and not isinstance(description, str):
        return jsonify({'error': 'description must be a string'}), 400

    # Validate site_id exists and is required
    site_id = data.get('site_id')
    if site_id is None:
        return jsonify({'error': 'site_id is required'}), 400
    try:
        site_id = int(site_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'site_id must be an integer'}), 400

    from ..utils import validate_foreign_key
    if not validate_foreign_key('sites', 'id', site_id):
        return jsonify({'error': f'site_id {site_id} does not exist'}), 400

    # Validate template_id exists if provided
    template_id = data.get('template_id')
    if template_id is not None:
        try:
            template_id = int(template_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'template_id must be an integer'}), 400

        if not validate_foreign_key('survey_template', 'id', template_id):
            return jsonify({'error': f'template_id {template_id} does not exist'}), 400

    status_str = data.get('status', 'draft')
    if not isinstance(status_str, str):
        return jsonify({'error': 'status must be a string'}), 400

    try:
        status = SurveyStatus(status_str)
    except ValueError:
        return jsonify({'error': f'status must be one of: {[s.value for s in SurveyStatus]}'}), 400

    try:
        survey = Survey(
            title=title.strip(),
            description=description.strip() if description else None,
            site_id=site_id,
            template_id=template_id,
            status=status
        )

        db.session.add(survey)
        db.session.commit()
        return jsonify({
            'id': survey.id,
            'template_id': survey.template_id,
            'message': 'Survey created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create survey: {str(e)}'}), 500


@bp.route('/surveys/<int:survey_id>', methods=['DELETE'])
def delete_survey(survey_id):
    from ..utils import cascade_delete_survey

    try:
        summary = cascade_delete_survey(survey_id)
        db.session.commit()

        return jsonify({
            'message': 'Survey deleted successfully',
            'summary': summary
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete survey: {str(e)}'}), 500