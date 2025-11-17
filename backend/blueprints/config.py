"""Config blueprint for Flask API."""
import os
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


@bp.route('/config/cloud-storage', methods=['GET'])
def get_cloud_storage_config():
    """Get cloud storage configuration."""
    config_keys = [
        'CLOUD_STORAGE_PROVIDER',
        'CLOUD_STORAGE_ACCESS_KEY',
        'CLOUD_STORAGE_SECRET_KEY',
        'CLOUD_STORAGE_BUCKET',
        'CLOUD_STORAGE_REGION',
        'CLOUD_STORAGE_LOCAL_PATH'
    ]

    config = {}
    for key in config_keys:
        env_value = os.getenv(key)
        if env_value:
            # Mask sensitive values
            if 'SECRET' in key or 'ACCESS_KEY' in key:
                config[key.lower()] = '*' * len(env_value) if len(env_value) > 4 else env_value
            else:
                config[key.lower()] = env_value

    return jsonify({
        'cloud_storage': config,
        'message': 'Cloud storage configuration retrieved (sensitive values masked)'
    })


@bp.route('/config/cloud-storage/test', methods=['POST'])
def test_cloud_storage_config():
    """Test cloud storage configuration."""
    try:
        from ..services.cloud_storage import get_cloud_storage
        cloud_storage = get_cloud_storage()

        # Try to list containers/buckets to test connection
        containers = cloud_storage.driver.list_containers()
        container_names = [c.name for c in containers]

        return jsonify({
            'status': 'success',
            'message': 'Cloud storage connection successful',
            'containers': container_names,
            'provider': cloud_storage.provider_name
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Cloud storage connection failed: {str(e)}'
        }), 500


@bp.route('/config/cloud-storage/status', methods=['GET'])
def get_cloud_storage_status():
    """Get cloud storage status and queue information."""
    try:
        from ..services.upload_queue import get_upload_queue
        upload_queue = get_upload_queue()

        # Get pending photos count
        from ..models import Photo
        pending_count = Photo.query.filter_by(upload_status='pending').count()
        completed_count = Photo.query.filter_by(upload_status='completed').count()
        failed_count = Photo.query.filter_by(upload_status='failed').count()

        return jsonify({
            'upload_queue_running': upload_queue.running if upload_queue else False,
            'pending_uploads': pending_count,
            'completed_uploads': completed_count,
            'failed_uploads': failed_count,
            'local_storage_path': os.getenv('CLOUD_STORAGE_LOCAL_PATH', './local_photos')
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to get cloud storage status: {str(e)}'
        }), 500