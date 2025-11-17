"""Config blueprint for Flask API."""
from flask import Blueprint, jsonify, request
from ..models import db, AppConfig


bp = Blueprint('config', __name__, url_prefix='/api')


@bp.route('/config', methods=['GET'])
def get_all_config():
    """Get all configuration values."""
    configs = AppConfig.query.all()
    return jsonify({
        config.key: {
            'value': config.value,
            'description': config.description,
            'category': config.category
        } for config in configs
    })


@bp.route('/config/<key>', methods=['GET'])
def get_config(key):
    """Get a specific configuration value."""
    config = AppConfig.query.filter_by(key=key).first_or_404()
    return jsonify({
        'key': config.key,
        'value': config.value,
        'description': config.description,
        'category': config.category
    })


@bp.route('/config/<key>', methods=['PUT'])
def update_config(key):
    """Update a configuration value."""
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    config = AppConfig.query.filter_by(key=key).first()
    if not config:
        # Create new config if it doesn't exist
        config = AppConfig(key=key)

    if 'value' in data:
        config.value = str(data['value'])
    if 'description' in data:
        config.description = data['description']
    if 'category' in data:
        config.category = data['category']

    try:
        db.session.add(config)
        db.session.commit()
        return jsonify({
            'key': config.key,
            'value': config.value,
            'description': config.description,
            'category': config.category
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update config: {str(e)}'}), 500