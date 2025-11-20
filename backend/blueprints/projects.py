"""Projects blueprint for Flask API."""
from flask import Blueprint
from ..models import Project
from ..base.generic_crud import GenericCRUD, register_crud_routes
from shared.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from ..utils import cascade_delete_project

bp = Blueprint('projects', __name__, url_prefix='/api')

# Create generic CRUD instance
project_crud = GenericCRUD(
    model=Project,
    create_schema=ProjectCreate,
    update_schema=ProjectUpdate,
    response_schema=ProjectResponse,
    logger_name='projects',
    cascade_delete_func=cascade_delete_project
)

# Register standard CRUD routes
register_crud_routes(bp, project_crud, 'projects')