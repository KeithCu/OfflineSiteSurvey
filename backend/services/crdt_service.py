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

# Primary key type validation mapping: table -> {pk_field: expected_type}
PK_TYPE_VALIDATION_MAP = {
    'projects': {'id': int},
    'sites': {'id': int},
    'survey': {'id': int},
    'survey_response': {'id': int},
    'survey_template': {'id': int},
    'template_field': {'id': int},
    'photo': {'id': str},  # Photo IDs are strings (UUID-like)
    'app_config': {'id': int},
    'teams': {'id': int},
    'users': {'id': int},
}

# Table column validation mapping: table -> set of valid column names
TABLE_COLUMNS_MAP = {
    'projects': {'id', 'name', 'description', 'status', 'client_info', 'due_date', 'priority', 'created_at', 'updated_at'},
    'sites': {'id', 'name', 'address', 'latitude', 'longitude', 'notes', 'project_id', 'created_at', 'updated_at'},
    'survey': {'id', 'title', 'description', 'site_id', 'created_at', 'updated_at', 'status', 'template_id'},
    'survey_response': {'id', 'survey_id', 'question', 'answer', 'response_type', 'latitude', 'longitude', 'created_at', 'question_id', 'field_type'},
    'survey_template': {'id', 'name', 'description', 'category', 'is_default', 'created_at', 'updated_at', 'section_tags'},
    'template_field': {'id', 'template_id', 'field_type', 'question', 'description', 'required', 'options', 'order_index', 'section', 'conditions', 'photo_requirements', 'section_weight'},
    'photo': {'id', 'survey_id', 'site_id', 'cloud_url', 'thumbnail_url', 'upload_status', 'retry_count', 'last_retry_at', 'latitude', 'longitude', 'description', 'category', 'created_at', 'hash_value', 'size_bytes', 'file_path', 'requirement_id', 'fulfills_requirement', 'tags', 'question_id', 'corrupted'},
    'app_config': {'id', 'key', 'value', 'description', 'category', 'updated_at'},
    'teams': {'id', 'name', 'description', 'created_at', 'updated_at'},
    'users': {'id', 'username', 'email', 'password_hash', 'role', 'team_id', 'created_at', 'updated_at'},
}

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
    def validate_primary_key_content(table_name, pk_data):
        """Validate that primary key content matches expected types for the table.

        Args:
            table_name: Name of the table
            pk_data: Parsed JSON primary key data

        Returns:
            str or None: Error message if validation fails, None if valid
        """
        if table_name not in PK_TYPE_VALIDATION_MAP:
            return f'Unknown table for PK validation: {table_name}'

        expected_pk_types = PK_TYPE_VALIDATION_MAP[table_name]

        # Check that all expected PK fields are present
        for pk_field in expected_pk_types:
            if pk_field not in pk_data:
                return f'Primary key missing required field: {pk_field}'

        # Check that PK field values match expected types
        for pk_field, expected_type in expected_pk_types.items():
            value = pk_data[pk_field]
            if not isinstance(value, expected_type):
                return f'Primary key field {pk_field} must be {expected_type.__name__}, got {type(value).__name__}'

        return None

    @staticmethod
    def validate_column_name(table_name, column_name):
        """Validate that column name exists in the table schema.

        Args:
            table_name: Name of the table
            column_name: Name of the column to validate

        Returns:
            str or None: Error message if validation fails, None if valid
        """
        if table_name not in TABLE_COLUMNS_MAP:
            return f'Unknown table for column validation: {table_name}'

        if column_name not in TABLE_COLUMNS_MAP[table_name]:
            valid_columns = sorted(TABLE_COLUMNS_MAP[table_name])
            return f'Column "{column_name}" does not exist in table "{table_name}". Valid columns: {", ".join(valid_columns)}'

        return None

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

        # Validate column exists in table schema
        column_validation_error = CRDTService.validate_column_name(table_name, column_name)
        if column_validation_error:
            return (column_validation_error, None)
        
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

        # Validate primary key content types
        pk_validation_error = CRDTService.validate_primary_key_content(table_name, pk_data)
        if pk_validation_error:
            return (pk_validation_error, None)
        
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
        
        # Apply all valid changes in a single transaction and audit conflicts
        for change in valid_changes:
            # Check current state before applying change (for conflict detection)
            current_state = CRDTService._get_current_state(cursor, change['table'], change['pk'], change['cid'])

            # Apply the change
            cursor.execute(
                "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
            )

            # Check if a conflict occurred by comparing with expected result
            CRDTService._audit_conflict_if_needed(cursor, change, current_state)
        
        conn.commit()

        return (len(valid_changes), integrity_issues)

    @staticmethod
    def _get_current_state(cursor, table_name, pk_json, column_name):
        """Get the current state of a specific cell before applying a change.

        Args:
            cursor: Database cursor
            table_name: Table name
            pk_json: Primary key as JSON string
            column_name: Column name

        Returns:
            dict: Current state info or None if not found
        """
        try:
            # Parse PK to get the actual values for WHERE clause
            pk_data = json.loads(pk_json)

            # Build WHERE clause from PK
            where_conditions = []
            params = []
            for key, value in pk_data.items():
                where_conditions.append(f"{key} = ?")
                params.append(value)

            where_clause = " AND ".join(where_conditions)
            query = f"SELECT {column_name} FROM {table_name} WHERE {where_clause}"

            cursor.execute(query, params)
            result = cursor.fetchone()

            if result:
                return {'value': result[0]}
            else:
                return None

        except Exception as e:
            logger.warning(f"Error getting current state for {table_name}.{column_name} with pk {pk_json}: {e}")
            return None

    @staticmethod
    def _audit_conflict_if_needed(cursor, change, previous_state):
        """Check if a conflict occurred and log it to the audit table.

        Args:
            cursor: Database cursor
            change: The change that was applied
            previous_state: State before the change was applied
        """
        try:
            # Get the new state after applying the change
            new_state = CRDTService._get_current_state(cursor, change['table'], change['pk'], change['cid'])

            if new_state and previous_state:
                # If the value changed and it wasn't what we expected, a conflict occurred
                expected_value = change['val']
                actual_value = new_state['value']

                if actual_value != expected_value:
                    # This indicates a conflict resolution occurred
                    CRDTService._log_conflict(
                        cursor,
                        change['table'],
                        change['pk'],
                        change['cid'],
                        expected_value,  # The "lost" value (what we tried to set)
                        actual_value,    # The "winning" value (what actually got set)
                        change['site_id']
                    )

        except Exception as e:
            logger.warning(f"Error auditing conflict for change {change}: {e}")

    @staticmethod
    def _log_conflict(cursor, table_name, pk_json, column_name, lost_value, winning_value, site_id):
        """Log a conflict to the audit table.

        Args:
            cursor: Database cursor
            table_name: Table name
            pk_json: Primary key as JSON string
            column_name: Column name
            lost_value: The value that was lost
            winning_value: The value that won
            site_id: Site ID that originated the losing change
        """
        try:
            cursor.execute("""
                INSERT INTO crdt_conflict_audit
                (table_name, pk, cid, lost_value, winning_value, site_id, resolution_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (table_name, pk_json, column_name, str(lost_value), str(winning_value), site_id, 'last_write_wins'))

            logger.info(f"Logged CRDT conflict: {table_name}.{column_name} for pk {pk_json} - lost: {lost_value}, won: {winning_value}")

        except Exception as e:
            logger.error(f"Error logging CRDT conflict: {e}")

