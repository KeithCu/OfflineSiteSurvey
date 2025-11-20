"""Surveys blueprint for Flask API."""
from flask import Blueprint, request, jsonify
from ..models import db, Survey, SurveyResponse
from ..base.crud_base import CRUDBase
from shared.validation import ValidationError
from shared.schemas import SurveyCreate, SurveyUpdate, SurveyResponseSchema
from pydantic import ValidationError as PydanticValidationError
from ..utils import validate_foreign_key
bp = Blueprint('surveys', __name__, url_prefix='/api')


class SurveyCRUD(CRUDBase):
    """CRUD operations for Survey model."""
    
    def __init__(self):
        super().__init__(Survey, logger_name='surveys')
    
    def serialize(self, survey, include_responses=False):
        """Serialize survey to dictionary using Pydantic.
        
        Args:
            survey: Survey model instance
            include_responses: Whether to include responses in serialization
        """
        result = SurveyResponseSchema.model_validate(survey).model_dump(mode='json')
        
        if include_responses:
            result['responses'] = self._serialize_responses(survey.responses)
        
        return result
    
    def _serialize_responses(self, responses):
        """Serialize survey responses to list of dictionaries."""
        return [{
            'id': r.id,
            'question': r.question,
            'answer': r.answer,
            'response_type': r.response_type,
            'latitude': r.latitude,
            'longitude': r.longitude,
            'created_at': r.created_at.isoformat()
        } for r in responses]
    
    def validate_create_data(self, data):
        """Validate and prepare data for survey creation using Pydantic."""
        try:
            survey = SurveyCreate(**data)
            validated_data = survey.model_dump(exclude_none=True)
            
            # Validate that site_id exists
            site_id = validated_data['site_id']
            if not validate_foreign_key('sites', 'id', site_id):
                raise ValidationError(f'site_id {site_id} does not exist')
            
            # Validate template_id exists if provided
            template_id = validated_data.get('template_id')
            if template_id is not None:
                if not validate_foreign_key('survey_template', 'id', template_id):
                    raise ValidationError(f'template_id {template_id} does not exist')
            
            return validated_data
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))
    
    def get_detail(self, resource_id):
        """Get single survey by ID with responses included."""
        survey = self.model.query.get_or_404(resource_id)
        return jsonify(self.serialize(survey, include_responses=True))
    
    def create(self, validate_func=None):
        """Create a new survey with custom response format including template_id."""
        try:
            data = self.get_json_data()
            
            if validate_func:
                validated_data = validate_func(data)
            else:
                validated_data = self.validate_create_data(data)
            
            survey = self.model(**validated_data)
            db.session.add(survey)
            db.session.commit()
            
            self.logger.info(f"Created {self.get_singular_name()}: {survey.id} - {survey.title}")
            
            return jsonify({
                'id': survey.id,
                'template_id': survey.template_id,
                'message': f'{self.get_singular_name().title()} created successfully'
            }), 201
            
        except ValidationError as e:
            self.logger.warning(f"Validation error in {self.get_singular_name()} creation: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            self.logger.error(f"Failed to create {self.get_singular_name()}: {e}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': f'Failed to create {self.get_singular_name()}'}), 500


# Create CRUD instance
survey_crud = SurveyCRUD()


@bp.route('/surveys', methods=['GET'])
def get_surveys():
    """Get paginated list of surveys."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    return survey_crud.get_list(page=page, per_page=per_page)


@bp.route('/surveys/<int:survey_id>', methods=['GET'])
def get_survey(survey_id):
    """Get single survey by ID with responses."""
    return survey_crud.get_detail(survey_id)


@bp.route('/surveys', methods=['POST'])
def create_survey():
    """Create a new survey."""
    return survey_crud.create()


@bp.route('/surveys/<int:survey_id>', methods=['DELETE'])
def delete_survey(survey_id):
    """Delete a survey."""
    return survey_crud.delete(survey_id)