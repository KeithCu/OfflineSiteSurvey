"""Authentication blueprint for API key management."""
from flask import Blueprint, request, jsonify
import secrets
from ..models import db, AppConfig


bp = Blueprint('auth', __name__, url_prefix='/api')


@bp.route('/auth/key', methods=['POST'])
def generate_api_key():
    """Generate a new API key for authentication."""
    # Require existing API key to generate new ones (for security)
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if api_key:
        # Validate the existing API key
        config_entry = AppConfig.query.filter_by(value=api_key, category='auth').first()
        if not config_entry:
            return jsonify({'error': 'Invalid existing API key'}), 401
    else:
        # Check if this is initial setup (no API keys exist yet)
        existing_keys = AppConfig.query.filter_by(category='auth').count()
        if existing_keys > 0:
            return jsonify({'error': 'Existing API key required to generate new keys'}), 401

    try:
        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)

        # Store the API key in app config with a descriptive key
        config_key = f'api_key_{secrets.token_hex(8)}'
        config_entry = AppConfig(
            key=config_key,
            value=api_key,
            description='API key for authentication',
            category='auth'
        )

        db.session.add(config_entry)
        db.session.commit()

        return jsonify({
            'api_key': api_key,
            'config_key': config_key,
            'message': 'API key generated successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to generate API key: {str(e)}'}), 500


@bp.route('/auth/validate', methods=['GET'])
def validate_api_key():
    """Validate an API key."""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

    if not api_key:
        return jsonify({'error': 'API key required'}), 401

    # Check if the API key exists in app config
    config_entry = AppConfig.query.filter_by(value=api_key, category='auth').first()

    if config_entry:
        return jsonify({
            'valid': True,
            'config_key': config_entry.key,
            'description': config_entry.description
        })

    return jsonify({'valid': False, 'error': 'Invalid API key'}), 401


def require_api_key(f):
    """Decorator to require API key authentication for a route."""
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        # Check if the API key exists in app config
        config_entry = AppConfig.query.filter_by(value=api_key, category='auth').first()

        if not config_entry:
            return jsonify({'error': 'Invalid API key'}), 401

        # Add the config entry to request for potential use in the route
        request.api_key_config = config_entry

        return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


def init_auth(app):
    """Initialize authentication for the Flask app."""
    @app.before_request
    def check_auth():
        # Skip authentication for auth routes
        if request.path.startswith('/api/auth'):
            return

        # Skip authentication for non-API routes
        if not request.path.startswith('/api'):
            return

        # Check API key
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            from flask import jsonify
            return jsonify({'error': 'API key required'}), 401

        # Check if the API key exists in app config
        config_entry = AppConfig.query.filter_by(value=api_key, category='auth').first()

        if not config_entry:
            from flask import jsonify
            return jsonify({'error': 'Invalid API key'}), 401

        # Add the config entry to request for potential use in the route
        request.api_key_config = config_entry
