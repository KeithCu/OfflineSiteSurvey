"""CRDT sync blueprint for Flask API."""
from flask import Blueprint, jsonify, request
import sqlite3
import json
from ..models import db, Photo
from ..utils import compute_photo_hash


bp = Blueprint('crdt', __name__, url_prefix='/api')


@bp.route('/changes', methods=['POST'])
def apply_changes():
    changes = request.get_json()
    conn = db.engine.raw_connection()
    cursor = conn.cursor()

    integrity_issues = []

    for change in changes:
        # Verify photo integrity if this is a photo table change
        if change['table'] == 'photo' and change['cid'] == 'image_data' and change['val']:
            # Extract photo ID from pk (format: '{"id":"photo_id"}')
            try:
                pk_data = json.loads(change['pk'])
                photo_id = pk_data.get('id')

                # Check if we have existing photo data to compare
                existing_photo = Photo.query.get(photo_id)
                if existing_photo and existing_photo.hash_value:
                    # Verify the incoming data matches expected hash
                    incoming_hash = compute_photo_hash(change['val'], existing_photo.hash_algo)
                    if incoming_hash != existing_photo.hash_value:
                        integrity_issues.append({
                            'photo_id': photo_id,
                            'expected_hash': existing_photo.hash_value,
                            'received_hash': incoming_hash,
                            'action': 'rejected'
                        })
                        continue  # Skip this change
            except (json.JSONDecodeError, AttributeError):
                pass  # Continue with change if we can't parse

        cursor.execute(
            "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
        )

    conn.commit()
    conn.close()

    response = {'message': 'Changes applied successfully'}
    if integrity_issues:
        response['integrity_issues'] = integrity_issues
        response['message'] = 'Changes applied with integrity issues'

    return jsonify(response)


@bp.route('/changes', methods=['GET'])
def get_changes():
    version = request.args.get('version', 0)
    site_id = request.args.get('site_id')

    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row

    cursor.execute(
        "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id != ?",
        (version, site_id)
    )

    changes = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in changes])