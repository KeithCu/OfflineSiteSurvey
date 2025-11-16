from flask import Blueprint, redirect, request, url_for, flash, session
import requests
import os
from .models import db, User
from datetime import datetime, timedelta

cc_auth = Blueprint('cc_auth', __name__)

@cc_auth.route('/auth')
def auth():
    """Redirect user to CompanyCam to authorize."""
    client_id = os.environ.get('COMPANYCAM_CLIENT_ID')
    redirect_uri = os.environ.get('COMPANYCAM_REDIRECT_URI')

    # We add a 'state' for security
    state = os.urandom(16).hex()
    session['companycam_oauth_state'] = state

    auth_url = (
        f"https://app.companycam.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&state={state}"
    )
    return redirect(auth_url)

@cc_auth.route('/callback')
def callback():
    """Handle the callback from CompanyCam."""
    code = request.args.get('code')
    state = request.args.get('state')

    if state != session.pop('companycam_oauth_state', None):
        flash('State mismatch. Authentication failed.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        # Exchange code for token
        url = 'https://app.companycam.com/oauth/token'
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': os.environ.get('COMPANYCAM_REDIRECT_URI'),
            'client_id': os.environ.get('COMPANYCAM_CLIENT_ID'),
            'client_secret': os.environ.get('COMPANYCAM_CLIENT_SECRET')
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Store tokens in DB for our admin user
        user = User.query.filter_by(username='admin').first()
        if user:
            user.companycam_access_token = token_data['access_token']
            user.companycam_refresh_token = token_data['refresh_token']
            expires_in = token_data['expires_in'] - 300 # 5-min buffer
            user.companycam_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            db.session.commit()
            flash('CompanyCam account connected successfully!', 'success')

    except Exception as e:
        flash(f'Error connecting CompanyCam: {str(e)}', 'danger')

    return redirect(url_for('main.dashboard'))
