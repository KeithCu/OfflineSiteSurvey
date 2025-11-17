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
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    # Validate required fields
    if 'name' not in data:
        return jsonify({'error': 'name field is required'}), 400

    name = data['name']
    if not isinstance(name, str) or not name.strip():
        return jsonify({'error': 'name must be a non-empty string'}), 400

    # Validate optional fields
    description = data.get('description')
    if description is not None and not isinstance(description, str):
        return jsonify({'error': 'description must be a string'}), 400

    status_str = data.get('status', 'draft')
    if not isinstance(status_str, str):
        return jsonify({'error': 'status must be a string'}), 400

    try:
        status = ProjectStatus(status_str)
    except ValueError:
        return jsonify({'error': f'status must be one of: {[s.value for s in ProjectStatus]}'}), 400

    client_info = data.get('client_info')
    if client_info is not None and not isinstance(client_info, str):
        return jsonify({'error': 'client_info must be a string'}), 400

    due_date = None
    due_date_str = data.get('due_date')
    if due_date_str:
        if not isinstance(due_date_str, str):
            return jsonify({'error': 'due_date must be a string in ISO format'}), 400
        try:
            due_date = datetime.datetime.fromisoformat(due_date_str)
        except ValueError:
            return jsonify({'error': 'due_date must be a valid ISO date string'}), 400

    priority_str = data.get('priority', 'medium')
    from ..models import PriorityLevel
    if not isinstance(priority_str, str):
        return jsonify({'error': 'priority must be a string'}), 400

    try:
        priority = PriorityLevel(priority_str)
    except ValueError:
        return jsonify({'error': f'priority must be one of: {[p.value for p in PriorityLevel]}'}), 400

    try:
        project = Project(
            name=name.strip(),
            description=description.strip() if description else None,
            status=status,
            client_info=client_info.strip() if client_info else None,
            due_date=due_date,
            priority=priority
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({
            'id': project.id,
            'message': 'Project created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create project: {str(e)}'}), 500


@bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    project = Project.query.get_or_404(project_id)

    # Validate and update name
    if 'name' in data:
        name = data['name']
        if not isinstance(name, str) or not name.strip():
            return jsonify({'error': 'name must be a non-empty string'}), 400
        project.name = name.strip()

    # Validate and update description
    if 'description' in data:
        description = data['description']
        if description is not None and not isinstance(description, str):
            return jsonify({'error': 'description must be a string'}), 400
        project.description = description.strip() if description else None

    # Validate and update status
    if 'status' in data:
        status_str = data['status']
        if not isinstance(status_str, str):
            return jsonify({'error': 'status must be a string'}), 400
        try:
            project.status = ProjectStatus(status_str)
        except ValueError:
            return jsonify({'error': f'status must be one of: {[s.value for s in ProjectStatus]}'}), 400

    # Validate and update client_info
    if 'client_info' in data:
        client_info = data['client_info']
        if client_info is not None and not isinstance(client_info, str):
            return jsonify({'error': 'client_info must be a string'}), 400
        project.client_info = client_info.strip() if client_info else None

    # Validate and update due_date
    if 'due_date' in data:
        due_date_str = data['due_date']
        if due_date_str is not None:
            if not isinstance(due_date_str, str):
                return jsonify({'error': 'due_date must be a string in ISO format'}), 400
            try:
                project.due_date = datetime.datetime.fromisoformat(due_date_str)
            except ValueError:
                return jsonify({'error': 'due_date must be a valid ISO date string'}), 400
        else:
            project.due_date = None

    # Validate and update priority
    if 'priority' in data:
        priority_str = data['priority']
        if not isinstance(priority_str, str):
            return jsonify({'error': 'priority must be a string'}), 400
        from ..models import PriorityLevel
        try:
            project.priority = PriorityLevel(priority_str)
        except ValueError:
            return jsonify({'error': f'priority must be one of: {[p.value for p in PriorityLevel]}'}), 400

    try:
        db.session.commit()
        return jsonify({'message': 'Project updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update project: {str(e)}'}), 500


@bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'})