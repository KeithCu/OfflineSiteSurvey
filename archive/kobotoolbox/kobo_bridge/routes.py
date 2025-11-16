from flask import Blueprint, render_template, flash
from .models import db, User, KoboForm, KoboSubmission
from .tasks import scheduler

main = Blueprint('main', __name__)

@main.route('/')
def dashboard():
    user = User.query.filter_by(username='admin').first()
    cc_authenticated = True if (user and user.companycam_access_token) else False

    # Get sync status
    job = scheduler.get_job('sync_job')
    last_run = job.last_run_time if job else None

    stats = {
        'total': KoboSubmission.query.count(),
        'synced': KoboSubmission.query.filter_by(sync_status='Synced').count(),
        'pending': KoboSubmission.query.filter_by(sync_status='Pending').count(),
        'failed': KoboSubmission.query.filter_by(sync_status='Failed').count(),
    }

    recent_submissions = KoboSubmission.query.order_by(
        KoboSubmission.submitted_at.desc()
    ).limit(20).all()

    return render_template(
        'dashboard.html',
        cc_authenticated=cc_authenticated,
        stats=stats,
        last_run=last_run,
        submissions=recent_submissions
    )
