import click
import json
import logging
from flask import current_app
from flask.cli import with_appcontext
from .models import db, AppConfig, SurveyTemplate, TemplateField, Photo
from .utils import compute_photo_hash

logger = logging.getLogger(__name__)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    logger.info("Starting database initialization")
    logger.info("Creating database tables and schema")
    db.create_all()
    logger.info("Database tables created successfully")

    # Ensure CRR tables are initialized (even if database already existed)
    # The event listener in app.py only fires on first creation, so we explicitly
    # initialize CRR tables here to handle both new and existing databases
    logger.info("Initializing CRR tables for CRDT synchronization")
    from .models import create_crr_tables
    with db.engine.connect() as conn:
        # Call create_crr_tables with metadata and connection (matching event listener signature)
        create_crr_tables(db.metadata, conn)
    logger.info("CRR tables initialized successfully")

    # Add CHECK constraints for data validation
    logger.info("Adding database constraints for data validation")
    with db.engine.connect() as conn:
        # Photo hash validation (SHA-256 is 64 characters)
        conn.execute(db.text("ALTER TABLE photo ADD CONSTRAINT IF NOT EXISTS chk_photo_hash_length CHECK (length(hash_value) = 64);"))
        logger.debug("Added photo hash length constraint")
        # Image compression quality range
        conn.execute(db.text("ALTER TABLE app_config ADD CONSTRAINT IF NOT EXISTS chk_compression_quality_range CHECK (key != 'image_compression_quality' OR (CAST(value AS INTEGER) >= 1 AND CAST(value AS INTEGER) <= 100));"))
        logger.debug("Added image compression quality range constraint")
        # Auto-sync interval must be non-negative
        conn.execute(db.text("ALTER TABLE app_config ADD CONSTRAINT IF NOT EXISTS chk_sync_interval_non_negative CHECK (key != 'auto_sync_interval' OR CAST(value AS INTEGER) >= 0);"))
        logger.debug("Added auto-sync interval non-negative constraint")
    logger.info("Database constraints added successfully")

    # Seed initial data
    logger.info("Seeding initial database configuration")
    if not AppConfig.query.filter_by(key='image_compression_quality').first():
        config = AppConfig(key='image_compression_quality', value='75')
        db.session.add(config)
        logger.info("Added default image_compression_quality config (75)")
    else:
        logger.debug("image_compression_quality config already exists")

    if not SurveyTemplate.query.filter_by(is_default=True).first():
        logger.info("Loading default survey template")
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'data', 'templates', 'store.json')
        logger.debug(f"Loading template from: {template_path}")
        with open(template_path, 'r') as f:
            template_data = json.load(f)

        template = SurveyTemplate(
            name=template_data['name'],
            description=template_data['description'],
            category=template_data['category'],
            is_default=True
        )
        section_tags = template_data.get('section_tags')
        if section_tags:
            template.section_tags = json.dumps(section_tags)
            logger.debug(f"Loaded section tags for template: {template.name}")
        db.session.add(template)
        db.session.flush()
        logger.debug(f"Created template '{template.name}' with ID {template.id}")
        
        field_count = len(template_data['fields'])
        logger.info(f"Adding {field_count} template fields")
        for field_data in template_data['fields']:
            field = TemplateField(template_id=template.id, **field_data)
            db.session.add(field)
        logger.info(f"Successfully added {field_count} template fields")
    else:
        logger.debug("Default survey template already exists")

    logger.info("Committing database changes")
    db.session.commit()
    logger.info("Database initialization completed successfully")
    click.echo('Initialized the database with indexes.')


@click.command('check-photo-integrity')
@click.option('--fix', is_flag=True, help='Attempt to fix integrity issues by re-computing hashes')
@with_appcontext
def check_photo_integrity_command(fix):
    """Check integrity of all photos in the database"""
    logger.info(f"Starting photo integrity check (fix={fix})")
    photos = Photo.query.all()
    logger.info(f"Checking integrity for {len(photos)} photos")
    issues_found = 0
    fixed = 0

    for photo in photos:
        current_hash = None
        actual_size = None

        # Check local data first (legacy support)
        if photo.image_data:
            current_hash = compute_photo_hash(photo.image_data)
            actual_size = len(photo.image_data)
        # Check cloud data if no local data or if we want to verify cloud integrity
        elif photo.cloud_url and photo.upload_status == 'completed':
            try:
                from .services.cloud_storage import get_cloud_storage
                from urllib.parse import urlparse
                cloud_storage = get_cloud_storage()

                def extract_object_name_from_url(url):
                    if not url:
                        return None
                    parsed = urlparse(url)
                    path = parsed.path.lstrip('/')
                    return path if path else None

                object_name = extract_object_name_from_url(photo.cloud_url)
                if object_name:
                    image_data = cloud_storage.download_photo(object_name)
                    current_hash = compute_photo_hash(image_data)
                    actual_size = len(image_data)
                    click.echo(f"  Verified photo {photo.id} integrity from cloud")
                else:
                    click.echo(f"  Skipping photo {photo.id}: invalid cloud URL format")
                    continue
            except Exception as e:
                click.echo(f"  Error downloading photo {photo.id} from cloud: {e}")
                continue
        else:
            # No data available to check
            continue

        size_matches = photo.size_bytes == actual_size if actual_size is not None else True

        if photo.hash_value != current_hash or not size_matches:
            issues_found += 1
            logger.warning(f"Photo integrity issue: photo_id={photo.id}, hash_match={photo.hash_value == current_hash}, size_match={size_matches}")
            click.echo(f"Integrity issue with photo {photo.id}:")
            if photo.hash_value != current_hash:
                click.echo(f"  Hash mismatch: stored={photo.hash_value}, computed={current_hash}")
            if not size_matches:
                click.echo(f"  Size mismatch: stored={photo.size_bytes}, actual={actual_size}")

            if fix and current_hash and actual_size is not None:
                photo.hash_value = current_hash
                photo.size_bytes = actual_size
                db.session.commit()
                fixed += 1
                logger.info(f"Fixed photo integrity: photo_id={photo.id}")
                click.echo(f"  Fixed photo {photo.id}")
            elif fix:
                logger.warning(f"Could not fix photo integrity: photo_id={photo.id}, no valid data available")
                click.echo(f"  Could not fix photo {photo.id}: no valid data available")

    if issues_found == 0:
        logger.info("Photo integrity check completed: All photos passed")
        click.echo("All photos passed integrity check")
    else:
        logger.warning(f"Photo integrity check completed: Found {issues_found} issues, fixed {fixed}")
        click.echo(f"Found {issues_found} integrity issues")
        if fix:
            click.echo(f"Fixed {fixed} photos")


@click.command('check-referential-integrity')
@click.option('--fix', is_flag=True, help='Attempt to fix integrity issues by deleting orphaned records')
@click.option('--relationship', help='Check specific relationship type (sites, surveys, responses, template_fields, photos)')
@with_appcontext
def check_referential_integrity_command(fix, relationship):
    """Check referential integrity of all foreign key relationships"""
    from .utils import get_orphaned_records
    from .models import db, Site, Survey, SurveyResponse, TemplateField, Photo

    orphaned = get_orphaned_records(relationship)

    # Add photo-site relationship check
    if 'photos' in orphaned:
        photo_ids = orphaned['photos']
        orphaned_photo_sites = []
        for photo_id in photo_ids:
            photo = db.session.get(Photo, photo_id)
            if photo and photo.site_id:
                site_exists = db.session.query(Site.query.filter_by(id=photo.site_id).exists()).scalar()
                if not site_exists:
                    orphaned_photo_sites.append(photo_id)
        if orphaned_photo_sites:
            orphaned.setdefault('photo_sites', []).extend(orphaned_photo_sites)
            # Fix: Define total_orphaned before using it
    total_orphaned = sum(len(records) for records in orphaned.values())

    total_orphaned = sum(len(records) for records in orphaned.values())

    if total_orphaned == 0:
        click.echo("All foreign key relationships are intact - no orphaned records found")
        return

    click.echo(f"Found {total_orphaned} orphaned records:")

    for relationship_type, record_ids in orphaned.items():
        click.echo(f"\n{relationship_type.upper()}: {len(record_ids)} orphaned records")

        if relationship_type == 'sites':
            for site_id in record_ids[:10]:  # Show first 10
                site = db.session.get(Site, site_id)
                if site:
                    click.echo(f"  Site ID {site_id}: '{site.name}' references invalid project_id {site.project_id}")
        elif relationship_type == 'surveys':
            for survey_id in record_ids[:10]:
                survey = db.session.get(Survey, survey_id)
                if survey:
                    site_valid = survey.site_id is not None
                    template_valid = survey.template_id is None or True  # We'll check template separately
                    if not site_valid:
                        click.echo(f"  Survey ID {survey_id}: '{survey.title}' references invalid site_id {survey.site_id}")
                    if survey.template_id and not template_valid:
                        click.echo(f"  Survey ID {survey_id}: '{survey.title}' references invalid template_id {survey.template_id}")
        elif relationship_type == 'responses':
            for response_id in record_ids[:10]:
                response = db.session.get(SurveyResponse, response_id)
                if response:
                    click.echo(f"  Response ID {response_id}: question '{response.question}' references invalid survey_id {response.survey_id}")
        elif relationship_type == 'template_fields':
            for field_id in record_ids[:10]:
                field = db.session.get(TemplateField, field_id)
                if field:
                    click.echo(f"  TemplateField ID {field_id}: '{field.question}' references invalid template_id {field.template_id}")
        elif relationship_type == 'photos':
            for photo_id in record_ids[:10]:
                photo = db.session.get(Photo, photo_id)
                if photo:
                    click.echo(f"  Photo ID {photo_id}: references invalid survey_id {photo.survey_id}")
        elif relationship_type == 'photo_sites':
            for photo_id in record_ids[:10]:
                photo = db.session.get(Photo, photo_id)
                if photo:
                    click.echo(f"  Photo ID {photo_id}: references invalid site_id {photo.site_id}")

        if len(record_ids) > 10:
            click.echo(f"  ... and {len(record_ids) - 10} more")

    if not fix:
        click.echo(f"\nUse --fix to delete these orphaned records")
        return

    # Fix mode - delete orphaned records
    click.echo(f"\nDeleting orphaned records...")

    deleted_counts = {'sites': 0, 'surveys': 0, 'responses': 0, 'template_fields': 0, 'photos': 0}

    try:
        # Delete in order to avoid constraint violations
        # Delete photos first (depend on surveys/sites)
        if 'photos' in orphaned:
            for photo_id in orphaned['photos']:
                photo = db.session.get(Photo, photo_id)
                if photo:
                    db.session.delete(photo)
                    deleted_counts['photos'] += 1

        # Delete survey responses (depend on surveys)
        if 'responses' in orphaned:
            for response_id in orphaned['responses']:
                response = db.session.get(SurveyResponse, response_id)
                if response:
                    db.session.delete(response)
                    deleted_counts['responses'] += 1

        # Delete surveys (depend on sites/templates)
        if 'surveys' in orphaned:
            for survey_id in orphaned['surveys']:
                survey = db.session.get(Survey, survey_id)
                if survey:
                    # Cascade delete any remaining responses/photos for this survey
                    responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
                    for response in responses:
                        db.session.delete(response)
                    photos = Photo.query.filter_by(survey_id=survey_id).all()
                    for photo in photos:
                        db.session.delete(photo)
                    db.session.delete(survey)
                    deleted_counts['surveys'] += 1

        # Delete template fields (depend on templates)
        if 'template_fields' in orphaned:
            for field_id in orphaned['template_fields']:
                field = db.session.get(TemplateField, field_id)
                if field:
                    db.session.delete(field)
                    deleted_counts['template_fields'] += 1

        # Delete sites (depend on projects)
        if 'sites' in orphaned:
            for site_id in orphaned['sites']:
                site = db.session.get(Site, site_id)
                if site:
                    # Cascade delete any remaining surveys/responses/photos for this site
                    surveys = Survey.query.filter_by(site_id=site_id).all()
                    for survey in surveys:
                        responses = SurveyResponse.query.filter_by(survey_id=survey.id).all()
                        for response in responses:
                            db.session.delete(response)
                        photos = Photo.query.filter_by(survey_id=survey.id).all()
                        for photo in photos:
                            db.session.delete(photo)
                        db.session.delete(survey)
                    photos = Photo.query.filter_by(site_id=site_id).all()
                    for photo in photos:
                        db.session.delete(photo)
                    db.session.delete(site)
                    deleted_counts['sites'] += 1

        db.session.commit()

        total_deleted = sum(deleted_counts.values())
        click.echo(f"Successfully deleted {total_deleted} orphaned records:")
        for relationship_type, count in deleted_counts.items():
            if count > 0:
                click.echo(f"  {relationship_type}: {count}")

    except Exception as e:
        db.session.rollback()
        click.echo(f"Error deleting orphaned records: {e}")
        return 1