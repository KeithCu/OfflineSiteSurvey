"""Surveys blueprint for Flask API."""
from flask import Blueprint, jsonify
from ..models import Survey, SurveyResponse
from ..base.generic_crud import GenericCRUD, register_crud_routes
from shared.validation import ValidationError
from shared.schemas import SurveyCreate, SurveyUpdate, SurveyResponseSchema, SurveyWithResponsesResponse, SurveyResponseResponse
from ..utils import validate_foreign_key, cascade_delete_survey

bp = Blueprint('surveys', __name__, url_prefix='/api')


def validate_survey_foreign_keys(data):
    """Pre-create hook to validate site_id and template_id exist."""
    site_id = data.get('site_id')
    if site_id and not validate_foreign_key('sites', 'id', site_id):
        raise ValidationError(f'site_id {site_id} does not exist')
    
    template_id = data.get('template_id')
    if template_id is not None and not validate_foreign_key('survey_template', 'id', template_id):
        raise ValidationError(f'template_id {template_id} does not exist')
    
    return data


def serialize_survey_with_responses(survey):
    """Serialize survey with responses included."""
    survey_data = SurveyResponseSchema.model_validate(survey).model_dump(mode='json')
    responses = [SurveyResponseResponse.model_validate(r).model_dump(mode='json') for r in survey.responses]
    return SurveyWithResponsesResponse(**survey_data, responses=responses).model_dump(mode='json')


# Create generic CRUD instance
survey_crud = GenericCRUD(
    model=Survey,
    create_schema=SurveyCreate,
    update_schema=SurveyUpdate,
    response_schema=SurveyResponseSchema,
    logger_name='surveys',
    pre_create_hook=validate_survey_foreign_keys,
    cascade_delete_func=cascade_delete_survey
)


# Override get_detail to include responses
def get_detail_with_responses(resource_id):
    """Get single survey by ID with responses included."""
    survey = Survey.query.get_or_404(resource_id)
    return jsonify(serialize_survey_with_responses(survey))

survey_crud.get_detail = get_detail_with_responses

# Register standard CRUD routes
register_crud_routes(bp, survey_crud, 'surveys')