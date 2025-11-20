"""Projects blueprint for Flask API."""
from flask import Blueprint, request
from ..models import Project, ProjectStatus
from ..base.crud_base import CRUDBase
from shared.validation import Validator, ValidationError
from shared.enums import PriorityLevel
import datetime
bp = Blueprint('projects', __name__, url_prefix='/api')


class ProjectCRUD(CRUDBase):
    """CRUD operations for Project model."""
    
    def __init__(self):
        super().__init__(Project, logger_name='projects')
    
    def serialize(self, project):
        """Serialize project to dictionary."""
        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status.value,
            'client_info': project.client_info,
            'due_date': project.due_date.isoformat() if project.due_date else None,
            'priority': project.priority.value,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        }
    
    def validate_create_data(self, data):
        """Validate and prepare data for project creation."""
        # Validate input data using shared validator
        validated_data = Validator.validate_project_data(data)
        
        # Handle status enum
        status_str = data.get('status', 'draft')
        if not isinstance(status_str, str):
            raise ValidationError('status must be a string')
        
        try:
            status = ProjectStatus(status_str)
        except ValueError:
            raise ValidationError(f'Invalid status: {status_str}')
        
        validated_data['status'] = status
        
        # Handle priority enum
        priority_str = data.get('priority', 'medium')
        if not isinstance(priority_str, str):
            raise ValidationError('priority must be a string')
        
        try:
            priority = PriorityLevel(priority_str)
        except ValueError:
            raise ValidationError(f'Invalid priority: {priority_str}')
        
        validated_data['priority'] = priority
        
        # Handle due date
        due_date = None
        due_date_str = data.get('due_date')
        if due_date_str:
            if not isinstance(due_date_str, str):
                raise ValidationError('due_date must be a string in ISO format')
            try:
                due_date = datetime.datetime.fromisoformat(due_date_str)
            except ValueError:
                raise ValidationError('due_date must be a valid ISO date string')
        
        validated_data['due_date'] = due_date
        
        return validated_data
    
    def validate_update_data(self, data):
        """Validate and prepare data for project update."""
        validated_data = {}
        
        # Validate and prepare name
        if 'name' in data:
            name = data['name']
            if not isinstance(name, str) or not name.strip():
                raise ValidationError('name must be a non-empty string')
            validated_data['name'] = name.strip()
        
        # Validate and prepare description
        if 'description' in data:
            description = data['description']
            if description is not None and not isinstance(description, str):
                raise ValidationError('description must be a string')
            validated_data['description'] = description.strip() if description else None
        
        # Validate and prepare status
        if 'status' in data:
            status_str = data['status']
            if not isinstance(status_str, str):
                raise ValidationError('status must be a string')
            try:
                validated_data['status'] = ProjectStatus(status_str)
            except ValueError:
                raise ValidationError(f'status must be one of: {[s.value for s in ProjectStatus]}')
        
        # Validate and prepare client_info
        if 'client_info' in data:
            client_info = data['client_info']
            if client_info is not None and not isinstance(client_info, str):
                raise ValidationError('client_info must be a string')
            validated_data['client_info'] = client_info.strip() if client_info else None
        
        # Validate and prepare due_date
        if 'due_date' in data:
            due_date_str = data['due_date']
            if due_date_str is not None:
                if not isinstance(due_date_str, str):
                    raise ValidationError('due_date must be a string in ISO format')
                try:
                    validated_data['due_date'] = datetime.datetime.fromisoformat(due_date_str)
                except ValueError:
                    raise ValidationError('due_date must be a valid ISO date string')
            else:
                validated_data['due_date'] = None
        
        # Validate and prepare priority
        if 'priority' in data:
            priority_str = data['priority']
            if not isinstance(priority_str, str):
                raise ValidationError('priority must be a string')
            try:
                validated_data['priority'] = PriorityLevel(priority_str)
            except ValueError:
                raise ValidationError(f'priority must be one of: {[p.value for p in PriorityLevel]}')
        
        return validated_data


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