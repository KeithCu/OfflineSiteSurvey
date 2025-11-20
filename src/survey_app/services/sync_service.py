"""Sync service for CRDT-specific logic."""
import json
import logging
from sqlalchemy import text

from shared.models import Photo


class SyncService:
    """Service for handling CRDT synchronization operations."""

    def __init__(self, session_factory, site_id, last_applied_changes=None):
        """Initialize sync service with session factory and site ID."""
        self.session_factory = session_factory
        self.site_id = site_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_applied_changes = last_applied_changes if last_applied_changes is not None else {}

    def _get_session(self):
        """Get a database session."""
        return self.session_factory()

    def get_changes_since(self, version):
        """Get CRDT changes since specified version."""
        session = self._get_session()
        try:
            conn = session.connection()
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            cursor.execute(
                """SELECT c."table", c.pk, c.cid, c.val, c.col_version, c.db_version, c.site_id 
                   FROM crsql_changes c
                   LEFT JOIN photo p ON c."table" = 'photo' AND json_extract(c.pk, '$.id') = p.id
                   WHERE c.db_version > ? AND c.site_id != ?
                   AND (c."table" != 'photo' OR p.upload_status IS NULL OR p.upload_status != 'pending')""",
                (version, self.site_id)
            )
            changes = cursor.fetchall()
            return [dict(zip([c[0] for c in cursor.description], row)) for row in changes]
        finally:
            session.close()

    def get_current_version(self):
        """Get current CRDT database version."""
        session = self._get_session()
        try:
            conn = session.connection()
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            cursor.execute("SELECT crsql_dbversion()")
            version = cursor.fetchone()[0]
            return version
        finally:
            session.close()

    def apply_changes(self, changes):
        """Apply CRDT changes from remote clients."""
        session = self._get_session()
        try:
            conn = session.connection()
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            integrity_issues = []
            applied_changes = {}
            
            for change in changes:
                table_name = change['table']
                change_version = change['db_version']
                last_applied = self.last_applied_changes.get(table_name, 0)
                
                if change_version <= last_applied:
                    continue
                    
                if table_name == 'photo' and change['cid'] == 'cloud_url' and change['val']:
                    try:
                        pk_data = json.loads(change['pk'])
                        photo_id = pk_data.get('id')
                        existing_photo = session.get(Photo, photo_id)
                        if existing_photo and existing_photo.hash_value and existing_photo.upload_status == 'completed':
                            pass
                    except (json.JSONDecodeError, AttributeError, TypeError):
                        pass
                        
                try:
                    cursor.execute(
                        "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (table_name, change['pk'], change['cid'], change['val'], change['col_version'], change_version, change['site_id'])
                    )
                    if table_name not in applied_changes or change_version > applied_changes[table_name]:
                        applied_changes[table_name] = change_version
                except Exception as e:
                    self.logger.error(f"Failed to apply change for table {table_name}: {e}")
                    continue
                    
            session.commit()
            
            for table_name, version in applied_changes.items():
                self.last_applied_changes[table_name] = max(
                    self.last_applied_changes.get(table_name, 0),
                    version
                )
                
            if integrity_issues:
                self.logger.warning(f"Photo integrity issues detected: {integrity_issues}")
                
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

