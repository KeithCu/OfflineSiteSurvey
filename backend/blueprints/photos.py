"""Photos blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import json
from ..models import db, Photo
from ...shared.utils import compute_photo_hash


bp = Blueprint('photos', __name__, url_prefix='/api')


@bp.route('/photos/requirement-fulfillment', methods=['POST'])
def mark_requirement_fulfillment():
    """Mark a photo as fulfilling a requirement"""
    data = request.get_json()
    photo_id = data.get('photo_id')
    requirement_id = data.get('requirement_id')
    fulfills = data.get('fulfills', True)

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