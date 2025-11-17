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