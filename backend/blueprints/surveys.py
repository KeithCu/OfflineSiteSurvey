"""Surveys blueprint for Flask API."""
from flask import Blueprint, request, jsonify
from ..models import db, Survey, SurveyResponse, SurveyStatus
from ..base.crud_base import CRUDBase
from shared.validation import Validator, ValidationError
from ..utils import validate_foreign_key
from typing import Dict, Any, List


bp = Blueprint('surveys', __name__, url_prefix='/api')


class SurveyCRUD(CRUDBase):
    """CRUD operations for Survey model."""
    
    def __init__(self):
        super().__init__(Survey, logger_name='surveys')
    
    def serialize(self, survey: Survey, include_responses: bool = False) -> Dict[str, Any]:
        """Serialize survey to dictionary.
        
        Args:
            survey: Survey model instance
            include_responses: Whether to include responses in serialization
        """
        result = {
            'id': survey.id,
            'title': survey.title,
            'description': survey.description,
            'template_id': survey.template_id,
            'status': survey.status.value if hasattr(survey.status, 'value') else str(survey.status),
            'created_at': survey.created_at.isoformat(),
            'updated_at': survey.updated_at.isoformat()
        }
        
        if include_responses:
            result['responses'] = self._serialize_responses(survey.responses)
        
        return result
    
    def _serialize_responses(self, responses: List[SurveyResponse]) -> List[Dict[str, Any]]:
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
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and prepare data for survey creation."""
        # Validate input data using shared validator
        validated_data = Validator.validate_survey_data(data)
        
        # Validate that site_id exists
        site_id = validated_data['site_id']
        if not validate_foreign_key('sites', 'id', site_id):
            raise ValidationError(f'site_id {site_id} does not exist')
        
        # Validate template_id exists if provided
        template_id = data.get('template_id')
        if template_id is not None:
            try:
                template_id = int(template_id)
            except (ValueError, TypeError):
                raise ValidationError('template_id must be an integer')
            
            if not validate_foreign_key('survey_template', 'id', template_id):
                raise ValidationError(f'template_id {template_id} does not exist')
            validated_data['template_id'] = template_id
        
        # Handle status enum
        status_str = data.get('status', 'draft')
        if not isinstance(status_str, str):
            raise ValidationError('status must be a string')
        
        try:
            validated_data['status'] = SurveyStatus(status_str)
        except ValueError:
            raise ValidationError(f'status must be one of: {[s.value for s in SurveyStatus]}')
        
        # Clean up string fields
        if 'title' in validated_data:
            validated_data['title'] = validated_data['title'].strip()
        
        if 'description' in validated_data:
            description = validated_data['description']
            validated_data['description'] = description.strip() if description else None
        
        return validated_data
    
    def get_detail(self, resource_id: int) -> tuple:
        """Get single survey by ID with responses included."""
        survey = self.model.query.get_or_404(resource_id)
        return jsonify(self.serialize(survey, include_responses=True))
    
    def create(self, validate_func=None) -> tuple:
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
    from ..utils import cascade_delete_survey
    return survey_crud.delete(survey_id, cascade_func=cascade_delete_survey)