"""Photos blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import json
from ..models import db, Photo
from shared.utils import compute_photo_hash


bp = Blueprint('photos', __name__, url_prefix='/api')

@bp.route('/photos', methods=['GET'])
def get_photos():
    """Get all photos."""
    photos = Photo.query.all()
    return jsonify([{
        'id': p.id,
        'survey_id': p.survey_id,
        'site_id': p.site_id,
        'latitude': p.latitude,
        'longitude': p.longitude,
        'description': p.description,
        'category': p.category,
        'created_at': p.created_at.isoformat(),
        'hash_value': p.hash_value,
        'size_bytes': p.size_bytes
    } for p in photos])



@bp.route('/photos/requirement-fulfillment', methods=['POST'])
def mark_requirement_fulfillment():
    """Mark a photo as fulfilling a requirement"""
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    # Validate photo_id
    photo_id = data.get('photo_id')
    if photo_id is None:
        return jsonify({'error': 'photo_id field is required'}), 400
    if not isinstance(photo_id, str) or not photo_id.strip():
        return jsonify({'error': 'photo_id must be a non-empty string'}), 400

    # Validate requirement_id (can be None to clear)
    requirement_id = data.get('requirement_id')
    if requirement_id is not None and not isinstance(requirement_id, str):
        return jsonify({'error': 'requirement_id must be a string or null'}), 400

    # Validate fulfills
    fulfills = data.get('fulfills', True)
    if not isinstance(fulfills, bool):
        return jsonify({'error': 'fulfills must be a boolean'}), 400

    try:
        photo = Photo.query.get_or_404(photo_id)
        photo.requirement_id = requirement_id
        photo.fulfills_requirement = fulfills
        db.session.commit()

        return jsonify({
            'photo_id': photo_id,
            'requirement_id': requirement_id,
            'fulfills': fulfills,
            'message': 'Photo requirement fulfillment updated'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update photo requirement: {str(e)}'}), 500


@bp.route('/photos/<photo_id>/integrity', methods=['GET'])
def get_photo_integrity(photo_id):
    """Get integrity information for a photo"""
    photo = Photo.query.get_or_404(photo_id)

    # Compute current hash of stored image data
    current_hash = compute_photo_hash(photo.image_data, photo.hash_algo)

    integrity_status = {
        'photo_id': photo_id,
        'stored_hash': photo.hash_value,
        'current_hash': current_hash,
        'hash_matches': photo.hash_value == current_hash,
        'size_bytes': photo.size_bytes,
        'actual_size': len(photo.image_data) if photo.image_data else 0,
        'size_matches': photo.size_bytes == len(photo.image_data) if photo.image_data else False
    }

    return jsonify(integrity_status)