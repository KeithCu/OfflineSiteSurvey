"""Backend utility functions for Site Survey application."""
from flask import jsonify
from shared.utils import compute_photo_hash, should_show_field
from .models import db, Project, Site, Survey, SurveyResponse, SurveyTemplate, TemplateField, Photo
import logging


logger = logging.getLogger(__name__)


def api_error(message, status_code=400, log_level='warning', details=None):
    """
    Standardized API error response with consistent logging.

    Args:
        message (str): Error message for the client
        status_code (int): HTTP status code
        log_level (str): Logging level ('debug', 'info', 'warning', 'error', 'critical')
        details (dict, optional): Additional details for logging

    Returns:
        Flask response: JSON error response
    """
    # Log the error with appropriate level
    log_func = getattr(logger, log_level, logger.warning)
    if details:
        log_func(f"API Error ({status_code}): {message} - Details: {details}")
    else:
        log_func(f"API Error ({status_code}): {message}")

    # Return consistent JSON error format
    return jsonify({'error': message}), status_code


def handle_api_exception(e, operation="operation", status_code=500):
    """
    Handle exceptions in API endpoints with consistent logging and responses.

    Args:
        e (Exception): The exception that occurred
        operation (str): Description of the operation being performed
        status_code (int): HTTP status code to return

    Returns:
        Flask response: JSON error response
    """
    logger.error(f"Exception during {operation}: {str(e)}", exc_info=True)
    return api_error(f"Failed to {operation}", status_code, 'error')


def validate_foreign_key(table_name, column_name, value):
    """
    Validate that a foreign key reference exists.

    Args:
        table_name (str): Name of the table being referenced
        column_name (str): Name of the column being referenced
        value: The value to check for existence

    Returns:
        bool: True if reference exists or value is None, False otherwise
    """
    if value is None:
        return True  # Allow NULL values for optional FKs

    try:
        if table_name == 'projects':
            return db.session.get(Project, value) is not None
        elif table_name == 'sites':
            return db.session.get(Site, value) is not None
        elif table_name == 'survey':
            return db.session.get(Survey, value) is not None
        elif table_name == 'survey_template':
            return db.session.get(SurveyTemplate, value) is not None
        elif table_name == 'template_field':
            return db.session.get(TemplateField, value) is not None
        else:
            logger.warning(f"Unknown table for FK validation: {table_name}")
            return False
    except Exception as e:
        logger.error(f"Error validating FK {table_name}.{column_name}={value}: {e}")
        return False


def get_orphaned_records(relationship_type=None):
    """
    Find all orphaned records in the database.

    Args:
        relationship_type (str, optional): Specific relationship to check.
            Options: 'sites', 'surveys', 'responses', 'template_fields', 'photos'
            If None, returns all orphaned records.

    Returns:
        dict: Dictionary with relationship types as keys and lists of orphaned record IDs as values
    """
    orphaned = {}

    try:
        if relationship_type is None or relationship_type == 'sites':
            # Sites without valid projects
            orphaned_sites = []
            for site in Site.query.all():
                if not validate_foreign_key('projects', 'id', site.project_id):
                    orphaned_sites.append(site.id)
            if orphaned_sites:
                orphaned['sites'] = orphaned_sites

        if relationship_type is None or relationship_type == 'surveys':
            # Surveys without valid sites
            orphaned_surveys = []
            for survey in Survey.query.all():
                if not validate_foreign_key('sites', 'id', survey.site_id):
                    orphaned_surveys.append(survey.id)
            # Surveys without valid templates (SET NULL should handle this, but check anyway)
            for survey in Survey.query.filter(Survey.template_id.isnot(None)):
                if not validate_foreign_key('survey_template', 'id', survey.template_id):
                    orphaned_surveys.append(survey.id)
            if orphaned_surveys:
                orphaned['surveys'] = list(set(orphaned_surveys))  # Remove duplicates

        if relationship_type is None or relationship_type == 'responses':
            # Survey responses without valid surveys
            orphaned_responses = []
            for response in SurveyResponse.query.all():
                if not validate_foreign_key('survey', 'id', response.survey_id):
                    orphaned_responses.append(response.id)
            if orphaned_responses:
                orphaned['responses'] = orphaned_responses

        if relationship_type is None or relationship_type == 'template_fields':
            # Template fields without valid templates
            orphaned_fields = []
            for field in TemplateField.query.all():
                if not validate_foreign_key('survey_template', 'id', field.template_id):
                    orphaned_fields.append(field.id)
            if orphaned_fields:
                orphaned['template_fields'] = orphaned_fields

        if relationship_type is None or relationship_type == 'photos':
            # Photos without valid surveys
            orphaned_photos = []
            for photo in Photo.query.all():
                survey_valid = validate_foreign_key('survey', 'id', photo.survey_id)
                site_valid = validate_foreign_key('sites', 'id', photo.site_id)
                if not survey_valid or not site_valid:
                    orphaned_photos.append(photo.id)
            if orphaned_photos:
                orphaned['photos'] = orphaned_photos

    except Exception as e:
        logger.error(f"Error finding orphaned records: {e}")

    return orphaned


def cascade_delete_project(project_id):
    """
    Delete a project and all its child records (sites, surveys, responses, photos).

    Args:
        project_id (int): ID of the project to delete

    Returns:
        dict: Summary of deleted records
    """
    summary = {
        'projects': 0,
        'sites': 0,
        'surveys': 0,
        'responses': 0,
        'photos': 0
    }

    try:
        project = db.session.get(Project, project_id)
        if not project:
            return summary

        # Get all sites for this project
        sites = Site.query.filter_by(project_id=project_id).all()
        summary['sites'] = len(sites)

        # For each site, cascade delete
        for site in sites:
            site_summary = cascade_delete_site(site.id)
            summary['surveys'] += site_summary['surveys']
            summary['responses'] += site_summary['responses']
            summary['photos'] += site_summary['photos']

        # Delete the project
        db.session.delete(project)
        summary['projects'] = 1

        logger.info(f"Cascading delete completed for project {project_id}: {summary}")

    except Exception as e:
        logger.error(f"Error in cascade delete of project {project_id}: {e}")
        raise

    return summary


def cascade_delete_site(site_id):
    """
    Delete a site and all its child records (surveys, responses, photos).

    Args:
        site_id (int): ID of the site to delete

    Returns:
        dict: Summary of deleted records
    """
    summary = {
        'sites': 0,
        'surveys': 0,
        'responses': 0,
        'photos': 0
    }

    try:
        site = db.session.get(Site, site_id)
        if not site:
            return summary

        # Get all surveys for this site
        surveys = Survey.query.filter_by(site_id=site_id).all()
        summary['surveys'] = len(surveys)

        # For each survey, cascade delete
        for survey in surveys:
            survey_summary = cascade_delete_survey(survey.id)
            summary['responses'] += survey_summary['responses']
            summary['photos'] += survey_summary['photos']

        # Delete the site
        db.session.delete(site)
        summary['sites'] = 1

        logger.info(f"Cascading delete completed for site {site_id}: {summary}")

    except Exception as e:
        logger.error(f"Error in cascade delete of site {site_id}: {e}")
        raise

    return summary


def cascade_delete_survey(survey_id):
    """
    Delete a survey and all its child records (responses, photos).

    Args:
        survey_id (int): ID of the survey to delete

    Returns:
        dict: Summary of deleted records
    """
    summary = {
        'surveys': 0,
        'responses': 0,
        'photos': 0
    }

    try:
        survey = db.session.get(Survey, survey_id)
        if not survey:
            return summary

        # Delete survey responses
        responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
        summary['responses'] = len(responses)
        for response in responses:
            db.session.delete(response)

        # Delete photos for this survey
        photos = Photo.query.filter_by(survey_id=survey_id).all()
        summary['photos'] = len(photos)
        for photo in photos:
            db.session.delete(photo)

        # Delete the survey
        db.session.delete(survey)
        summary['surveys'] = 1

        logger.info(f"Cascading delete completed for survey {survey_id}: {summary}")

    except Exception as e:
        logger.error(f"Error in cascade delete of survey {survey_id}: {e}")
        raise

    return summary


def cascade_delete_template(template_id):
    """
    Delete a survey template and all its child records (fields).
    Also cleans up orphaned question_id references in SurveyResponse and Photo records.

    Args:
        template_id (int): ID of the template to delete

    Returns:
        dict: Summary of deleted records
    """
    summary = {
        'templates': 0,
        'template_fields': 0,
        'responses_cleaned': 0,
        'photos_cleaned': 0
    }

    try:
        template = db.session.get(SurveyTemplate, template_id)
        if not template:
            return summary

        # Get all field IDs that will be deleted
        fields = TemplateField.query.filter_by(template_id=template_id).all()
        field_ids = [field.id for field in fields]
        summary['template_fields'] = len(fields)

        # Clean up orphaned question_id references in SurveyResponse records
        # Since foreign keys are disabled for CRR tables, we handle this at application level
        if field_ids:
            responses_updated = db.session.query(SurveyResponse).filter(
                SurveyResponse.question_id.in_(field_ids)
            ).update({SurveyResponse.question_id: None}, synchronize_session=False)
            summary['responses_cleaned'] = responses_updated

            # Clean up orphaned question_id references in Photo records
            photos_updated = db.session.query(Photo).filter(
                Photo.question_id.in_(field_ids)
            ).update({Photo.question_id: None}, synchronize_session=False)
            summary['photos_cleaned'] = photos_updated

        # SQLAlchemy will handle cascade delete of template fields due to cascade='all, delete-orphan'
        # Delete the template (cascade will handle fields)
        db.session.delete(template)
        summary['templates'] = 1

        logger.info(f"Cascading delete completed for template {template_id}: {summary}")

    except Exception as e:
        logger.error(f"Error in cascade delete of template {template_id}: {e}")
        raise

    return summary