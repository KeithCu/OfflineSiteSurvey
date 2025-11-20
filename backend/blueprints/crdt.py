"""CRDT sync blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import sqlite3
import json
import uuid
import re
import logging
from ..models import db, Photo
from ..utils import compute_photo_hash
from ..services.crdt_service import CRDTService

logger = logging.getLogger(__name__)
bp = Blueprint('crdt', __name__, url_prefix='/api')

# Valid CRR table names (from create_crr_tables in models.py)
VALID_CRR_TABLES = {'projects', 'sites', 'survey', 'survey_response', 'survey_template', 'template_field', 'photo'}

# Valid column name pattern (alphanumeric and underscore only)
COLUMN_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


@bp.route('/changes', methods=['POST'])
def apply_changes():
    try:
        changes = request.get_json()
    except Exception:
        logger.warning("CRDT sync: Invalid JSON data received")
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(changes, list):
        logger.warning("CRDT sync: Changes must be a list")
        return jsonify({'error': 'Changes must be a list'}), 400

    if not changes:
        logger.debug("CRDT sync: No changes to apply")
        return jsonify({'message': 'No changes to apply'}), 200
    
    # Log sync start
    site_id = changes[0].get('site_id', 'unknown') if changes else 'unknown'
    logger.info(f"CRDT sync: Applying {len(changes)} changes from site_id={site_id}")

    conn = db.engine.raw_connection()
    cursor = conn.cursor()

    integrity_issues = []
    valid_changes = []

    try:
        for change in changes:
            # Validate required fields in change object
            required_fields = ['table', 'pk', 'cid', 'val', 'col_version', 'db_version', 'site_id']
            if not all(field in change for field in required_fields):
                return jsonify({'error': f'Change missing required fields: {required_fields}'}), 400

            # Security: Validate table name to prevent SQL injection
            table_name = change.get('table')
            if not isinstance(table_name, str) or table_name not in VALID_CRR_TABLES:
                return jsonify({'error': f'Invalid table name: {table_name}. Must be one of: {sorted(VALID_CRR_TABLES)}'}), 400

            # Security: Validate column name to prevent SQL injection
            column_name = change.get('cid')
            if not isinstance(column_name, str) or not COLUMN_NAME_PATTERN.match(column_name):
                return jsonify({'error': f'Invalid column name: {column_name}. Must be alphanumeric with underscores only'}), 400

            # Validate pk is valid JSON string
            pk_str = change.get('pk')
            if not isinstance(pk_str, str):
                return jsonify({'error': 'pk must be a JSON string'}), 400
            try:
                pk_data = json.loads(pk_str)
                if not isinstance(pk_data, dict):
                    return jsonify({'error': 'pk must be a JSON object'}), 400
            except json.JSONDecodeError:
                return jsonify({'error': 'pk must be valid JSON'}), 400

            # Validate version numbers are integers
            try:
                col_version = int(change.get('col_version'))
                db_version = int(change.get('db_version'))
                if col_version < 0 or db_version < 0:
                    return jsonify({'error': 'Version numbers must be non-negative integers'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'col_version and db_version must be integers'}), 400

            # Validate site_id is valid UUID format
            site_id = change.get('site_id')
            if not isinstance(site_id, str):
                return jsonify({'error': 'site_id must be a string'}), 400
            try:
                uuid.UUID(site_id)
            except (ValueError, TypeError):
                return jsonify({'error': f'site_id must be a valid UUID: {site_id}'}), 400

            # Validate foreign key references using unified CRDTService
            # Note: Foreign keys are disabled during CRR table creation for CRDT operations,
            # but we perform application-level validation with warnings (not blocking) to detect issues
            fk_issue = CRDTService.validate_foreign_key_change(change)
            if fk_issue:
                integrity_issues.append(fk_issue)
                # Continue - don't block sync, but log warning
            # if change['table'] == 'sites' and change['cid'] == 'project_id':
            #     if not validate_foreign_key('projects', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'Site references non-existent project_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'survey' and change['cid'] == 'site_id':
    #     if not validate_foreign_key('sites', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'Survey references non-existent site_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'survey' and change['cid'] == 'template_id' and change['val'] is not None:
    #     if not validate_foreign_key('survey_template', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'Survey references non-existent template_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'survey_response' and change['cid'] == 'survey_id':
    #     if not validate_foreign_key('survey', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'SurveyResponse references non-existent survey_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'template_field' and change['cid'] == 'template_id':
    #     if not validate_foreign_key('survey_template', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'TemplateField references non-existent template_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'photo' and change['cid'] == 'survey_id':
    #     if not validate_foreign_key('survey', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'Photo references non-existent survey_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'photo' and change['cid'] == 'site_id':
    #     if not validate_foreign_key('sites', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'Photo references non-existent site_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change
    #
    # elif change['table'] == 'photo' and change['cid'] == 'question_id' and change['val'] is not None:
    #     if not validate_foreign_key('template_field', 'id', change['val']):
    #         integrity_issues.append({
    #             'change': change,
    #             'error': f'Photo references non-existent question_id: {change["val"]}',
    #             'action': 'rejected'
    #         })
    #         continue  # Skip this change

            # Handle photo table changes - verify photo integrity for relevant changes
            if change['table'] == 'photo':
                # Extract photo ID from pk (format: '{"id":"photo_id"}')
                try:
                    pk_data = json.loads(change['pk'])
                    photo_id = pk_data.get('id')
                    # Use raw SQL on the same connection to avoid session inconsistency
                    cursor.execute("SELECT * FROM photo WHERE id = ?", (photo_id,))
                    photo_row = cursor.fetchone()
                    if photo_row:
                        # Convert row to dict for easier access
                        existing_photo = dict(zip([col[0] for col in cursor.description], photo_row))
                    else:
                        existing_photo = None

                    # CRITICAL: Reject all changes for photos with upload_status='pending'
                    # This prevents syncing incomplete uploads which could result in invalid cloud_url values
                    # Photos must complete upload before they can be synced to other clients
                    
                    # Reject changes that set upload_status='pending' (prevents syncing new pending photos)
                    if change['cid'] == 'upload_status' and change['val'] == 'pending':
                        integrity_issues.append({
                            'photo_id': photo_id,
                            'error': 'Cannot sync photo with upload_status=pending. Photo must complete upload first.',
                            'action': 'rejected'
                        })
                        continue  # Skip this change
                    
                    # Reject changes for existing photos that currently have upload_status='pending'
                    if existing_photo and existing_photo.get('upload_status') == 'pending':
                        integrity_issues.append({
                            'photo_id': photo_id,
                            'error': 'Cannot sync photo with upload_status=pending. Photo must complete upload first.',
                            'action': 'rejected'
                        })
                        continue  # Skip this change

                    # Validate cloud URL changes - download and verify hash (with fallback)
                    if change['cid'] == 'cloud_url' and change['val'] and existing_photo and existing_photo.get('hash_value'):
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
                                if downloaded_hash != existing_photo.get('hash_value'):
                                    integrity_issues.append({
                                        'photo_id': photo_id,
                                        'expected_hash': existing_photo.get('hash_value'),
                                        'received_hash': downloaded_hash,
                                        'action': 'rejected'
                                    })
                                    continue  # Skip this change
                        except Exception as e:
                            # Cloud storage verification failed - reject the change to prevent corrupted photos
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': f'Cloud verification failed: {str(e)}',
                                'action': 'rejected'
                            })
                            continue  # Skip this change

                    # Validate hash_value changes - ensure they match any existing cloud data
                    elif change['cid'] == 'hash_value' and change['val'] and existing_photo and existing_photo.get('cloud_url') and existing_photo.get('upload_status') == 'completed':
                        try:
                            from ..services.cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            object_name = extract_object_name_from_url(existing_photo.get('cloud_url'))
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
                            # Cloud verification failed - reject hash changes when cloud is unavailable
                            # to prevent accepting potentially incorrect hash values
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': f'Hash verification failed due to cloud unavailability: {str(e)}',
                                'action': 'rejected'
                            })
                            continue  # Skip this change

                    # Validate upload_status changes to 'completed' - verify cloud data exists and matches hash (with fallback)
                    elif change['cid'] == 'upload_status' and change['val'] == 'completed' and existing_photo and existing_photo.get('hash_value'):
                        if not existing_photo.get('cloud_url'):
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': 'Cannot mark upload as completed without cloud_url',
                                'action': 'rejected'
                            })
                            continue  # Skip this change

                        try:
                            from ..services.cloud_storage import get_cloud_storage
                            cloud_storage = get_cloud_storage()
                            object_name = extract_object_name_from_url(existing_photo.get('cloud_url'))
                            if object_name:
                                downloaded_data = cloud_storage.download_photo(object_name)
                                downloaded_hash = compute_photo_hash(downloaded_data)
                                if downloaded_hash != existing_photo.get('hash_value'):
                                    integrity_issues.append({
                                        'photo_id': photo_id,
                                        'expected_hash': existing_photo.get('hash_value'),
                                        'received_hash': downloaded_hash,
                                        'action': 'rejected'
                                    })
                                    continue  # Skip this change
                        except Exception as e:
                            # Cloud verification failed - reject the change to prevent corrupted photos
                            integrity_issues.append({
                                'photo_id': photo_id,
                                'error': f'Upload completion verification failed: {str(e)}',
                                'action': 'rejected'
                            })
                            continue  # Skip this change

                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                    # Log parsing errors but continue with change
                    integrity_issues.append({
                        'error': f'Failed to parse photo change data: {str(e)}',
                        'change': change,
                        'action': 'logged'
                    })

            # Collect valid changes for batch application
            valid_changes.append(change)

        # Apply all valid changes in a single short transaction
        for change in valid_changes:
            cursor.execute(
                "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
            )

        conn.commit()

        # Log sync completion
        applied_count = len(valid_changes)
        rejected_count = len(changes) - applied_count
        logger.info(f"CRDT sync: Applied {applied_count} changes, rejected {rejected_count} changes from site_id={site_id}")
        
        if integrity_issues:
            logger.warning(f"CRDT sync: {len(integrity_issues)} integrity issues detected for site_id={site_id}")
            for issue in integrity_issues[:5]:  # Log first 5 issues
                logger.warning(f"CRDT sync integrity issue: {issue.get('error', issue.get('action', 'unknown'))}")

        response = {'message': 'Changes applied successfully'}
        if integrity_issues:
            response['integrity_issues'] = integrity_issues
            response['message'] = 'Changes applied with integrity issues'

        return jsonify(response)

    except Exception as e:
        conn.rollback()
        logger.error(f"CRDT sync: Failed to apply changes from site_id={site_id}: {e}", exc_info=True)
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

        # Validate site_id parameter (client UUID)
        if not site_id:
            return jsonify({'error': 'site_id parameter is required'}), 400

        # Validate that site_id is a valid UUID format (client identifier)
        try:
            uuid.UUID(site_id)
        except (ValueError, TypeError):
            return jsonify({'error': f'Invalid site_id format: {site_id} is not a valid UUID'}), 400

    except Exception:
        return jsonify({'error': 'Invalid request parameters'}), 400

    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row

    try:
        # Filter out photo changes where upload_status='pending' to prevent syncing incomplete uploads
        # This prevents syncing photos before cloud upload completes, which could result in invalid cloud_url values
        cursor.execute(
            """SELECT c."table", c.pk, c.cid, c.val, c.col_version, c.db_version, c.site_id 
               FROM crsql_changes c
               LEFT JOIN photo p ON c."table" = 'photo' AND json_extract(c.pk, '$.id') = p.id
               WHERE c.db_version > ? AND c.site_id != ?
               AND (c."table" != 'photo' OR p.upload_status IS NULL OR p.upload_status != 'pending')""",
            (version, site_id)
        )

        changes = cursor.fetchall()
        change_count = len(changes)
        logger.info(f"CRDT sync: Returning {change_count} changes for site_id={site_id} (from version {version})")
        return jsonify([dict(row) for row in changes])

    except Exception as e:
        logger.error(f"CRDT sync: Failed to retrieve changes for site_id={site_id}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to retrieve changes: {str(e)}'}), 500
    finally:
        conn.close()