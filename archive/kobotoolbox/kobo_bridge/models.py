from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

# User model to store CompanyCam tokens
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Encrypt these in production!
    companycam_access_token = db.Column(db.String(255))
    companycam_refresh_token = db.Column(db.String(255))
    companycam_token_expires_at = db.Column(db.DateTime)

class KoboForm(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kobo_uid = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)

class KoboSubmission(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    form_id = db.Column(db.String(36), db.ForeignKey('kobo_form.id'), nullable=False)
    kobo_id = db.Column(db.String(50), unique=True, nullable=False)
    submission_data = db.Column(db.Text, nullable=False) # Store raw JSON
    submitted_at = db.Column(db.DateTime, nullable=False)

    # Sync status
    sync_status = db.Column(db.String(50), default='Pending') # Pending, Synced, Failed
    sync_error = db.Column(db.Text, nullable=True)
    companycam_project_id = db.Column(db.String(50))
    synced_at = db.Column(db.DateTime, nullable=True)

class KoboAttachment(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = db.Column(db.String(36), db.ForeignKey('kobo_submission.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    kobo_url = db.Column(db.String(500), nullable=False)
    companycam_photo_id = db.Column(db.String(50))
