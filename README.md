# Site Survey App Project

This project contains a comprehensive offline-first site survey application with advanced features.

## Features

✅ **Offline-First Architecture** - Complete survey workflow works without internet, syncs automatically when available

✅ **Cross-Platform Apps** - Native BeeWare applications for iOS, Android, Windows, macOS, and Linux

✅ **Flask REST API Backend** - Robust server with configuration management and survey templates

✅ **Dual Database System** - PostgreSQL/SQLite backend with local SQLite frontend for offline operation

✅ **Cloud Photo Storage** - Photos stored in cloud storage (S3, GCS, Azure) using Apache Libcloud with integrity verification

✅ **Automatic Image Compression** - Photos reduced to 75% quality to optimize storage while maintaining usability

✅ **GPS Photo Tagging** - Automatic location capture and metadata storage for all survey photos

✅ **Photo Gallery & Management** - Grid view thumbnails, categorized storage (interior/exterior/issues/progress), and search functionality

✅ **Survey Templates** - Create and manage reusable templates for different property types and inspection requirements

✅ **Complete Survey Workflow** - Full MVP with all question types (text, yes/no, multiple choice, photo) and immediate data saving

✅ **Enhanced Survey UI** - Progress tracking, field validation, conditional logic, and intuitive navigation

✅ **Project Hierarchy Management** - Organize work with Projects → Sites → Surveys → Photos structure

✅ **Configurable Settings** - Server-managed configuration for image quality, sync intervals, and app behavior

✅ **CRDT-Based Synchronization** - Robust multi-client sync with automatic conflict resolution using cr-sqlite

## File Structure

- `pyproject.toml` (Project configuration)
- `README.md` (Main project documentation)
- `ROADMAP.md` (Development roadmap and priorities)
- `backend/app.py` (Flask REST API backend with template support)
- `backend/services/` (Cloud storage services and upload queue)
- `backend/store_survey_template.py` (Survey template definitions)
- `src/survey_app/app.py` (BeeWare cross-platform frontend with enhanced UI, photo gallery, and project management)
- `src/survey_app/local_db.py` (Local SQLite database with CRDT sync, photo metadata, and project hierarchy)
- `archive/` (Archived KoboToolbox and analysis files)

## Status: MVP Complete + Phase 2 Complete + Phase 3 Project & Site Management Complete + Phase 4 Performance & Reliability Complete ✅

The core MVP survey workflow is fully functional with all question types working properly. Phase 2 enhancements are complete including conditional logic, photo requirements, enhanced survey UI, and comprehensive photo management. Phase 3 adds comprehensive project and site management with status tracking, metadata, templates, and enhanced site features. Phase 4 adds enterprise-grade performance optimizations and reliability features for production deployment.

## Reliability & Data Integrity

### Photo Integrity Verification
- **Cryptographic Hashing**: All photos are protected with SHA-256 hashes computed at capture time
- **Integrity Endpoints**: REST API endpoints for verifying photo integrity (`/api/photos/<id>/integrity`)
- **Sync Verification**: Photo data is validated during CRDT synchronization to prevent corruption
- **CLI Tools**: Command-line utilities for bulk integrity checking and repair

### Advanced Sync Reliability
- **Configurable Sync Intervals**: Background sync adapts to network conditions (default: 5 minutes)
- **Exponential Backoff**: Failed sync attempts use intelligent retry with jitter to prevent battery drain
- **Sync Health Indicators**: Real-time status display with visual indicators (🟢🟡🔴) and failure counts
- **Offline Queue**: Operations are queued when offline and processed when connectivity returns

### Auto-Save Protection
- **Debounced Auto-Save**: In-progress survey answers are automatically saved every 2 seconds of inactivity
- **Draft Management**: Temporary drafts prevent data loss during app crashes or battery issues
- **Smart Throttling**: Auto-save only triggers after 30+ seconds of continuous typing to avoid excessive database writes

### Backup & Disaster Recovery
- **Automated Backups**: Database and media files are automatically backed up with configurable retention
- **Point-in-Time Recovery**: Restore from any timestamped backup with integrity validation
- **Stale Backup Protection**: System refuses backups older than 30 days for security
- **Cross-Platform CLI**: Backup and restore operations work on all supported platforms

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
- ✅ Cloud storage with Apache Libcloud (S3, GCS, Azure, MinIO)
- ✅ Upload queue with background processing and verification
- ✅ Photo integrity verification via cryptographic hashing
- ✅ Local caching for offline viewing
- ✅ Photo storage with metadata
- ✅ Photo capture in survey workflow

### Configuration Management
- Server-side configuration for app settings
- Client apps fetch settings on startup
- Configurable parameters:
  - `image_compression_quality`: JPEG quality (1-100)
  - `auto_sync_interval`: Auto-sync frequency in seconds
  - `max_offline_days`: Maximum offline data retention

### Cloud Storage Configuration
- Environment variables for cloud storage (Apache Libcloud):
  - `CLOUD_STORAGE_PROVIDER`: Storage provider (s3, gcs, azure)
  - `CLOUD_STORAGE_ACCESS_KEY`: Provider access key
  - `CLOUD_STORAGE_SECRET_KEY`: Provider secret key
  - `CLOUD_STORAGE_BUCKET`: Bucket/container name
  - `CLOUD_STORAGE_REGION`: Region for S3/GCS
  - `CLOUD_STORAGE_LOCAL_PATH`: Local directory for pending uploads

### Survey Templates
- Default comprehensive store survey template included
- Covers electrical, structural, safety, and maintenance inspections
- Template system for creating custom survey types
- Organized by sections (General, Electrical, Structural, Safety, etc.)

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
- **Section-Scoped Tags**: Assign tags defined per survey section and surface only relevant tags during capture
- **Template Tag Editor**: Define per-section tag sets inside the template editor for consistent tagging

### Project Hierarchy & Management
- Projects → Sites → Surveys → Photos organization
- Project management UI for creating and selecting projects
- Sites nested under projects with notes and GPS coordinates
- Hierarchical navigation and data structure
- **Project Status Tracking**: Draft, In Progress, Completed, Archived states
- **Project Metadata**: Client information, due dates, priority levels
- **Project Templates**: Standardized project structures for different industries

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

## Cloud Storage Architecture

The application uses Apache Libcloud for scalable, cloud-based photo storage with offline-first operation.

### Local-First Upload Flow
1. **Photo Capture**: Photo stored locally in pending directory
2. **Database Record**: Created with `upload_status='pending'` (no cloud URLs yet)
3. **Background Upload**: Queue service uploads to cloud when online
4. **Verification**: Downloads uploaded photo and verifies hash matches original
5. **Database Update**: Only after verification passes → updates with cloud URLs and `upload_status='completed'`

### Supported Providers
- **Amazon S3** (recommended, most tested)
- **Google Cloud Storage**
- **Azure Blob Storage**
- **MinIO** (S3-compatible)

### Key Features
- **Integrity Verification**: Cryptographic hash verification after upload
- **Offline Caching**: Local caching of downloaded photos for offline viewing
- **Upload Queue**: Background processing with retry logic and exponential backoff
- **Provider Agnostic**: Single API supports multiple cloud providers

## Prerequisites

- **Python**: 3.11+ with uv
- **Database**: PostgreSQL (recommended) or SQLite
- **Cloud Storage**: Apache Libcloud for cloud photo storage (S3, GCS, Azure, MinIO)
- **Mobile Development**: Android SDK (for Android), Xcode (for iOS, macOS only)
- **GUI Framework**: GTK+ development libraries (for Linux desktop development)

## API Endpoints

### Configuration
- `GET /api/config` - Get all configuration
- `GET /api/config/<key>` - Get specific config value
- `PUT /api/config/<key>` - Update configuration
- `GET /api/config/cloud-storage` - Get cloud storage configuration (masked)
- `POST /api/config/cloud-storage/test` - Test cloud storage connection
- `GET /api/config/cloud-storage/status` - Get upload queue status

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

## Testing

The application includes comprehensive test suites for both backend and frontend components.

### Backend Testing

```bash
# Install test dependencies (included in pyproject.toml)
uv sync

# Run all backend tests
uv run pytest tests/test_backend/ -v

# Run with coverage report
uv run pytest tests/test_backend/ --cov=backend --cov-report=html

# Run specific test categories
uv run pytest tests/test_backend/test_models.py       # Database models
uv run pytest tests/test_backend/test_api.py         # API endpoints
uv run pytest tests/test_backend/test_utils.py       # Utility functions
uv run pytest tests/test_backend/test_crdt_sync.py   # CRDT sync logic
uv run pytest tests/test_backend/test_cloud_storage.py  # Cloud storage
```

### Frontend Testing

```bash
# Run all frontend tests
uv run pytest tests/test_frontend/ -v

# Run with coverage
uv run pytest tests/test_frontend/ --cov=src/survey_app --cov-report=html

# Run specific test categories
uv run pytest tests/test_frontend/test_local_db.py  # Database operations
uv run pytest tests/test_frontend/test_handlers.py  # UI handlers
```

### Test Structure

```
tests/
├── conftest.py              # Shared test fixtures and configuration
├── test_backend/            # Backend component tests
│   ├── test_models.py       # Database model tests
│   ├── test_api.py          # API endpoint tests
│   ├── test_utils.py        # Shared utility tests
│   └── test_crdt_sync.py    # CRDT synchronization tests
└── test_frontend/           # Frontend component tests
    ├── test_local_db.py     # Local database tests
    └── test_handlers.py     # UI handler tests
```

## Logging

The application uses structured logging for debugging and monitoring.

### Backend Logging

Backend logs are written to `logs/backend.log` with rotation (10MB, 5 backups). Logs include:
- Database operations
- API requests and responses
- CRDT sync operations
- Photo integrity checks

```bash
# View recent backend logs
tail -f logs/backend.log

# Search for specific events
grep "ERROR" logs/backend.log
grep "sync" logs/backend.log
```

### Frontend Logging

Frontend logs are written to console only (suitable for Toga applications). Logs include:
- UI interactions
- Database operations
- Sync operations
- Auto-save events

### Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General operational messages
- `WARNING`: Warning conditions that don't prevent operation
- `ERROR`: Error conditions that may affect functionality

## Local Development


### Development Workflow

1. **Backend Changes**: Modify files in `backend/`, restart Flask server
2. **Frontend Changes**: Modify files in `src/survey_app/`, Toga will hot-reload
3. **Database Changes**: Run `uv run flask init-db` to apply schema updates
4. **Testing**: Run `uv run pytest` to verify changes don't break functionality

### Database Management

```bash
# Reset database (WARNING: destroys all data)
rm instance/backend_main.db
uv run flask init-db

# Check photo integrity
uv run flask check-photo-integrity

# Create backup
python backup_restore.py backup

# Restore from backup
python backup_restore.py restore --backup-file backups/backup_*.zip
```

### Debugging

```bash
# Enable debug logging
export FLASK_ENV=development
uv run flask --app backend.app run --debug

# View logs in real-time
tail -f logs/backend.log

# Run tests with verbose output
uv run pytest -v -s
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

## Backup & Restore Operations

### Creating Backups
```bash
# Create a backup of database and media files
python backup_restore.py backup

# Create backup in specific directory
python backup_restore.py backup --backup-dir /path/to/backups

# Backup database only (no media files)
python backup_restore.py backup --no-media
```

### Restoring from Backup
```bash
# Restore from a specific backup file with integrity validation
python backup_restore.py restore --backup-file backups/backup_20241116_143022.zip

# Restore without hash validation (faster but less safe)
python backup_restore.py restore --backup-file backups/backup_20241116_143022.zip --no-validate
```

### Managing Backup Retention
```bash
# Clean up old backups, keeping only the 5 most recent
python backup_restore.py cleanup --max-backups 5

# Clean up backups in specific directory
python backup_restore.py cleanup --backup-dir /path/to/backups --max-backups 10
```

### Photo Integrity Checking
```bash
# Check integrity of all photos in the backend database
uv run flask check-photo-integrity

# Check and automatically fix integrity issues
uv run flask check-photo-integrity --fix
```

### Disaster Recovery Workflow
1. **Stop the application** if it's currently running
2. **Identify the backup** you want to restore from
3. **Run integrity check** on the backup if possible
4. **Perform the restore** operation
5. **Restart the application** and verify data integrity
6. **Check sync status** to ensure proper reconnection

**Example emergency restore:**
```bash
# Stop the app
pkill -f "flask run"

# Restore from latest backup
python backup_restore.py restore --backup-file $(ls -t backups/backup_*.zip | head -1)

# Verify integrity
uv run flask check-photo-integrity

# Restart the app
uv run flask run
```

## License

This project is licensed under the GNU Lesser General Public License v3.0 (LGPL v3). See the LICENSE file for full licensing terms and conditions.

Individual components have their own licenses:
- BeeWare framework: BSD licensed
- cr-sqlite: MIT licensed
- Other dependencies: See their respective licenses
