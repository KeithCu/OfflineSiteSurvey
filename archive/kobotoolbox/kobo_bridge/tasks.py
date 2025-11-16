from apscheduler.schedulers.background import BackgroundScheduler
from .models import db, User, KoboForm, KoboSubmission, KoboAttachment
from .kobo_client import KoboClient
from .companycam_client import CompanyCamClient
from datetime import datetime
import json

scheduler = BackgroundScheduler(daemon=True)

def init_scheduler(app):
    """Initialize and start the scheduler."""
    scheduler.add_job(
        func=run_sync_job,
        trigger='interval',
        seconds=300, # Run every 5 minutes
        id='sync_job',
        replace_existing=True,
        kwargs={'app': app}
    )
    if not scheduler.running:
        scheduler.start()

def run_sync_job(app):
    """The main background job function."""
    with app.app_context():
        print(f"[{datetime.utcnow()}] Running background sync job...")

        # 1. Check if CompanyCam is authenticated
        user = User.query.filter_by(username='admin').first()
        if not user or not user.companycam_access_token:
            print("CompanyCam not authenticated. Skipping sync.")
            return

        try:
            kobo_client = KoboClient()
            cc_client = CompanyCamClient(user_id='admin') # Uses admin's tokens

            # 2. Sync Kobo Forms
            kobo_forms = kobo_client.get_forms()
            for form_data in kobo_forms:
                form = KoboForm.query.filter_by(kobo_uid=form_data['uid']).first()
                if not form:
                    form = KoboForm(
                        kobo_uid=form_data['uid'],
                        name=form_data['name']
                    )
                    db.session.add(form)
                    db.session.commit()

                # 3. Sync Submissions for each form
                sync_new_submissions(kobo_client, cc_client, form)

            print("Sync job completed.")

        except Exception as e:
            print(f"Error during sync job: {str(e)}")

def sync_new_submissions(kobo_client, cc_client, form):
    """Syncs new submissions for a given form."""
    print(f"Checking for submissions for form: {form.name}")
    new_submissions = kobo_client.get_submissions(form.kobo_uid, form.last_sync)

    if not new_submissions:
        print("No new submissions found.")
        return

    for sub_data in new_submissions:
        # Check if we already processed this
        kobo_id = str(sub_data['_id'])
        if KoboSubmission.query.filter_by(kobo_id=kobo_id).first():
            continue

        print(f"Processing new submission {kobo_id}...")

        # Create local submission record
        submission = KoboSubmission(
            form_id=form.id,
            kobo_id=kobo_id,
            submission_data=json.dumps(sub_data),
            submitted_at=datetime.fromisoformat(sub_data['_submission_time'].replace('Z', '+00:00')),
            sync_status='Pending'
        )
        db.session.add(submission)
        db.session.commit()

        try:
            # --- CompanyCam Logic ---
            # 1. Create Project
            project_name = sub_data.get('store_name', f"Kobo Survey {kobo_id}")
            project_address = sub_data.get('store_address')

            cc_project = cc_client.create_project(
                name=project_name,
                address=project_address
            )
            cc_project_id = cc_project['id']
            submission.companycam_project_id = cc_project_id

            # 2. Upload Photos
            for attachment in sub_data.get('_attachments', []):
                filename = attachment['filename'].split('/')[-1]
                kobo_url = attachment['download_url']

                # Download photo from Kobo IN MEMORY
                photo_bytes = kobo_client.download_attachment_in_memory(kobo_url)

                # Upload photo to CompanyCam FROM MEMORY
                cc_photo = cc_client.upload_photo(
                    project_id=cc_project_id,
                    photo_data=photo_bytes,
                    filename=filename,
                    captured_at=submission.submitted_at
                )

                # Store local attachment record
                att_record = KoboAttachment(
                    submission_id=submission.id,
                    filename=filename,
                    kobo_url=kobo_url,
                    companycam_photo_id=cc_photo['id']
                )
                db.session.add(att_record)

            # Mark as synced
            submission.sync_status = 'Synced'
            submission.synced_at = datetime.utcnow()
            print(f"Successfully synced submission {kobo_id} to CC project {cc_project_id}")

        except Exception as e:
            print(f"Failed to sync submission {kobo_id}: {str(e)}")
            submission.sync_status = 'Failed'
            submission.sync_error = str(e)

        db.session.commit()

    # Update the form's last_sync time to now
    form.last_sync = datetime.utcnow()
    db.session.commit()
