"""Sites blueprint for Flask API."""
from flask import Blueprint, jsonify
from ..models import Site
from ..base.generic_crud import GenericCRUD, register_crud_routes
from shared.validation import ValidationError
from shared.schemas import SiteCreate, SiteUpdate, SiteResponse
from ..utils import validate_foreign_key, cascade_delete_site

bp = Blueprint('sites', __name__, url_prefix='/api')


def validate_project_id(data):
    """Pre-create hook to validate project_id exists."""
    project_id = data.get('project_id')
    if project_id and not validate_foreign_key('projects', 'id', project_id):
        raise ValidationError(f'Project with ID {project_id} does not exist')
    return data


def validate_project_id_update(data, resource):
    """Pre-update hook to validate project_id exists if provided."""
    if 'project_id' in data:
        project_id = data['project_id']
        if project_id is not None and not validate_foreign_key('projects', 'id', project_id):
            raise ValidationError(f'project_id {project_id} does not exist')
    return data


def serialize_site_list(site):
    """Serialize site for list view (include project_id)."""
    return SiteResponse.model_validate(site).model_dump(mode='json')


def serialize_site_detail(site):
    """Serialize site for detail view (exclude project_id)."""
    result = SiteResponse.model_validate(site).model_dump(mode='json')
    result.pop('project_id', None)
    return result


# Create generic CRUD instance
site_crud = GenericCRUD(
    model=Site,
    create_schema=SiteCreate,
    update_schema=SiteUpdate,
    response_schema=SiteResponse,
    logger_name='sites',
    pre_create_hook=validate_project_id,
    pre_update_hook=validate_project_id_update,
    cascade_delete_func=cascade_delete_site
)


# Override get_list to include project_id
def get_list_with_project_id(page=1, per_page=50, max_per_page=100):
    """Get paginated list of sites (with project_id included)."""
    per_page = min(per_page, max_per_page)
    
    pagination = Site.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    items = [serialize_site_list(item) for item in pagination.items]
    
    return jsonify({
        'sites': items,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

site_crud.get_list = get_list_with_project_id


# Override get_detail to exclude project_id
def get_detail_without_project_id(resource_id):
    """Get single site by ID (without project_id in response)."""
    site = Site.query.get_or_404(resource_id)
    return jsonify(serialize_site_detail(site))

site_crud.get_detail = get_detail_without_project_id

# Register standard CRUD routes
register_crud_routes(bp, site_crud, 'sites')