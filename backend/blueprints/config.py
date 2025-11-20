"""Config blueprint for Flask API."""
import os
import re
import logging
from flask import Blueprint, jsonify, request
from ..models import db, AppConfig
from shared.validation import Validator, ValidationError

logger = logging.getLogger(__name__)


bp = Blueprint('config', __name__, url_prefix='/api')

# Valid config key pattern (alphanumeric and underscore only)
CONFIG_KEY_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Known config keys with validation rules
CONFIG_VALIDATION_RULES = {
    'image_compression_quality': {
        'type': int,
        'min': 1,
        'max': 100,
        'description': 'JPEG compression quality (1-100)'
    },
    'auto_sync_interval': {
        'type': int,
        'min': 0,
        'max': 86400,  # Max 24 hours
        'description': 'Auto-sync frequency in seconds (0-86400)'
    },
    'max_offline_days': {
        'type': int,
        'min': 0,
        'max': 365,  # Max 1 year
        'description': 'Maximum offline data retention in days (0-365)'
    }
}


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

    # Validate config key format
    if not CONFIG_KEY_PATTERN.match(key):
        return jsonify({'error': f'Invalid config key format: {key}. Must be alphanumeric with underscores only'}), 400

    # Validate key length
    if len(key) > 100:
        return jsonify({'error': 'Config key must be 100 characters or less'}), 400

    config = AppConfig.query.filter_by(key=key).first()
    old_value = None
    if not config:
        # Create new config if it doesn't exist
        config = AppConfig(key=key)
        logger.info(f"Creating new configuration: key={key}")
    else:
        old_value = config.value
        logger.info(f"Updating configuration: key={key}, old_value={old_value}")

    # Validate and set value
    if 'value' in data:
        value = data['value']
        
        # Apply known validation rules if key is recognized
        if key in CONFIG_VALIDATION_RULES:
            rule = CONFIG_VALIDATION_RULES[key]
            try:
                # Convert to appropriate type
                if rule['type'] == int:
                    value_int = int(value)
                    # Validate range
                    if 'min' in rule and value_int < rule['min']:
                        return jsonify({'error': f'{key} must be at least {rule["min"]}'}), 400
                    if 'max' in rule and value_int > rule['max']:
                        return jsonify({'error': f'{key} must be at most {rule["max"]}'}), 400
                    config.value = str(value_int)
                else:
                    config.value = str(value)
            except (ValueError, TypeError):
                return jsonify({'error': f'{key} must be a valid {rule["type"].__name__}'}), 400
        else:
            # For unknown keys, just validate it's a reasonable string
            value_str = str(value)
            if len(value_str) > 10000:  # Reasonable limit for config values
                return jsonify({'error': 'Config value too long (max 10000 characters)'}), 400
            config.value = value_str

    # Validate and set description
    if 'description' in data:
        description = data['description']
        if description is not None:
            if not isinstance(description, str):
                return jsonify({'error': 'description must be a string'}), 400
            try:
                description = Validator.validate_string_length(description, 'description', 0, 300)
                config.description = description
            except ValidationError as e:
                return jsonify({'error': str(e)}), 400

    # Validate and set category
    if 'category' in data:
        category = data['category']
        if category is not None:
            if not isinstance(category, str):
                return jsonify({'error': 'category must be a string'}), 400
            try:
                category = Validator.validate_string_length(category, 'category', 0, 50)
                config.category = category
            except ValidationError as e:
                return jsonify({'error': str(e)}), 400

    try:
        db.session.add(config)
        db.session.commit()
        logger.info(f"Configuration updated: key={key}, new_value={config.value}, old_value={old_value}")
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