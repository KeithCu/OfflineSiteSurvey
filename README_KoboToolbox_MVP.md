# Offline Site Survey MVP - Self-Hosted KoboToolbox Bridge

## Overview

This guide implements a robust, automated **Minimum Viable Product (MVP)** for offline site surveys using the **Self-Hosted KoboToolbox Bridge approach**.

We deploy your own **private KoboToolbox server** for complete data control and build an automated **Flask Bridge** to process survey data and sync it to CompanyCam.

**Why Self-Hosted?**
- ✅ **Complete data sovereignty** - all survey data stays on your infrastructure
- ✅ **No usage limits** - unlimited surveys and storage
- ✅ **Enhanced security** - control access and compliance
- ✅ **Customization** - modify server behavior as needed
- ✅ **Offline reliability** - no dependency on external services

**Core Architecture:**

1. **Data Collection (Android):** Technicians use the **KoBoCollect** app for offline data/photo capture.

2. **Data Inbox (Private Server):** KoBoCollect syncs to your **self-hosted KoboToolbox server** running on your infrastructure.

3. **Bridge & Portal (Your Flask App):** A Flask app running on your Linode server, which:
   * Runs a background task to automatically poll your private KoboToolbox API.
   * Pulls new surveys and photos from your private server.
   * Pushes them to the CompanyCam API using a proper OAuth 2.0 connection.
   * Provides a simple web dashboard to monitor sync status.

---

## 🛑 Critical Limitation: Android-Only

This approach is **Android-Only**. The official **KoBoCollect** and **ODK Collect** apps do not have iOS versions.

If iOS support is a requirement, you must use a different client, such as **Enketo** (Kobo's web-form client), which works in any mobile browser but has different offline capabilities. This plan proceeds assuming an Android-only client is acceptable for the MVP.

---

## Prerequisites

* Python 3.11+
* `uv` (or `pip`)
* **Server Requirements for Self-Hosted KoboToolbox:**
  - **Arch Linux** or **Debian** server
  - 4GB RAM minimum, 8GB recommended
  - Docker and Docker Compose
  - Domain name with SSL certificate
* CompanyCam account (with API access, requires Pro plan or higher)
* Android device
* PostgreSQL server (for both KoboToolbox and your Flask bridge)

---

## Phase 1: Self-Hosted KoboToolbox Server Setup (4-6 Hours)

This phase sets up your private KoboToolbox server. This gives you complete control over your data and eliminates any usage limits.

### 1. **Server Preparation**

#### **Arch Linux:**
```bash
# Update system
sudo pacman -Syu

# Install Docker and Docker Compose
sudo pacman -S docker docker-compose

# Enable and start Docker service
sudo systemctl enable docker.service
sudo systemctl start docker.service

# Add your user to docker group (optional)
sudo usermod -aG docker $USER
```

#### **Debian:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose

# Enable and start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Add your user to docker group (optional)
sudo usermod -aG docker $USER
```

### 2. **Deploy KoboToolbox Using kobo-install**
```bash
# Clone the installer
git clone https://github.com/kobotoolbox/kobo-install
cd kobo-install

# Make the installer executable
chmod +x run.py

# Run the installer (interactive setup)
python3 run.py

# During setup, configure:
# - Domain: your-survey-server.com
# - HTTPS: Enable SSL
# - Database: PostgreSQL (recommended)
# - Admin user: Create your admin account
```

### 3. **Alternative: Manual Docker Deployment**
If you prefer more control:

```bash
# Create project directory
mkdir kobo-server && cd kobo-server

# Download docker-compose template
curl -O https://raw.githubusercontent.com/kobotoolbox/kobo-docker/master/docker-compose.yml

# Customize the configuration
# Edit docker-compose.yml with your settings
```

### 4. **Access Your Server**
- Open `https://your-survey-server.com` in your browser
- Log in with the admin account you created
- Verify the server is running properly

### 5. **Create Survey Form**
1. **Create Project:**
   * Click "New" → "Project" → "Build from scratch"
   * Name it "Site Survey MVP"

2. **Add Questions:**
   * `store_name` (Text, Required)
   * `store_address` (Text)
   * `electrical_panel_photo` (Image)
   * `structural_issue_photo` (Image)
   * `notes` (Text)

3. **Deploy the Form:**
   * Click "Deploy" in the form builder

### 6. **Get API Token**
1. Go to your user settings: `https://your-survey-server.com/token/`
2. Copy your API token (you'll need this for the bridge)

### 7. **Configure KoBo Collect (Android App)**
1. **Install App:**
   * Download "KoBo Collect" from Google Play Store

2. **Configure Server:**
   * Open Settings → Server Settings
   * **URL:** `https://your-survey-server.com`
   * **Username:** `your-admin-username`
   * **Password:** `your-admin-password`

3. **Test Data Collection:**
   * Go to "Get Blank Form" → Download "Site Survey MVP"
   * Put phone in Airplane Mode
   * Fill out 2-3 test surveys with photos
   * Turn off Airplane Mode → "Send Finalized Form"
   * Verify data appears in your private server dashboard

---

## Phase 2: Flask Bridge & Portal Setup (3 Hours)

This phase builds the Flask app that will run the sync logic and host the dashboard.

### 1\. Project Setup

```bash
mkdir kobo-bridge
cd kobo-bridge
uv init
```

### 2\. Install Dependencies

```bash
# Add core web, db, and http libraries
uv add flask flask-sqlalchemy psycopg2-binary requests python-dotenv

# Add the background scheduler
uv add apscheduler
```

### 3\. Create `.env` File

Create a `.env` file in your project root.

```ini:.env
# --- Flask ---
SECRET_KEY=your-strong-random-secret-key

# Assumes a local Postgres DB named 'kobo_bridge'
DATABASE_URL=postgresql://user:password@localhost:5432/kobo_bridge

# --- KoboToolbox (Private Server) ---
# The API token you copied from your private server in Phase 1
KOBO_API_TOKEN=your-private-server-api-token-here
# The API host for your PRIVATE server (kpi subdomain)
KOBO_API_HOST=https://your-survey-server.com

# --- CompanyCam ---
# Get these from your CompanyCam developer app settings
COMPANYCAM_CLIENT_ID=your-client-id-here
COMPANYCAM_CLIENT_SECRET=your-client-secret-here
# This must match the redirect URI in your CompanyCam app settings
# Use your actual domain (e.g., https://your-bridge-server.com/companycam/callback)
COMPANYCAM_REDIRECT_URI=https://your-bridge-server.com/companycam/callback
```

### 4\. Create Database Models (`src/kobo_bridge/models.py`)

We need a local DB to cache submissions and, critically, to store the CompanyCam OAuth tokens.

```python
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
```

### 5\. Create Flask App Factory (`src/kobo_bridge/__init__.py`)

```python
import os
from flask import Flask
from .models import db
from .routes import main
from .companycam_auth import cc_auth
from .tasks import scheduler, init_scheduler
from dotenv import load_dotenv

def create_app():
    load_dotenv() # Load .env file

    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Create a default user for token storage
        from .models import User
        if not User.query.first():
            print("Creating default user...")
            default_user = User(username='admin')
            db.session.add(default_user)
            db.session.commit()

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(cc_auth, url_prefix='/companycam')

    # Initialize and start the scheduler
    init_scheduler(app)

    return app
```

---

## Phase 3: CompanyCam OAuth 2.0 Flow (2 Hours)

This is the correct, user-based authentication flow.

### 1\. Create CompanyCam Client (`src/kobo_bridge/companycam_client.py`)

This client *uses* tokens; it doesn't fetch them (the auth flow does that).

```python
import requests
import os
from .models import db, User
from datetime import datetime, timedelta

class CompanyCamClient:
    def __init__(self, user_id='admin'):
        # For this MVP, we hardcode the 'admin' user
        self.user = User.query.filter_by(username=user_id).first()
        self.base_url = 'https://api.companycam.com/v2'
        self.client_id = os.environ.get('COMPANYCAM_CLIENT_ID')
        self.client_secret = os.environ.get('COMPANYCAM_CLIENT_SECRET')

    def _get_headers(self):
        if not self.user or not self.user.companycam_access_token:
            raise Exception("User not authenticated with CompanyCam.")

        # Check if token is expired
        if self.user.companycam_token_expires_at <= datetime.utcnow():
            self.refresh_token()

        return {'Authorization': f'Bearer {self.user.companycam_access_token}'}

    def refresh_token(self):
        print("Refreshing CompanyCam token...")
        url = 'https://app.companycam.com/oauth/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.user.companycam_refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Update user in DB
        self.user.companycam_access_token = token_data['access_token']
        self.user.companycam_refresh_token = token_data['refresh_token']
        expires_in = token_data['expires_in'] - 300 # 5-min buffer
        self.user.companycam_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        db.session.commit()
        print("Token refreshed successfully.")

    def create_project(self, name, address=None):
        url = f"{self.base_url}/projects"
        payload = {'name': name}
        if address:
            payload['address'] = address

        response = requests.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def upload_photo(self, project_id, photo_data, filename, captured_at=None):
        url = f"{self.base_url}/projects/{project_id}/photos"

        # We upload from in-memory data, not a file path
        files = {'photo': (filename, photo_data, 'image/jpeg')}

        # Add metadata if available
        data = {}
        if captured_at:
            data['captured_at'] = captured_at.isoformat()

        response = requests.post(url, files=files, data=data, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
```

### 2\. Create OAuth Routes (`src/kobo_bridge/companycam_auth.py`)

```python
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
```

---

## Phase 4: Automated Sync Service (3 Hours)

This is the core "bridge" logic. It runs in the background.

### 1\. Create KoboToolbox Client (`src/kobo_bridge/kobo_client.py`)

```python
import requests
import os
import json

class KoboClient:
    def __init__(self):
        self.base_url = os.environ.get('KOBO_API_HOST')
        self.token = os.environ.get('KOBO_API_TOKEN')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json'
        })

    def get_forms(self):
        url = f"{self.base_url}/api/v2/assets/"
        params = {'asset_type': 'survey'}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()['results']

    def get_submissions(self, form_uid, last_sync_time=None):
        url = f"{self.base_url}/api/v2/assets/{form_uid}/data/"
        params = {}
        if last_sync_time:
            # Kobo uses ISO format. Add a 1-second buffer.
            query_time = (last_sync_time).isoformat()
            params['query'] = json.dumps({
                "_submission_time": {"$gt": query_time}
            })

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()['results']

    def download_attachment_in_memory(self, attachment_url):
        # We use a separate session for this, as the auth
        # might be different (e.g., cookies)
        response = requests.get(
            attachment_url,
            headers={'Authorization': f'Token {self.token}'}
        )
        response.raise_for_status()
        return response.content # Return raw bytes
```

### 2\. Create Background Task (`src/kobo_bridge/tasks.py`)

This is the heart of the bridge.

```python
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
```

---

## Phase 5: Dashboard UI & Final Testing (2 Hours)

This is the simple web portal to monitor the *results* of the background sync.

### 1\. Create Dashboard Routes (`src/kobo_bridge/routes.py`)

```python
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
```

### 2\. Create Templates (`src/kobo_bridge/templates/...`)

**`base.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Kobo Bridge Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">🛠️ Kobo Bridge</a>
        </div>
    </nav>
    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

**`dashboard.html`**

```html
{% extends "base.html" %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h1>Dashboard</h1>
    {% if not cc_authenticated %}
        <a href="{{ url_for('cc_auth.auth') }}" class="btn btn-primary btn-lg">
            Connect CompanyCam Account
        </a>
    {% else %}
        <span class="badge bg-success p-2">CompanyCam Connected</span>
    {% endif %}
</div>

<div class="row mb-4">
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title">{{ stats.total }}</h3>
                <p class="card-text">Total Submissions</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title text-success">{{ stats.synced }}</h3>
                <p class="card-text">Synced to CC</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title text-warning">{{ stats.pending }}</h3>
                <p class="card-text">Pending</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h3 class="card-title text-danger">{{ stats.failed }}</h3>
                <p class="card-text">Failed</p>
            </div>
        </div>
    </div>
</div>

<p class="text-muted">
    Background sync runs every 5 minutes.
    Last run: {{ last_run.strftime('%Y-%m-%d %H:%M:%S UTC') if last_run else 'Never' }}
</p>

<h3>Recent Submissions</h3>
<table class="table">
    <thead>
        <tr>
            <th>Submitted At</th>
            <th>Kobo ID</th>
            <th>Sync Status</th>
            <th>CC Project ID</th>
            <th>Error</th>
        </tr>
    </thead>
    <tbody>
        {% for sub in submissions %}
        <tr>
            <td>{{ sub.submitted_at.strftime('%Y-%m-%d %H:%M') }}</td>
            <td>{{ sub.kobo_id }}</td>
            <td>
                {% if sub.sync_status == 'Synced' %}
                    <span class="badge bg-success">Synced</span>
                {% elif sub.sync_status == 'Failed' %}
                    <span class="badge bg-danger">Failed</span>
                {% else %}
                    <span class="badge bg-warning">Pending</span>
                {% endif %}
            </td>
            <td>{{ sub.companycam_project_id or 'N/A' }}</td>
            <td class="text-danger"><small>{{ sub.sync_error or '' }}</small></td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

### 3\. Deploy and Test

1. **Deploy the Bridge:**
   ```bash
   # On your server (could be same as KoboToolbox or separate)
   git clone <your-bridge-repo>
   cd kobo-bridge
   uv sync
   ```

2. **Run the App:**
   ```bash
   # For development
   uv run flask --app src.kobo_bridge:create_app --debug run --host=0.0.0.0 --port=5000

   # For production, use a proper WSGI server like gunicorn:
   # uv run gunicorn -w 4 -b 0.0.0.0:5000 src.kobo_bridge:create_app()
   ```

3. **Access the Dashboard:**
   - Open `https://your-bridge-server.com` in your browser
   - Click "Connect CompanyCam Account" and complete the OAuth flow

4. **Test End-to-End:**
   - Submit a new test survey from your KoBoCollect app (connected to your private server)
   - Wait for the background job to run (runs every 5 minutes)
   - Watch the bridge dashboard - submission should appear and sync status should change from "Pending" → "Synced"
   - Check your CompanyCam account to verify the new project and photos were created
