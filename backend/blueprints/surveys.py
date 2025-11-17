"""Surveys blueprint for Flask API."""
from flask import Blueprint, jsonify, request
from ..models import db, Survey, SurveyResponse, SurveyStatus


bp = Blueprint('surveys', __name__, url_prefix='/api')


@bp.route('/surveys', methods=['GET'])
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
        'status': survey.status.value,
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

    site_id = data.get('site_id')
    if site_id is not None:
        try:
            site_id = int(site_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'site_id must be an integer'}), 400

    template_id = data.get('template_id')
    if template_id is not None:
        try:
            template_id = int(template_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'template_id must be an integer'}), 400

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