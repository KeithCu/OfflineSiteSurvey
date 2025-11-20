"""CRDT Service for unified CRDT synchronization logic."""
import json
import logging
from ..models import db
from ..utils import validate_foreign_key

logger = logging.getLogger(__name__)

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
    def validate_changes(changes):
        """Validate a list of changes for foreign key integrity.
        
        Args:
            changes: List of change dictionaries
            
        Returns:
            tuple: (valid_changes, integrity_issues)
        """
        valid_changes = []
        integrity_issues = []
        
        for change in changes:
            # Validate FK using unified mapping
            fk_issue = CRDTService.validate_foreign_key_change(change)
            if fk_issue:
                integrity_issues.append(fk_issue)
                # Continue - don't block sync, but log warning
            
            valid_changes.append(change)
        
        return valid_changes, integrity_issues

