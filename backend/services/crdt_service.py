"""CRDT Service for unified CRDT synchronization logic."""
import json
import logging
import re
import uuid
from urllib.parse import urlparse
from ..models import db
from ..utils import validate_foreign_key, compute_photo_hash

logger = logging.getLogger(__name__)

# Valid CRR table names (from create_crr_tables in models.py)
VALID_CRR_TABLES = {'projects', 'sites', 'survey', 'survey_response', 'survey_template', 'template_field', 'photo'}

# Valid column name pattern (alphanumeric and underscore only)
COLUMN_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Foreign key validation mapping: table -> {column: (referenced_table, referenced_column)}
FK_VALIDATION_MAP = {
    'sites': {
        'project_id': ('projects', 'id')
    },
    'survey': {
        'site_id': ('sites', 'id'),
        'template_id': ('survey_template', 'id')
    },
    'survey_response': {
        'survey_id': ('survey', 'id')
    },
    'template_field': {
        'template_id': ('survey_template', 'id')
    },
    'photo': {
        'survey_id': ('survey', 'id'),
        'site_id': ('sites', 'id'),
        'question_id': ('template_field', 'id')
    }
}


class CRDTService:
    """Service class for CRDT synchronization operations."""
    
    @staticmethod
    def validate_change_structure(change):
        """Validate the structure and format of a change object.
        
        Args:
            change: Change dictionary to validate
            
        Returns:
            tuple: (error_message, None) if invalid, (None, validated_data) if valid
        """
        # Validate required fields
        required_fields = ['table', 'pk', 'cid', 'val', 'col_version', 'db_version', 'site_id']
        if not all(field in change for field in required_fields):
            return (f'Change missing required fields: {required_fields}', None)
        
        # Security: Validate table name to prevent SQL injection
        table_name = change.get('table')
        if not isinstance(table_name, str) or table_name not in VALID_CRR_TABLES:
            return (f'Invalid table name: {table_name}. Must be one of: {sorted(VALID_CRR_TABLES)}', None)
        
        # Security: Validate column name to prevent SQL injection
        column_name = change.get('cid')
        if not isinstance(column_name, str) or not COLUMN_NAME_PATTERN.match(column_name):
            return (f'Invalid column name: {column_name}. Must be alphanumeric with underscores only', None)
        
        # Validate pk is valid JSON string
        pk_str = change.get('pk')
        if not isinstance(pk_str, str):
            return ('pk must be a JSON string', None)
        try:
            pk_data = json.loads(pk_str)
            if not isinstance(pk_data, dict):
                return ('pk must be a JSON object', None)
        except json.JSONDecodeError:
            return ('pk must be valid JSON', None)
        
        # Validate version numbers are integers
        try:
            col_version = int(change.get('col_version'))
            db_version = int(change.get('db_version'))
            if col_version < 0 or db_version < 0:
                return ('Version numbers must be non-negative integers', None)
        except (ValueError, TypeError):
            return ('col_version and db_version must be integers', None)
        
        # Validate site_id is valid UUID format
        site_id = change.get('site_id')
        if not isinstance(site_id, str):
            return ('site_id must be a string', None)
        try:
            uuid.UUID(site_id)
        except (ValueError, TypeError):
            return (f'site_id must be a valid UUID: {site_id}', None)
        
        return (None, change)
    
    @staticmethod
    def validate_foreign_key_change(change):
        """Validate foreign key changes using FK_VALIDATION_MAP.
        
        Args:
            change: Change dictionary with 'table', 'cid', 'val' keys
            
        Returns:
            dict or None: Integrity issue dict if validation fails, None if valid
        """
        table_name = change.get('table')
        column_name = change.get('cid')
        value = change.get('val')
        
        # Skip None values (optional FKs)
        if value is None:
            return None
        
        # Check if this column needs FK validation
        table_fks = FK_VALIDATION_MAP.get(table_name, {})
        if column_name not in table_fks:
            return None
        
        referenced_table, referenced_column = table_fks[column_name]
        
        # Validate FK exists
        if not validate_foreign_key(referenced_table, referenced_column, value):
            return {
                'change': change,
                'error': f'{table_name}.{column_name} references non-existent {referenced_table}.{referenced_column}: {value}',
                'action': 'warning'
            }
        
        return None
    
    @staticmethod
    def _extract_object_name_from_url(url):
        """Extract object name from cloud storage URL."""
        if not url:
            return None
        parsed = urlparse(url)
        path = parsed.path.lstrip('/')
        return path if path else None
    
    @staticmethod
    def _get_pending_value(photo_id, column_name, existing_photo, pending_changes_by_photo):
        """Get the value for a column, checking pending changes first, then existing DB state.

        Args:
            photo_id: The photo ID to check
            column_name: The column name to get value for
            existing_photo: The current DB state for the photo
            pending_changes_by_photo: Dict of pending changes grouped by photo_id

        Returns:
            The value from pending changes, or existing DB state, or None
        """
        # Check pending changes first
        if photo_id in pending_changes_by_photo:
            photo_changes = pending_changes_by_photo[photo_id]
            if column_name in photo_changes:
                return photo_changes[column_name]

        # Fall back to existing DB state
        return existing_photo.get(column_name) if existing_photo else None

    @staticmethod
    def validate_photo_integrity(change, cursor, pending_changes_by_photo=None):
        """Validate photo integrity for photo table changes.

        Args:
            change: Change dictionary for photo table
            cursor: Database cursor for querying photo data
            pending_changes_by_photo: Optional dict of pending changes grouped by photo_id

        Returns:
            dict or None: Integrity issue dict if validation fails, None if valid
        """
        # Extract photo ID from pk (format: '{"id":"photo_id"}')
        try:
            pk_data = json.loads(change['pk'])
            photo_id = pk_data.get('id')
            
            # Query existing photo
            cursor.execute("SELECT * FROM photo WHERE id = ?", (photo_id,))
            photo_row = cursor.fetchone()
            if photo_row:
                existing_photo = dict(zip([col[0] for col in cursor.description], photo_row))
            else:
                existing_photo = None
            
            # Allow setting upload_status='pending' (needed for offline photo creation)
            # But block changing FROM 'pending' to other statuses during sync
            if change['cid'] == 'upload_status' and change['val'] != 'pending' and existing_photo and existing_photo.get('upload_status') == 'pending':
                return {
                    'photo_id': photo_id,
                    'error': 'Cannot change upload_status from pending during sync. Upload must complete first.',
                    'action': 'rejected'
                }
            
            # For existing photos with upload_status='pending', only block critical fields
            if existing_photo and existing_photo.get('upload_status') == 'pending':
                # Define which fields can be updated even when upload_status='pending'
                allowed_metadata_fields = {
                    'description', 'tags', 'category', 'latitude', 'longitude', 'section'
                }
                # Define fields that cannot be updated when upload_status='pending'
                blocked_fields = {
                    'cloud_url', 'hash_value', 'upload_status', 'size_bytes', 'file_path'
                }

                # Allow metadata updates, but block critical field changes
                if change['cid'] in blocked_fields:
                    return {
                        'photo_id': photo_id,
                        'error': f'Cannot update {change["cid"]} while photo upload is pending. Photo must complete upload first.',
                        'action': 'rejected'
                    }
                elif change['cid'] not in allowed_metadata_fields:
                    # Unknown field - block for safety
                    return {
                        'photo_id': photo_id,
                        'error': f'Cannot update {change["cid"]} while photo upload is pending. Photo must complete upload first.',
                        'action': 'rejected'
                    }
            
            # Validate cloud URL changes - download and verify hash
            if change['cid'] == 'cloud_url' and change['val']:
                expected_hash = CRDTService._get_pending_value(photo_id, 'hash_value', existing_photo, pending_changes_by_photo)
                if expected_hash:
                try:
                    from ..services.cloud_storage import get_cloud_storage
                    cloud_storage = get_cloud_storage()
                    object_name = CRDTService._extract_object_name_from_url(change['val'])
                    if object_name:
                        downloaded_data = cloud_storage.download_photo(object_name)
                        downloaded_hash = compute_photo_hash(downloaded_data)
                        if downloaded_hash != existing_photo.get('hash_value'):
                            return {
                                'photo_id': photo_id,
                                'expected_hash': existing_photo.get('hash_value'),
                                'received_hash': downloaded_hash,
                                'action': 'rejected'
                            }
                except Exception as e:
                    return {
                        'photo_id': photo_id,
                        'error': f'Cloud verification failed: {str(e)}',
                        'action': 'rejected'
                    }
            
            # Validate hash_value changes - ensure they match any existing cloud data
            elif change['cid'] == 'hash_value' and change['val']:
                cloud_url = CRDTService._get_pending_value(photo_id, 'cloud_url', existing_photo, pending_changes_by_photo)
                upload_status = CRDTService._get_pending_value(photo_id, 'upload_status', existing_photo, pending_changes_by_photo)
                if cloud_url and upload_status == 'completed':
                try:
                    from ..services.cloud_storage import get_cloud_storage
                    cloud_storage = get_cloud_storage()
                    object_name = CRDTService._extract_object_name_from_url(existing_photo.get('cloud_url'))
                    if object_name:
                        downloaded_data = cloud_storage.download_photo(object_name)
                        downloaded_hash = compute_photo_hash(downloaded_data)
                        if downloaded_hash != change['val']:
                            return {
                                'photo_id': photo_id,
                                'expected_hash': downloaded_hash,
                                'received_hash': change['val'],
                                'action': 'rejected'
                            }
                except Exception as e:
                    return {
                        'photo_id': photo_id,
                        'error': f'Hash verification failed due to cloud unavailability: {str(e)}',
                        'action': 'rejected'
                    }
            
            # Validate upload_status changes to 'completed' - verify cloud data exists and matches hash
            elif change['cid'] == 'upload_status' and change['val'] == 'completed':
                cloud_url = CRDTService._get_pending_value(photo_id, 'cloud_url', existing_photo, pending_changes_by_photo)
                hash_value = CRDTService._get_pending_value(photo_id, 'hash_value', existing_photo, pending_changes_by_photo)
                if hash_value:
                if not cloud_url:
                    return {
                        'photo_id': photo_id,
                        'error': 'Cannot mark upload as completed without cloud_url',
                        'action': 'rejected'
                    }
                
                try:
                    from ..services.cloud_storage import get_cloud_storage
                    cloud_storage = get_cloud_storage()
                    object_name = CRDTService._extract_object_name_from_url(existing_photo.get('cloud_url'))
                    if object_name:
                        downloaded_data = cloud_storage.download_photo(object_name)
                        downloaded_hash = compute_photo_hash(downloaded_data)
                        if downloaded_hash != existing_photo.get('hash_value'):
                            return {
                                'photo_id': photo_id,
                                'expected_hash': existing_photo.get('hash_value'),
                                'received_hash': downloaded_hash,
                                'action': 'rejected'
                            }
                except Exception as e:
                    return {
                        'photo_id': photo_id,
                        'error': f'Upload completion verification failed: {str(e)}',
                        'action': 'rejected'
                    }
            
            return None
            
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            return {
                'error': f'Failed to parse photo change data: {str(e)}',
                'change': change,
                'action': 'logged'
            }
    
    @staticmethod
    def process_changes(changes, conn, cursor):
        """Process and validate a list of changes, applying valid ones.
        
        Args:
            changes: List of change dictionaries
            conn: Database connection
            cursor: Database cursor
            
        Returns:
            tuple: (applied_count, integrity_issues)
            
        Raises:
            ValueError: If any change has structural validation errors
        """
        integrity_issues = []
        valid_changes = []

        # Build pending changes map for atomic validation
        pending_changes_by_photo = {}
        for change in changes:
            if change.get('table') == 'photo':
                try:
                    pk_data = json.loads(change['pk'])
                    photo_id = pk_data.get('id')
                    if photo_id:
                        if photo_id not in pending_changes_by_photo:
                            pending_changes_by_photo[photo_id] = {}
                        pending_changes_by_photo[photo_id][change['cid']] = change['val']
                except (json.JSONDecodeError, KeyError):
                    pass  # Skip invalid changes, they'll be caught later

        for change in changes:
            # Validate change structure
            error_msg, validated_change = CRDTService.validate_change_structure(change)
            if error_msg:
                # Structural validation errors should be returned as HTTP 400
                raise ValueError(error_msg)
            
            # Validate foreign key references
            fk_issue = CRDTService.validate_foreign_key_change(validated_change)
            if fk_issue:
                integrity_issues.append(fk_issue)
                # Continue - don't block sync, but log warning
            
            # Handle photo table changes - verify photo integrity
            if validated_change['table'] == 'photo':
                photo_issue = CRDTService.validate_photo_integrity(validated_change, cursor, pending_changes_by_photo)
                if photo_issue:
                    integrity_issues.append(photo_issue)
                    # Skip rejected photo changes
                    if photo_issue.get('action') == 'rejected':
                        continue
            
            # Collect valid changes for batch application
            valid_changes.append(validated_change)
        
        # Apply all valid changes in a single transaction
        for change in valid_changes:
            cursor.execute(
                "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
            )
        
        conn.commit()
        
        return (len(valid_changes), integrity_issues)

