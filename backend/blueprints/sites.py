"""Sites blueprint for Flask API."""
from flask import Blueprint, request, jsonify
from ..models import Site
from ..base.crud_base import CRUDBase
from shared.validation import ValidationError
from shared.schemas import SiteCreate, SiteUpdate, SiteResponse
from pydantic import ValidationError as PydanticValidationError
from ..utils import validate_foreign_key
bp = Blueprint('sites', __name__, url_prefix='/api')


class SiteCRUD(CRUDBase):
    """CRUD operations for Site model."""
    
    def __init__(self):
        super().__init__(Site, logger_name='sites')
    
    def serialize(self, site, include_project_id=True):
        """Serialize site to dictionary using Pydantic.
        
        Args:
            site: Site model instance
            include_project_id: Whether to include project_id in response
        """
        result = SiteResponse.model_validate(site).model_dump(mode='json')
        if not include_project_id:
            result.pop('project_id', None)
        return result
    
    def validate_create_data(self, data):
        """Validate and prepare data for site creation using Pydantic."""
        try:
            site = SiteCreate(**data)
            validated_data = site.model_dump(exclude_none=True)
            
            # Validate that project_id exists
            project_id = validated_data['project_id']
            if not validate_foreign_key('projects', 'id', project_id):
                raise ValidationError(f'Project with ID {project_id} does not exist')
            
            return validated_data
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))
    
    def validate_update_data(self, data):
        """Validate and prepare data for site update using Pydantic."""
        try:
            site = SiteUpdate(**data)
            validated_data = site.model_dump(exclude_none=True)
            
            # Validate that project_id exists if provided
            if 'project_id' in validated_data:
                project_id = validated_data['project_id']
                if project_id is not None and not validate_foreign_key('projects', 'id', project_id):
                    raise ValidationError(f'project_id {project_id} does not exist')
            
            return validated_data
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))
    
    def get_list(self, page=1, per_page=50, max_per_page=100):
        """Get paginated list of sites (with project_id included)."""
        per_page = min(per_page, max_per_page)
        
        pagination = self.model.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Include project_id in list view
        items = [self.serialize(item, include_project_id=True) for item in pagination.items]
        
        return jsonify({
            self.get_plural_name(): items,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    
    def get_detail(self, resource_id):
        """Get single site by ID (without project_id in response)."""
        site = self.model.query.get_or_404(resource_id)
        return jsonify(self.serialize(site, include_project_id=False))


# Create CRUD instance
site_crud = SiteCRUD()


@bp.route('/sites', methods=['GET'])
def get_sites():
    """Get paginated list of sites."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    return site_crud.get_list(page=page, per_page=per_page)


@bp.route('/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    """Get single site by ID."""
    return site_crud.get_detail(site_id)


@bp.route('/sites', methods=['POST'])
def create_site():
    """Create a new site."""
    return site_crud.create()


@bp.route('/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    """Update an existing site."""
    return site_crud.update(site_id)


@bp.route('/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    """Delete a site."""
    return site_crud.delete(site_id)