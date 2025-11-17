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