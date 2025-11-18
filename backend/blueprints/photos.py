"""Photos blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import json
import secrets
import uuid
from urllib.parse import urlparse
from ..models import db, Photo, Survey, TemplateField
from shared.utils import compute_photo_hash, generate_thumbnail
from ..services.upload_queue import get_upload_queue


def extract_object_name_from_url(url):
    """Extract object name from cloud storage URL."""
    if not url:
        return None
    # Parse URL and extract path, removing leading slash
    parsed = urlparse(url)
    path = parsed.path.lstrip('/')
    return path if path else None


bp = Blueprint('photos', __name__, url_prefix='/api')

@bp.route('/photos', methods=['GET'])
def get_photos():
    """Get all photos."""
    photos = Photo.query.all()
    return jsonify([{
        'id': p.id,
        'survey_id': p.survey_id,
        'site_id': p.site_id,
        'cloud_url': p.cloud_url,
        'thumbnail_url': p.thumbnail_url,
        'upload_status': p.upload_status,
        'latitude': p.latitude,
        'longitude': p.longitude,
        'description': p.description,
        'category': p.category,
        'created_at': p.created_at.isoformat(),
        'hash_value': p.hash_value,
        'size_bytes': p.size_bytes,
        'tags': json.loads(p.tags) if p.tags else []
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

    # For cloud-stored photos, download and verify
    if photo.cloud_url:
        try:
            from ..services.cloud_storage import get_cloud_storage
            cloud_storage = get_cloud_storage()
            object_name = extract_object_name_from_url(photo.cloud_url)
            if not object_name:
                return jsonify({
                    'photo_id': photo_id,
                    'error': 'Invalid cloud URL format'
                }), 500
            image_data = cloud_storage.download_photo(object_name)
            current_hash = compute_photo_hash(image_data, photo.hash_algo)
            actual_size = len(image_data)
        except Exception as e:
            return jsonify({
                'photo_id': photo_id,
                'error': f'Failed to download and verify cloud photo: {str(e)}'
            }), 500
    else:
        # Legacy: check local data (shouldn't happen with new system)
        current_hash = None
        actual_size = 0

    integrity_status = {
        'photo_id': photo_id,
        'stored_hash': photo.hash_value,
        'current_hash': current_hash,
        'hash_matches': photo.hash_value == current_hash if current_hash else False,
        'size_bytes': photo.size_bytes,
        'actual_size': actual_size,
        'size_matches': photo.size_bytes == actual_size if actual_size else False,
        'upload_status': photo.upload_status,
        'cloud_url': photo.cloud_url
    }

    return jsonify(integrity_status)


@bp.route('/surveys/<int:survey_id>/photos', methods=['POST'])
def upload_photo_to_survey(survey_id):
    """Upload a photo to a survey."""
    try:
        # Validate survey exists
        survey = Survey.query.get_or_404(survey_id)

        # Check if image file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400

        # Read image data
        image_data = image_file.read()
        if not image_data:
            return jsonify({'error': 'Empty image file'}), 400

        # Get form data
        question_id_str = request.form.get('question_id')
        question_id = int(question_id_str) if question_id_str else None
        section_name = "general"
        if question_id:
            template_field = TemplateField.query.get(question_id)
            if template_field and template_field.section:
                section_name = template_field.section.lower().replace(" ", "_")

        # Generate unique photo ID
        random_string = secrets.token_hex(4)
        photo_id = f"{survey.site_id}-{section_name}-{random_string}"

        # Compute hash and size
        hash_value = compute_photo_hash(image_data)
        size_bytes = len(image_data)

        # Generate thumbnail
        thumbnail_data = generate_thumbnail(image_data, max_size=200)

        description = request.form.get('description', '')
        category = request.form.get('category', 'general')
        latitude = float(request.form.get('latitude', 0.0))
        longitude = float(request.form.get('longitude', 0.0))
        tags_payload = request.form.get('tags', '')
        tags = []
        if tags_payload:
            try:
                parsed = json.loads(tags_payload)
                if isinstance(parsed, list):
                    tags = parsed
                else:
                    tags = [str(parsed)]
            except json.JSONDecodeError:
                tags = [tag.strip() for tag in tags_payload.split(',') if tag.strip()]

        # Create photo record
        photo = Photo(
            id=photo_id,
            survey_id=survey_id,
            site_id=survey.site_id,  # Get site_id from survey
            cloud_url='',  # Will be set after upload
            thumbnail_url='',  # Will be set after upload
            upload_status='pending',  # Initially pending
            latitude=latitude,
            longitude=longitude,
            description=description,
            category=category,
            hash_value=hash_value,
            size_bytes=size_bytes,
            hash_algo='sha256',
            question_id=question_id,
            tags=json.dumps(tags)
        )

        db.session.add(photo)
        db.session.commit()

        # Queue for cloud upload
        upload_queue = get_upload_queue()
        upload_queue.queue_photo_for_upload(photo_id, image_data, thumbnail_data)

        # Start upload queue if not already running
        upload_queue.start()

        return jsonify({
            'id': photo_id,
            'survey_id': survey_id,
            'upload_status': 'pending',
            'message': 'Photo uploaded and queued for cloud storage'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to upload photo: {str(e)}'}), 500


@bp.route('/photos/<photo_id>', methods=['GET'])
def get_photo(photo_id):
    """Get photo metadata and optionally download image data."""
    photo = Photo.query.get_or_404(photo_id)

    response_data = {
        'id': photo.id,
        'survey_id': photo.survey_id,
        'site_id': photo.site_id,
        'cloud_url': photo.cloud_url,
        'thumbnail_url': photo.thumbnail_url,
        'upload_status': photo.upload_status,
        'latitude': photo.latitude,
        'longitude': photo.longitude,
        'description': photo.description,
        'category': photo.category,
        'created_at': photo.created_at.isoformat(),
        'hash_value': photo.hash_value,
        'size_bytes': photo.size_bytes,
        'tags': json.loads(photo.tags) if photo.tags else []
    }

    # If requesting full image data, download from cloud
    if request.args.get('include_data') == 'true':
        if photo.cloud_url and photo.upload_status == 'completed':
            try:
                from ..services.cloud_storage import get_cloud_storage
                cloud_storage = get_cloud_storage()
                object_name = extract_object_name_from_url(photo.cloud_url)
                if not object_name:
                    response_data['error'] = 'Invalid cloud URL format'
                else:
                    image_data = cloud_storage.download_photo(object_name)
                    response_data['image_data'] = image_data.hex()  # Return as hex string
            except Exception as e:
                response_data['error'] = f'Failed to download image data: {str(e)}'
        else:
            response_data['error'] = 'Image data not available (not uploaded or still pending)'

    return jsonify(response_data)


@bp.route('/photos/<photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """Delete a photo."""
    photo = Photo.query.get_or_404(photo_id)

    try:
        # Delete from cloud storage if uploaded
        if photo.cloud_url and photo.upload_status == 'completed':
            from ..services.cloud_storage import get_cloud_storage
            cloud_storage = get_cloud_storage()
            object_name = extract_object_name_from_url(photo.cloud_url)
            thumbnail_object_name = extract_object_name_from_url(photo.thumbnail_url) if photo.thumbnail_url else None
            if object_name:
                cloud_storage.delete_photo(object_name, thumbnail_object_name)

        # Delete from database
        db.session.delete(photo)
        db.session.commit()

        return jsonify({'message': 'Photo deleted successfully'}), 204

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete photo: {str(e)}'}), 500