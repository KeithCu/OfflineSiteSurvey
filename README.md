# Site Survey App Project

This project contains a comprehensive offline-first site survey application with advanced features.

## Overview

- **Backend:** Flask REST API with configuration management and survey templates
- **Frontend:** BeeWare cross-platform app (iOS, Android, Desktop) with offline functionality
- **Database:** PostgreSQL/SQLite backend, local SQLite frontend for offline-first operation
- **Cross-Platform:** Native apps for iOS, Android, Windows, macOS, and Linux
- **Features:** Automatic image compression, configurable settings, template-based surveys, robust CRDT-based sync, complete MVP survey workflow, photo gallery with categories and search, project hierarchy management

## Key Features

✅ **Offline-First Architecture** - Works without internet connectivity, syncs when available
✅ **Automatic Image Compression** - Reduces photo sizes to 75% quality to save storage
✅ **Configurable Settings** - Server-managed configuration for image quality, sync intervals, etc.
✅ **Survey Templates** - Create and manage reusable survey templates for different property types
✅ **Complete Survey Workflow** - Full MVP with all question types (text, yes/no, multiple choice, photo) and immediate response saving
✅ **Enhanced Survey UI** - Progress tracking, field type validation, and intuitive navigation
✅ **GPS Photo Tagging** - Automatic location capture for survey photos
✅ **Photo Gallery & Management** - Grid view thumbnails, categories (interior/exterior/issues/progress), search, and metadata storage
✅ **Project Hierarchy** - Organize work with Projects → Sites → Surveys → Photos structure
✅ **Cross-Platform** - Native apps for iOS, Android, Windows, macOS, and Linux
✅ **CRDT-Based Sync** - Robust multi-client synchronization with automatic conflict resolution

## File Structure

- `pyproject.toml` (Project configuration)
- `README.md` (Main project documentation)
- `ROADMAP.md` (Development roadmap and priorities)
- `backend/app.py` (Flask REST API backend with template support)
- `backend/store_survey_template.py` (Survey template definitions)
- `src/survey_app/app.py` (BeeWare cross-platform frontend with enhanced UI, photo gallery, and project management)
- `src/survey_app/local_db.py` (Local SQLite database with CRDT sync, photo metadata, and project hierarchy)
- `archive/` (Archived KoboToolbox and analysis files)

## Status: MVP Complete + Phase 2 Complete ✅

The core MVP survey workflow is fully functional with all question types working properly. Phase 2 enhancements are complete including conditional logic, photo requirements, enhanced survey UI, and comprehensive photo management.

### Core MVP Features Implemented

#### Complete Survey Workflow
- ✅ Create surveys from templates
- ✅ Answer all question types (text, yes/no, multiple choice, photo)
- ✅ Immediate response saving (prevents data loss)
- ✅ Survey completion and data persistence
- ✅ Template field ordering and validation

#### Photo Management
- ✅ Automatic image compression (75% JPEG quality)
- ✅ GPS location tagging for photos
- ✅ Photo storage with metadata
- ✅ Photo capture in survey workflow

### Configuration Management
- Server-side configuration for app settings
- Client apps fetch settings on startup
- Configurable parameters:
  - `image_compression_quality`: JPEG quality (1-100)
  - `auto_sync_interval`: Auto-sync frequency in seconds
  - `max_offline_days`: Maximum offline data retention

### Survey Templates
- Default comprehensive store survey template included
- Covers electrical, structural, safety, and maintenance inspections
- Template system for creating custom survey types
- Organized by sections (General, Electrical, Structural, Safety, etc.)
- **Conditional Logic**: Fields show/hide based on previous answers (e.g., electrical safety notes only if exposed wires = Yes)
- **Photo Requirements**: Built-in photo requirement definitions with descriptions and validation

### Enhanced Survey UI
- Progress indicators showing current question and completion status
- Field type validation with appropriate input controls (text, yes/no, dropdown, photo)
- Dynamic UI that adapts to different question types
- Template-based survey creation and execution
- **Conditional Logic**: Fields show/hide dynamically based on previous answers
- **Photo Requirements**: Visual checklists for required photos per survey section

### Enhanced UI
- Settings panel for configuration management
- Templates browser for creating surveys from templates
- Improved offline handling and sync status

### Photo Management & Gallery
- Thumbnail grid view with 4-column layout
- Photo categories: General, Interior, Exterior, Issues, Progress
- Search functionality by description text
- EXIF metadata storage and extraction
- Photo quality assessment framework
- Bulk operations support
- **Photo Requirements Tracking**: Visual checklists showing required vs. taken photos
- **Fulfillment Status**: Track which photos fulfill specific survey requirements

### Project Hierarchy
- Projects → Sites → Surveys → Photos organization
- Project management UI for creating and selecting projects
- Sites nested under projects
- Hierarchical navigation and data structure

## CRDT-Based Synchronization

This project uses CRDT (Conflict-Free Replicated Data Types) with `cr-sqlite` for robust offline-first synchronization between multiple clients and a central server.

### Hub-and-Spoke Architecture

The system implements a "hub-and-spoke" model using `cr-sqlite` for seamless multi-client synchronization:

#### Synchronization Flow

**1. Offline Data Collection:**
- **Client A (Offline)**: Takes photos, answers survey questions
- **Client A (Online)**: Pushes changeset (deltas since version 5) to server
- **Server**: Merges changeset into central `cr-sqlite` database (version becomes 10)
- **Client B (Online)**: Polls server for changes since its last sync (version 7)
- **Server**: Returns deltas from version 7 to 10 (including Client A's work)

This enables true multi-master, hub-and-spoke replication where the server acts as a CRDT-speaking source of truth.

**2. Server Implementation:**
The server logic is simplified using the `vlcn.io` REST example pattern:
- Load `cr-sqlite` extension
- Execute `INSERT INTO crsql_changes...` with received changesets
- The extension handles merging, conflict resolution, and version updates automatically

**3. Analytics Database (Optional/Low Priority):**
PostgreSQL can serve as a read-only analytics and reporting database, populated via background ETL when needed:
- Clients sync directly with `cr-sqlite` hub
- Internal Python service can periodically transform `cr-sqlite` changes to PostgreSQL (not high priority)
- Analytics remain available even if ETL script fails

### Implementation Components

1. **Central Server**: Simple Python server (FastAPI/Flask) using `vlcn.io` logic to handle changeset GET/POST operations with central `cr-sqlite` database
2. **Client Apps**: BeeWare apps with local `cr-sqlite` databases that sync changesets when online
3. **ETL Service (Optional)**: Background script that syncs central `cr-sqlite` to PostgreSQL for analytics (low priority)

### Benefits

- **True Offline-First**: Works without internet connectivity
- **Automatic Conflict Resolution**: CRDT handles concurrent changes gracefully
- **Simple Code**: Minimal custom sync logic required
- **Scalable**: Easy to add more clients without architectural changes
- **Reliable**: Sync failures don't block other operations

## Prerequisites

- **Python**: 3.11+ with uv
- **Database**: PostgreSQL (recommended) or SQLite
- **Mobile Development**: Android SDK (for Android), Xcode (for iOS, macOS only)
- **GUI Framework**: GTK+ development libraries (for Linux desktop development)

## API Endpoints

### Configuration
- `GET /api/config` - Get all configuration
- `GET /api/config/<key>` - Get specific config value
- `PUT /api/config/<key>` - Update configuration

### Templates
- `GET /api/templates` - List all templates
- `GET /api/templates/<id>` - Get template details
- `POST /api/templates` - Create new template
- `PUT /api/templates/<id>` - Update template
- `DELETE /api/templates/<id>` - Delete template

## Development

```bash
# Install dependencies
uv sync

# Download and set up cr-sqlite
./setup_crsqlite.sh

# Initialize the database
uv run flask init-db

# Run backend development server
uv run flask --app backend.app run --debug

# Run frontend development (Linux)
uv run briefcase dev

# Build for other platforms
uv run briefcase build android  # Android APK
uv run briefcase build iOS      # iOS app (macOS only)
uv run briefcase build windows  # Windows app
```

## Production Deployment

### Backend Setup
```bash
# Create and activate environment
uv venv --python 3.11
source .venv/bin/activate

# Install dependencies
uv pip install -e .
uv pip install gunicorn  # Production WSGI server

# Set environment variables
export FLASK_APP=backend/app.py
export FLASK_ENV=production
export DATABASE_URL=postgresql://survey_user:password@localhost/site_survey  # If using PostgreSQL

# Initialize database
flask db upgrade  # If using Flask-Migrate
# Or: python -c "from backend.app import db; db.create_all()"
```

### Systemd Service
Create `/etc/systemd/system/site-survey.service`:
```ini
[Unit]
Description=Site Survey Flask App
After=network.target

[Service]
User=keithcu
WorkingDirectory=/home/keithcu/Desktop/Python/OfflineSiteSurvey
Environment="PATH=/home/keithcu/Desktop/Python/OfflineSiteSurvey/.venv/bin"
Environment="FLASK_APP=backend/app.py"
Environment="FLASK_ENV=production"
ExecStart=/home/keithcu/Desktop/Python/OfflineSiteSurvey/.venv/bin/gunicorn --bind 0.0.0.0:8000 backend.app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl enable site-survey
sudo systemctl start site-survey
sudo systemctl status site-survey
```

### Apache Reverse Proxy (Alternative)

Create `/etc/httpd/conf/extra/site-survey.conf`:
```apache
<VirtualHost *:80>
    ServerName your-domain.com

    # Enable WSGI
    WSGIDaemonProcess site-survey user=keithcu group=keithcu threads=5
    WSGIScriptAlias / /home/keithcu/Desktop/Python/OfflineSiteSurvey/backend/app.wsgi

    <Directory /home/keithcu/Desktop/Python/OfflineSiteSurvey>
        WSGIProcessGroup site-survey
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>

    # Static files (if needed)
    Alias /static /home/keithcu/Desktop/Python/OfflineSiteSurvey/static
    <Directory /home/keithcu/Desktop/Python/OfflineSiteSurvey/static>
        Require all granted
    </Directory>

    ErrorLog /var/log/httpd/site-survey_error.log
    CustomLog /var/log/httpd/site-survey_access.log combined
</VirtualHost>
```

Create the WSGI file `/home/keithcu/Desktop/Python/OfflineSiteSurvey/backend/app.wsgi`:
```python
import sys
import os

# Add your project directory to the path
sys.path.insert(0, '/home/keithcu/Desktop/Python/OfflineSiteSurvey')

# Set environment variables
os.environ['FLASK_APP'] = 'backend/app.py'
os.environ['FLASK_ENV'] = 'production'

# Import and create the app
from backend.app import app

application = app
```

Enable the site:
```bash
echo "Include conf/extra/site-survey.conf" | sudo tee -a /etc/httpd/conf/httpd.conf
sudo apachectl configtest
```

### SSL with Let's Encrypt (Optional)
```bash
sudo certbot --apache -d your-domain.com
```

### Frontend (BeeWare)

#### Development
```bash
# Quick development testing
uv run briefcase dev

# Full packaged desktop app
uv run briefcase run linux  # or macOS/windows
```

#### Android Deployment
```bash
# Create and build Android app
uv run briefcase create android
uv run briefcase build android

# Run on connected device/emulator
uv run briefcase run android

# Package for Play Store distribution
uv run briefcase package android
```

#### iOS Deployment (macOS only)
```bash
# Create iOS app
uv run briefcase create iOS

# Open in Xcode for testing
uv run briefcase open iOS

# Run in simulator
uv run briefcase run iOS

# Package for App Store
uv run briefcase package iOS
```

## License

See individual component licenses (BeeWare is BSD licensed, cr-sqlite has its own license).
