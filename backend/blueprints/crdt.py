"""CRDT sync blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import sqlite3
import uuid
import logging
from ..models import db
from ..services.crdt_service import CRDTService

logger = logging.getLogger(__name__)
bp = Blueprint('crdt', __name__, url_prefix='/api')


@bp.route('/changes', methods=['POST'])
def apply_changes():
    """Apply CRDT changes from client."""
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

    try:
        # Process changes using CRDTService
        applied_count, integrity_issues = CRDTService.process_changes(changes, conn, cursor)
        
        # Log sync completion
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

    except ValueError as e:
        # Validation errors (structural issues) return 400
        conn.rollback()
        logger.warning(f"CRDT sync: Validation error for site_id={site_id}: {e}")
        return jsonify({'error': str(e)}), 400
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