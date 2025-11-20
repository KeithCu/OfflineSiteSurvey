from flask import Blueprint, request, jsonify, g
from ..models import db
from shared.models import Team, User
from shared.enums import UserRole

bp = Blueprint('teams', __name__, url_prefix='/api')

@bp.route('/teams', methods=['GET'])
def list_teams():
    """List all teams."""
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Authentication required'}), 401

    teams = Team.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'member_count': len(t.members)
    } for t in teams])

@bp.route('/teams', methods=['POST'])
def create_team():
    """Create a new team."""
    if not hasattr(g, 'user') or g.user.role != UserRole.ADMIN:
        return jsonify({'error': 'Admin privileges required'}), 403

    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Team name is required'}), 400

    try:
        team = Team(name=name, description=data.get('description', ''))
        db.session.add(team)
        db.session.commit()
        return jsonify({'id': team.id, 'name': team.name}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/teams/<int:team_id>/members', methods=['POST'])
def add_member(team_id):
    """Add a user to a team."""
    if not hasattr(g, 'user') or g.user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        return jsonify({'error': 'Admin or Manager privileges required'}), 403

    data = request.get_json()
    username = data.get('username')

    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        user.team_id = team.id
        db.session.commit()
        return jsonify({'message': f'User {username} added to team {team.name}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/teams/<int:team_id>/members', methods=['GET'])
def list_members(team_id):
    """List members of a team."""
    if not hasattr(g, 'user'):
        return jsonify({'error': 'Authentication required'}), 401

    team = Team.query.get(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'role': u.role
    } for u in team.members])
