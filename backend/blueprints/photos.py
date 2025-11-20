"""Photos blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import json
import secrets
import uuid
import hashlib
from urllib.parse import urlparse
from ..models import db, Photo, Survey, TemplateField
from shared.utils import compute_photo_hash, generate_thumbnail
from shared.validation import Validator, ValidationError
from shared.enums import PhotoCategory
from ..services.upload_queue import get_upload_queue
from ..utils import api_error, handle_api_exception


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
    try:
        photo_id = Validator.validate_string_length(str(photo_id).strip(), 'photo_id', 1, 200)
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400

    # Validate requirement_id (can be None to clear)
    requirement_id = data.get('requirement_id')
    if requirement_id is not None:
        if not isinstance(requirement_id, str):
            return jsonify({'error': 'requirement_id must be a string or null'}), 400
        try:
            requirement_id = Validator.validate_string_length(requirement_id.strip(), 'requirement_id', 1, 200)
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400

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
        return handle_api_exception(e, "update photo requirement")


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
            current_hash = compute_photo_hash(image_data)
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

        # Validate file type and size
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        allowed_mime_types = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
        max_file_size = 10 * 1024 * 1024  # 10MB limit

        # Check file extension
        if not image_file.filename:
            return jsonify({'error': 'Invalid file name'}), 400

        file_ext = image_file.filename.rsplit('.', 1)[1].lower() if '.' in image_file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'}), 400

        # Check MIME type
        if image_file.mimetype not in allowed_mime_types:
            return jsonify({'error': f'Invalid file type. Content type {image_file.mimetype} not allowed'}), 400

        # Check file size (if available)
        if hasattr(image_file, 'content_length') and image_file.content_length:
            if image_file.content_length > max_file_size:
                return jsonify({'error': f'File too large. Maximum size: {max_file_size // (1024*1024)}MB'}), 400

        # For large files, stream to temporary file to avoid loading into memory
        import tempfile
        import os

        temp_path = None
        try:
            # Create temporary file for streaming upload
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_path = temp_file.name
                # Stream the upload in chunks to avoid memory issues
                chunk_size = 8192  # 8KB chunks
                hash_obj = hashlib.sha256()
                total_size = 0

                while True:
                    chunk = image_file.stream.read(chunk_size)
                    if not chunk:
                        break

                    chunk_size_actual = len(chunk)
                    total_size += chunk_size_actual

                    # Check size limit during streaming
                    if total_size > max_file_size:
                        return jsonify({'error': f'File too large. Maximum size: {max_file_size // (1024*1024)}MB'}), 400

                    temp_file.write(chunk)
                    hash_obj.update(chunk)

                temp_file.flush()
                size_bytes = temp_file.tell()

            if size_bytes == 0:
                return jsonify({'error': 'Empty image file'}), 400

            # Get form data
            question_id_str = request.form.get('question_id')
            question_id = int(question_id_str) if question_id_str else None
            section_name = "general"
            if question_id:
                template_field = db.session.get(TemplateField, question_id)
                if template_field and template_field.section:
                    section_name = template_field.section.lower().replace(" ", "_")

            # Use provided ID or generate unique photo ID
            photo_id = request.form.get('id')
            if not photo_id:
                random_string = secrets.token_hex(4)
                photo_id = f"{survey.site_id}-{section_name}-{random_string}"

            # Check if photo already exists
            existing_photo = Photo.query.get(photo_id)

            # Get hash from streaming computation
            hash_value = hash_obj.hexdigest()

            # Generate thumbnail from file path to avoid loading large images into memory
            thumbnail_data = generate_thumbnail(image_path=temp_path, max_size=200)

            # Use file path instead of loading image data into memory to prevent OOM with large files
            image_path_for_upload = temp_path

            # Validate and sanitize description
            description = request.form.get('description', '')
            if description:
                description = Validator.validate_string_length(description, 'Photo description', 0, 5000)
                description = Validator.sanitize_html(description)

            # Validate category
            category_str = request.form.get('category', 'general')
            try:
                category = Validator.validate_choice(
                    category_str, 'Photo category',
                    [cat.value for cat in PhotoCategory]
                )
            except ValidationError:
                category = PhotoCategory.GENERAL.value  # Default fallback

            # Validate coordinates
            latitude_str = request.form.get('latitude', '0.0')
            longitude_str = request.form.get('longitude', '0.0')
            try:
                latitude, longitude = Validator.validate_coordinates(latitude_str, longitude_str)
            except ValidationError:
                # Default to 0,0 if invalid coordinates provided
                latitude, longitude = 0.0, 0.0

            # Validate tags structure
            tags_payload = request.form.get('tags', '')
            tags = []
            if tags_payload:
                try:
                    parsed = json.loads(tags_payload)
                    if isinstance(parsed, list):
                        # Validate each tag is a string and sanitize
                        tags = [Validator.sanitize_html(str(tag).strip()) for tag in parsed if str(tag).strip()]
                        # Limit to reasonable number of tags
                        tags = tags[:50]  # Max 50 tags
                    else:
                        tags = [Validator.sanitize_html(str(parsed).strip())]
                except json.JSONDecodeError:
                    # Fallback: comma-separated tags
                    tags = [Validator.sanitize_html(tag.strip()) for tag in tags_payload.split(',') if tag.strip()][:50]

            # Create or update photo record
            if existing_photo:
                photo = existing_photo
                # Update all fields from the client upload
                photo.upload_status = 'pending'
                photo.hash_value = hash_value
                photo.size_bytes = size_bytes
                photo.latitude = latitude
                photo.longitude = longitude
                photo.description = description
                photo.category = category
                photo.tags = json.dumps(tags)
                photo.question_id = question_id
                # Reset cloud URLs since we're uploading a new version
                photo.cloud_url = ''
                photo.thumbnail_url = ''
            else:
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
                    question_id=question_id,
                    tags=json.dumps(tags)
                )
                db.session.add(photo)

            db.session.commit()

            # Queue for cloud upload
            upload_queue = get_upload_queue()
            upload_queue.queue_photo_for_upload(photo_id, photo_path=image_path_for_upload, thumbnail_data=thumbnail_data)

            # Clean up temporary file after queuing (upload queue has copied it)
            os.unlink(image_path_for_upload)

            # Start upload queue if not already running
            upload_queue.start()

            return jsonify({
                'id': photo_id,
                'survey_id': survey_id,
                'upload_status': 'pending',
                'message': 'Photo uploaded and queued for cloud storage'
            }), 201

        finally:
            # Ensure temporary file is cleaned up even if exceptions occur
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    # Ignore cleanup errors to avoid masking the original exception
                    pass

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
