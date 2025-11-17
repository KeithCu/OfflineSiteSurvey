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

            # Handle photo table changes - verify cloud URLs instead of image data
            if change['table'] == 'photo' and change['cid'] == 'cloud_url' and change['val']:
                # Extract photo ID from pk (format: '{"id":"photo_id"}')
                try:
                    pk_data = json.loads(change['pk'])
                    photo_id = pk_data.get('id')

                    # Check if we have existing photo record
                    existing_photo = db.session.get(Photo, photo_id)
                    if existing_photo and existing_photo.hash_value:
                        # Download photo from cloud URL and verify hash
                        try:
                            from ..services.cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            # Extract object name from URL or use cloud_object_name if available
                            # For now, assume cloud_object_name is synced too
                            if existing_photo.cloud_object_name:
                                downloaded_data = cloud_storage.download_photo(existing_photo.cloud_object_name)
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
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': f'Failed to verify cloud photo: {str(e)}',
                                'action': 'rejected'
                            })
                            continue  # Skip this change
                except (json.JSONDecodeError, AttributeError, TypeError):
                    pass  # Continue with change if we can't parse

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