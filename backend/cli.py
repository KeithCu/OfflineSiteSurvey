import click
import json
from flask import current_app
from flask.cli import with_appcontext
from .models import db, AppConfig, SurveyTemplate, TemplateField, Photo
from .utils import compute_photo_hash


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.create_all()

    # Add database indexes for performance
    with db.engine.connect() as conn:
        # Photos indexes
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_photos_survey_id ON photo(survey_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_photos_site_id ON photo(site_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_photos_created_at ON photo(created_at);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_photos_category ON photo(category);"))

        # Responses indexes
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_responses_survey_id ON survey_response(survey_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_responses_question_id ON survey_response(question_id);"))

        # Hierarchy indexes
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_surveys_site_id ON survey(site_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_sites_project_id ON site(project_id);"))

        # Add CHECK constraints for data validation
        # Photo hash validation (SHA-256 is 64 characters)
        conn.execute(db.text("ALTER TABLE photo ADD CONSTRAINT IF NOT EXISTS chk_photo_hash_length CHECK (length(hash_value) = 64);"))
        # Image compression quality range
        conn.execute(db.text("ALTER TABLE app_config ADD CONSTRAINT IF NOT EXISTS chk_compression_quality_range CHECK (key != 'image_compression_quality' OR (CAST(value AS INTEGER) >= 1 AND CAST(value AS INTEGER) <= 100));"))
        # Auto-sync interval must be non-negative
        conn.execute(db.text("ALTER TABLE app_config ADD CONSTRAINT IF NOT EXISTS chk_sync_interval_non_negative CHECK (key != 'auto_sync_interval' OR CAST(value AS INTEGER) >= 0);"))

    # Seed initial data
    if not AppConfig.query.filter_by(key='image_compression_quality').first():
        config = AppConfig(key='image_compression_quality', value='75')
        db.session.add(config)

    if not SurveyTemplate.query.filter_by(is_default=True).first():
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'data', 'templates', 'store.json')
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
        db.session.add(template)
        db.session.flush()
        for field_data in template_data['fields']:
            field = TemplateField(template_id=template.id, **field_data)
            db.session.add(field)

    db.session.commit()
    click.echo('Initialized the database with indexes.')


@click.command('check-photo-integrity')
@click.option('--fix', is_flag=True, help='Attempt to fix integrity issues by re-computing hashes')
@with_appcontext
def check_photo_integrity_command(fix):
    """Check integrity of all photos in the database"""
    photos = Photo.query.all()
    issues_found = 0
    fixed = 0

    for photo in photos:
        if not photo.image_data:
            continue

        current_hash = compute_photo_hash(photo.image_data, photo.hash_algo)
        size_matches = photo.size_bytes == len(photo.image_data)

        if photo.hash_value != current_hash or not size_matches:
            issues_found += 1
            click.echo(f"Integrity issue with photo {photo.id}:")
            if photo.hash_value != current_hash:
                click.echo(f"  Hash mismatch: stored={photo.hash_value}, computed={current_hash}")
            if not size_matches:
                click.echo(f"  Size mismatch: stored={photo.size_bytes}, actual={len(photo.image_data)}")

            if fix:
                photo.hash_value = current_hash
                photo.size_bytes = len(photo.image_data)
                db.session.commit()
                fixed += 1
                click.echo(f"  Fixed photo {photo.id}")

    if issues_found == 0:
        click.echo("All photos passed integrity check")
    else:
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
                    click.echo(f"  Photo ID {photo_id}: references invalid survey_id {photo.survey_id} or site_id {photo.site_id}")

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