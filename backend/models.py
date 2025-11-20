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
    failed_tables = []
    successful_tables = []
    for table_name in crr_tables:
        try:
            connection.execute(text(f"SELECT crsql_as_crr('{table_name}');"))
            successful_tables.append(table_name)
            logger.debug(f"Made table '{table_name}' CRR-enabled")
        except Exception as e:
            failed_tables.append(table_name)
            logger.error(f"Failed to make {table_name} CRR: {e}", exc_info=True)

    if failed_tables:
        logger.critical(f"Failed to create CRR tables: {', '.join(failed_tables)}. CRDT synchronization will not work properly.")
        raise RuntimeError(f"Failed to create CRR tables: {', '.join(failed_tables)}. CRDT synchronization will not work properly.")

    connection.execute(text("PRAGMA foreign_keys = ON;"))
    logger.info(f"Successfully initialized {len(successful_tables)} CRR tables for CRDT sync")
