from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError, IntegrityError, SQLAlchemyError
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

    # Check if cr-sqlite extension is available
    try:
        # Try a simple cr-sqlite function to verify extension is loaded
        connection.execute(text("SELECT crsql_version();"))
        logger.debug("cr-sqlite extension verified as available")
    except Exception as e:
        logger.error(f"cr-sqlite extension not available: {e}. CRR table creation will be skipped.")
        logger.error("Make sure cr-sqlite extension is properly installed and loaded before initializing the database.")
        raise RuntimeError(f"cr-sqlite extension required for CRDT functionality: {e}")

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
            except (OperationalError, IntegrityError) as e:
                # If table is already CRR-enabled, SQLite/CRDT may raise OperationalError
                # Check if it's a "table already exists" type error
                error_msg = str(e).lower()
                if 'already' in error_msg or 'exists' in error_msg or 'duplicate' in error_msg:
                    logger.debug(f"Table '{table_name}' is already CRR-enabled, skipping")
                    successful_tables.append(table_name)
                else:
                    logger.error(f"Failed to make {table_name} CRR: {e}", exc_info=True)
                    # Fail fast on first real error to avoid inconsistent state
                    raise RuntimeError(f"Failed to make table '{table_name}' CRR: {e}. Stopping CRR initialization to prevent inconsistent database state.")
            except Exception as e:
                # Catch any other unexpected exceptions
                logger.error(f"Unexpected error making {table_name} CRR: {e}", exc_info=True)
                raise RuntimeError(f"Failed to make table '{table_name}' CRR: {e}. Stopping CRR initialization to prevent inconsistent database state.")

        logger.info(f"Successfully initialized {len(successful_tables)} CRR tables for CRDT sync")
    finally:
        # Always restore foreign keys, even on failure
        try:
            connection.execute(text("PRAGMA foreign_keys = ON;"))
        except Exception as e:
            logger.error(f"Failed to re-enable foreign keys: {e}")
