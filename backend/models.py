from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
import logging
from shared.models import (
    Base, Project, Site, Survey, SurveyResponse, AppConfig,
    SurveyTemplate, TemplateField, Photo, SurveyStatus, ProjectStatus
)

logger = logging.getLogger(__name__)
db = SQLAlchemy(model_class=Base)

def create_crr_tables(target, connection, **kw):
    """Make tables CRR for cr-sqlite sync."""
    logger.info("Initializing CRR tables for CRDT synchronization")
    connection.execute(text("PRAGMA foreign_keys = OFF;"))
    crr_tables = [
        'projects', 'sites', 'survey', 'survey_response',
        'survey_template', 'template_field', 'photo'
    ]
    successful_tables = []
    
    try:
        for table_name in crr_tables:
            try:
                connection.execute(text(f"SELECT crsql_as_crr('{table_name}');"))
                successful_tables.append(table_name)
                logger.debug(f"Made table '{table_name}' CRR-enabled")
            except Exception as e:
                error_msg = str(e).lower()
                # If table is already CRR-enabled, that's fine - just log and continue
                if 'already' in error_msg or 'exists' in error_msg or 'duplicate' in error_msg:
                    logger.debug(f"Table '{table_name}' is already CRR-enabled, skipping")
                    successful_tables.append(table_name)
                else:
                    logger.error(f"Failed to make {table_name} CRR: {e}", exc_info=True)
                    # Fail fast on first real error to avoid inconsistent state
                    raise RuntimeError(f"Failed to make table '{table_name}' CRR: {e}. Stopping CRR initialization to prevent inconsistent database state.")

        connection.execute(text("PRAGMA foreign_keys = ON;"))
        logger.info(f"Successfully initialized {len(successful_tables)} CRR tables for CRDT sync")
    except Exception:
        # Always restore foreign keys, even on failure
        connection.execute(text("PRAGMA foreign_keys = ON;"))
        raise
