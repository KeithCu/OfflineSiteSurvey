"""Projects blueprint for Flask API."""
from flask import Blueprint, request
from ..models import Project
from ..base.crud_base import CRUDBase
from shared.validation import ValidationError
from shared.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from pydantic import ValidationError as PydanticValidationError
bp = Blueprint('projects', __name__, url_prefix='/api')


class ProjectCRUD(CRUDBase):
    """CRUD operations for Project model."""
    
    def __init__(self):
        super().__init__(Project, logger_name='projects')
    
    def serialize(self, project):
        """Serialize project to dictionary using Pydantic."""
        return ProjectResponse.model_validate(project).model_dump(mode='json')
    
    def validate_create_data(self, data):
        """Validate and prepare data for project creation using Pydantic."""
        try:
            project = ProjectCreate(**data)
            return project.model_dump(exclude_none=True)
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))
    
    def validate_update_data(self, data):
        """Validate and prepare data for project update using Pydantic."""
        try:
            project = ProjectUpdate(**data)
            return project.model_dump(exclude_none=True)
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))


# Create CRUD instance
project_crud = ProjectCRUD()


@bp.route('/projects', methods=['GET'])
def get_projects():
    """Get paginated list of projects."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    return project_crud.get_list(page=page, per_page=per_page)


@bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get single project by ID."""
    return project_crud.get_detail(project_id)


@bp.route('/projects', methods=['POST'])
def create_project():
    """Create a new project."""
    return project_crud.create()


@bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update an existing project."""
    return project_crud.update(project_id)


@bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project."""
    from ..utils import cascade_delete_project
    return project_crud.delete(project_id, cascade_func=cascade_delete_project)