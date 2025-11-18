"""CRDT sync blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import sqlite3
import json
from ..models import db, Photo
from ..utils import compute_photo_hash


bp = Blueprint('crdt', __name__, url_prefix='/api')


@bp.route('/changes', methods=['POST'])
def apply_changes():
    try:
        changes = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(changes, list):
        return jsonify({'error': 'Changes must be a list'}), 400

    if not changes:
        return jsonify({'message': 'No changes to apply'}), 200

    conn = db.engine.raw_connection()
    cursor = conn.cursor()

    integrity_issues = []

    try:
        for change in changes:
            # Validate required fields in change object
            required_fields = ['table', 'pk', 'cid', 'val', 'col_version', 'db_version', 'site_id']
            if not all(field in change for field in required_fields):
                return jsonify({'error': f'Change missing required fields: {required_fields}'}), 400

            # Validate foreign key references to prevent orphaned records
            from ..utils import validate_foreign_key

            if change['table'] == 'sites' and change['cid'] == 'project_id':
                if not validate_foreign_key('projects', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'Site references non-existent project_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'survey' and change['cid'] == 'site_id':
                if not validate_foreign_key('sites', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'Survey references non-existent site_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'survey' and change['cid'] == 'template_id' and change['val'] is not None:
                if not validate_foreign_key('survey_template', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'Survey references non-existent template_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'survey_response' and change['cid'] == 'survey_id':
                if not validate_foreign_key('survey', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'SurveyResponse references non-existent survey_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'template_field' and change['cid'] == 'template_id':
                if not validate_foreign_key('survey_template', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'TemplateField references non-existent template_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'photo' and change['cid'] == 'survey_id':
                if not validate_foreign_key('survey', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'Photo references non-existent survey_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'photo' and change['cid'] == 'site_id':
                if not validate_foreign_key('sites', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'Photo references non-existent site_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            elif change['table'] == 'photo' and change['cid'] == 'question_id' and change['val'] is not None:
                if not validate_foreign_key('template_field', 'id', change['val']):
                    integrity_issues.append({
                        'change': change,
                        'error': f'Photo references non-existent question_id: {change["val"]}',
                        'action': 'rejected'
                    })
                    continue  # Skip this change

            # Handle photo table changes - verify photo integrity for relevant changes
            if change['table'] == 'photo':
                # Extract photo ID from pk (format: '{"id":"photo_id"}')
                try:
                    pk_data = json.loads(change['pk'])
                    photo_id = pk_data.get('id')
                    existing_photo = db.session.get(Photo, photo_id)

                    # Validate cloud URL changes - download and verify hash (with fallback)
                    if change['cid'] == 'cloud_url' and change['val'] and existing_photo and existing_photo.hash_value:
                        try:
                            from ..services.cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            # Extract object name from cloud URL
                            from urllib.parse import urlparse
                            def extract_object_name_from_url(url):
                                if not url:
                                    return None
                                parsed = urlparse(url)
                                path = parsed.path.lstrip('/')
                                return path if path else None

                            object_name = extract_object_name_from_url(change['val'])
                            if object_name:
                                downloaded_data = cloud_storage.download_photo(object_name)
                                downloaded_hash = compute_photo_hash(downloaded_data)
                                if downloaded_hash != existing_photo.hash_value:
                                    integrity_issues.append({
                                        'photo_id': photo_id,
                                        'expected_hash': existing_photo.hash_value,
                                        'received_hash': downloaded_hash,
                                        'action': 'rejected'
                                    })
                                    continue  # Skip this change
                        except Exception as e:
                            # Cloud storage temporarily unavailable - log warning but allow change
                            # This prevents valid syncs from being blocked by temporary network issues
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': f'Cloud verification failed (allowing change): {str(e)}',
                                'action': 'warning'
                            })
                            # Continue with change (don't skip)

                    # Validate hash_value changes - ensure they match any existing cloud data
                    elif change['cid'] == 'hash_value' and change['val'] and existing_photo and existing_photo.cloud_url and existing_photo.upload_status == 'completed':
                        try:
                            from ..services.cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            object_name = extract_object_name_from_url(existing_photo.cloud_url)
                            if object_name:
                                downloaded_data = cloud_storage.download_photo(object_name)
                                downloaded_hash = compute_photo_hash(downloaded_data)
                                if downloaded_hash != change['val']:
                                    integrity_issues.append({
                                        'photo_id': photo_id,
                                        'expected_hash': downloaded_hash,
                                        'received_hash': change['val'],
                                        'action': 'rejected'
                                    })
                                    continue  # Skip this change
                        except Exception as e:
                            # Log but don't reject - cloud might be temporarily unavailable
                            pass

                    # Validate upload_status changes to 'completed' - verify cloud data exists and matches hash (with fallback)
                    elif change['cid'] == 'upload_status' and change['val'] == 'completed' and existing_photo and existing_photo.hash_value:
                        if not existing_photo.cloud_url:
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': 'Cannot mark upload as completed without cloud_url',
                                'action': 'rejected'
                            })
                            continue  # Skip this change

                        try:
                            from ..services.cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            object_name = extract_object_name_from_url(existing_photo.cloud_url)
                            if object_name:
                                downloaded_data = cloud_storage.download_photo(object_name)
                                downloaded_hash = compute_photo_hash(downloaded_data)
                                if downloaded_hash != existing_photo.hash_value:
                                    integrity_issues.append({
                                        'photo_id': photo_id,
                                        'expected_hash': existing_photo.hash_value,
                                        'received_hash': downloaded_hash,
                                        'action': 'rejected'
                                    })
                                    continue  # Skip this change
                        except Exception as e:
                            # Cloud verification failed - allow the change but log warning
                            # The upload queue will handle re-verification later
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': f'Upload completion verification failed (allowing change): {str(e)}',
                                'action': 'warning'
                            })
                            # Continue with change (don't skip)

                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                    # Log parsing errors but continue with change
                    integrity_issues.append({
                        'error': f'Failed to parse photo change data: {str(e)}',
                        'change': change,
                        'action': 'logged'
                    })

            cursor.execute(
                "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
            )

        conn.commit()

        response = {'message': 'Changes applied successfully'}
        if integrity_issues:
            response['integrity_issues'] = integrity_issues
            response['message'] = 'Changes applied with integrity issues'

        return jsonify(response)

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Failed to apply changes: {str(e)}'}), 500
    finally:
        conn.close()


@bp.route('/changes', methods=['GET'])
def get_changes():
    try:
        version_str = request.args.get('version', '0')
        site_id = request.args.get('site_id')

        # Validate version parameter
        try:
            version = int(version_str)
        except ValueError:
            return jsonify({'error': 'Version must be an integer'}), 400

        # Validate site_id parameter
        if not site_id:
            return jsonify({'error': 'site_id parameter is required'}), 400

    except Exception:
        return jsonify({'error': 'Invalid request parameters'}), 400

    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row

    try:
        cursor.execute(
            "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id != ?",
            (version, site_id)
        )

        changes = cursor.fetchall()
        return jsonify([dict(row) for row in changes])

    except Exception as e:
        return jsonify({'error': f'Failed to retrieve changes: {str(e)}'}), 500
    finally:
        conn.close()