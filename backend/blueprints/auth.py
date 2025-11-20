"""Authentication blueprint for API key and User management."""
from flask import Blueprint, request, jsonify, g
import secrets
import re
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import db, AppConfig
from shared.models import User
from shared.enums import UserRole
from shared.validation import ValidationError

bp = Blueprint('auth', __name__, url_prefix='/api')

# API key validation constants
API_KEY_MIN_LENGTH = 20
API_KEY_MAX_LENGTH = 200
API_KEY_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')


def validate_api_key_format(api_key):
    """Validate API key format and length."""
    if not api_key:
        raise ValidationError('API key is required')
    if not isinstance(api_key, str):
        raise ValidationError('API key must be a string')
    api_key = api_key.strip()
    if len(api_key) < API_KEY_MIN_LENGTH:
        raise ValidationError(f'API key must be at least {API_KEY_MIN_LENGTH} characters')
    if len(api_key) > API_KEY_MAX_LENGTH:
        raise ValidationError(f'API key must be no more than {API_KEY_MAX_LENGTH} characters')
    if not API_KEY_PATTERN.match(api_key):
        raise ValidationError('API key contains invalid characters')
    return api_key


@bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'User already exists'}), 400

    # Default first user to ADMIN, others to SURVEYOR
    role = UserRole.SURVEYOR
    if User.query.count() == 0:
        role = UserRole.ADMIN

    try:
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()

        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/auth/login', methods=['POST'])
def login():
    """Login user and return token."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid username or password'}), 401

    # Generate token
    token = secrets.token_urlsafe(32)

    # Store token in AppConfig (category='user_token')
    # key: 'token_<token>', value: user_id
    try:
        # Remove old tokens for this user? Maybe later.

        config_entry = AppConfig(
            key=f'token_{token}',
            value=str(user.id),
            description=f'Token for user {user.username}',
            category='user_token'
        )
        db.session.add(config_entry)
        db.session.commit()

        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'team_id': user.team_id
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/auth/logout', methods=['POST'])
def logout():
    """Logout user by invalidating token."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Token required'}), 400

    try:
        config_entry = AppConfig.query.filter_by(key=f'token_{token}', category='user_token').first()
        if config_entry:
            db.session.delete(config_entry)
            db.session.commit()
            return jsonify({'message': 'Logged out successfully'})
        return jsonify({'error': 'Invalid token'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/auth/me', methods=['GET'])
def me():
    """Get current user info."""
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401

    return jsonify({
        'id': g.user.id,
        'username': g.user.username,
        'email': g.user.email,
        'role': g.user.role,
        'team_id': g.user.team_id
    })


@bp.route('/auth/key', methods=['POST'])
def generate_api_key():
    """Generate a new API key for machine authentication."""
    # ... (Existing implementation logic)
    # Require ADMIN user or existing API key
    auth_passed = False

    # Check API key
    api_key = request.headers.get('X-API-Key')
    if api_key:
        if AppConfig.query.filter_by(value=api_key, category='auth').first():
            auth_passed = True

    # Check User Token (Admin only)
    if not auth_passed and hasattr(g, 'user') and g.user and g.user.role == UserRole.ADMIN:
        auth_passed = True

    # Allow initial setup
    if not auth_passed:
        has_keys = AppConfig.query.filter_by(category='auth').count() > 0
        has_users = User.query.count() > 0
        if not has_keys and not has_users:
            auth_passed = True

    if not auth_passed:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        api_key = secrets.token_urlsafe(32)
        config_key = f'api_key_{secrets.token_hex(8)}'
        config_entry = AppConfig(
            key=config_key,
            value=api_key,
            description='API key for authentication',
            category='auth'
        )
        db.session.add(config_entry)
        db.session.commit()
        return jsonify({'api_key': api_key})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def init_auth(app):
    """Initialize authentication for the Flask app."""
    @app.before_request
    def check_auth():
        if request.path.startswith('/api/auth/login') or \
           request.path.startswith('/api/auth/register'):
            return

        if not request.path.startswith('/api'):
            return

        # Check Bearer Token (User Auth)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            config_entry = AppConfig.query.filter_by(key=f'token_{token}', category='user_token').first()
            if config_entry:
                user_id = int(config_entry.value)
                g.user = User.query.get(user_id)
                return # Authenticated as User

        # Check API Key (Machine Auth)
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if api_key:
            config_entry = AppConfig.query.filter_by(value=api_key, category='auth').first()
            if config_entry:
                g.api_key = config_entry
                return # Authenticated as Machine

        # If we are here, no valid auth found.
        # Only enforce auth on specific routes? Or all API routes?
        # Existing code enforced it globally for /api.
        # But /api/auth/key needs to be accessible if no keys exist?
        # Logic in generate_api_key handles the "no keys exist" case.

        # We should return 401 if no auth provided
        # BUT, let the individual routes handle 401 if they need user info?
        # Or enforce globally?
        # Existing code returned 401.

        # Exception: /api/config might be public? No.

        from flask import jsonify
        return jsonify({'error': 'Authentication required'}), 401
