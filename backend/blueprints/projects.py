"""Projects blueprint for Flask API."""
from flask import Blueprint, jsonify, request
from ..models import db, Project, ProjectStatus
import datetime


bp = Blueprint('projects', __name__, url_prefix='/api')


@bp.route('/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'status': p.status.value if p.status else None,
        'client_info': p.client_info,
        'due_date': p.due_date.isoformat() if p.due_date else None,
        'priority': p.priority,
        'created_at': p.created_at.isoformat(),
        'updated_at': p.updated_at.isoformat()
    } for p in projects])


@bp.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    project = Project(
        name=data['name'],
        description=data.get('description'),
        status=data.get('status', 'draft'),
        client_info=data.get('client_info'),
        due_date=datetime.datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        priority=data.get('priority', 'medium')
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({
        'id': project.id,
        'message': 'Project created successfully'
    }), 201


@bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    project.client_info = data.get('client_info', project.client_info)
    project.due_date = datetime.datetime.fromisoformat(data['due_date']) if data.get('due_date') else project.due_date
    project.priority = data.get('priority', project.priority)
    db.session.commit()
    return jsonify({'message': 'Project updated successfully'})


@bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'})