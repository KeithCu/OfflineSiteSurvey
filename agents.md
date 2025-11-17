# Site Survey App - Agent Guide

## Overview
Offline-first site survey application with cross-platform BeeWare frontend and Flask REST API backend. Uses CRDT-based synchronization with cr-sqlite for robust offline operation.

## Data Model & Schema

### Hierarchy Structure
The application uses a hierarchical data model:
- **Projects** → **Sites** → **Surveys** → **Photos/Responses**

### Model Relationships
- Project (1) → (many) Sites
- Site (1) → (many) Surveys
- Survey (1) → (many) SurveyResponses & Photos
- Photo (many) → (1) Survey & Site (for organization)

### ID Type Conventions
- **Integer IDs**: Projects, Sites, Surveys, SurveyResponses, SurveyTemplates, TemplateFields (auto-incrementing)
- **String IDs**: Photos (UUID-like strings for global uniqueness)
- **All IDs**: Start from 1, never 0

### Important Enums
```python
# Survey Status
SurveyStatus: ['draft', 'active', 'completed', 'archived']

# Project Status
ProjectStatus: ['draft', 'in_progress', 'completed', 'archived']

# Photo Categories
PhotoCategory: ['general', 'interior', 'exterior', 'issues', 'progress']

# Priority Levels
PriorityLevel: ['low', 'medium', 'high']
```

### Timestamp Conventions
- All timestamps are UTC timezone-aware (`datetime` with `timezone.utc`)
- Fields: `created_at`, `updated_at`
- Server default: `'1970-01-01 00:00:00'` (Unix epoch)

### Field Length Limits
- Project name: 200 characters
- Site name: 200 characters
- Survey title: 200 characters
- Template name: 200 characters
- Addresses/notes: 500-1000 characters
- Photo descriptions: Unlimited (Text field)

### Coordinate Validation
- Latitude: -90.0 to 90.0
- Longitude: -180.0 to 180.0
- Stored as Float with 6-8 decimal precision

## Prerequisites
- Python 3.11+
- uv package manager
- PostgreSQL (recommended) or SQLite for backend database
- Android SDK (for Android development)
- Xcode (for iOS/macOS development, macOS only)
- GTK+ development libraries (for Linux desktop development)

## Development Setup
```bash
# Activate virtual environment (DO THIS FIRST FOR ALL COMMANDS)
source .venv/bin/activate

# Install/update dependencies
uv sync

# Download and set up cr-sqlite
./setup_crsqlite.sh

# Initialize the database
uv run flask init-db
```

## Development Workflow
```bash
# Backend development server
uv run flask --app backend.app run --debug

# Frontend development (Linux)
uv run briefcase dev

# Full packaged desktop app
uv run briefcase run linux
```

## Key Directories & Files
- `backend/` - Flask REST API with blueprints and models
- `src/survey_app/` - BeeWare cross-platform frontend
- `tests/` - Test suites for both backend and frontend
- `shared/` - Shared utilities and models
- `migrations/` - Database migrations
- `pyproject.toml` - Project configuration
- `logs/backend.log` - Backend logs
- `backups/` - Database and media backups

## Database Management
```bash
# Initialize/reset database (WARNING: destroys all data)
rm instance/backend_main.db
uv run flask init-db

# Check photo integrity
uv run flask check-photo-integrity

# Check and fix photo integrity issues
uv run flask check-photo-integrity --fix
```

## Testing

### Test Structure
Tests are organized into backend and frontend suites:
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

### Test Fixtures
Shared fixtures in `conftest.py`:
- **app**: Flask test application with test database
- **client**: Flask test client for API testing
- **db**: Test database session
- **sample_data**: Pre-populated test data (projects, sites, surveys)

### Test Database Setup
- Tests use SQLite in-memory database (`:memory:`)
- Separate test database prevents interference with development data
- Automatic cleanup between tests
- CRDT extensions loaded for sync tests

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=backend --cov=src/survey_app --cov-report=html

# Backend tests only
uv run pytest tests/test_backend/ -v

# Frontend tests only
uv run pytest tests/test_frontend/ -v

# Specific test files
uv run pytest tests/test_backend/test_models.py
uv run pytest tests/test_backend/test_api.py
uv run pytest tests/test_backend/test_utils.py
uv run pytest tests/test_backend/test_crdt_sync.py
uv run pytest tests/test_frontend/test_local_db.py
uv run pytest tests/test_frontend/test_handlers.py

# Run tests with verbose output and stop on first failure
uv run pytest -v -s --tb=short

# Run specific test function
uv run pytest tests/test_backend/test_models.py::test_project_model_creation -v
```

### Test Categories
- **Unit Tests**: Individual function/component testing
- **Integration Tests**: API endpoint testing with database
- **CRDT Tests**: Synchronization logic and conflict resolution
- **Validation Tests**: Input validation and error handling
- **Database Tests**: Model relationships and constraints

## Backup & Restore Operations
```bash
# Create backup of database and media files
python backup_restore.py backup

# Create backup in specific directory
python backup_restore.py backup --backup-dir /path/to/backups

# Backup database only (no media files)
python backup_restore.py backup --no-media

# Restore from backup file with integrity validation
python backup_restore.py restore --backup-file backups/backup_20241116_143022.zip

# Restore without hash validation (faster but less safe)
python backup_restore.py restore --backup-file backups/backup_20241116_143022.zip --no-validate

# Clean up old backups, keeping only the 5 most recent
python backup_restore.py cleanup --max-backups 5
```

## Configuration Management
- Server-side configuration for app settings
- Client apps fetch settings on startup

Configurable parameters:
- `image_compression_quality`: JPEG quality (1-100, default 75)
- `auto_sync_interval`: Auto-sync frequency in seconds (default 300)
- `max_offline_days`: Maximum offline data retention (default 30)

### Cloud Storage Configuration
Environment variables for cloud storage (Apache Libcloud):
- `CLOUD_STORAGE_PROVIDER`: Storage provider (s3, gcs, azure)
- `CLOUD_STORAGE_ACCESS_KEY`: Provider access key
- `CLOUD_STORAGE_SECRET_KEY`: Provider secret key
- `CLOUD_STORAGE_BUCKET`: Bucket/container name
- `CLOUD_STORAGE_REGION`: Region for S3/GCS
- `CLOUD_STORAGE_LOCAL_PATH`: Local directory for pending uploads

API endpoints:
- `GET /api/config` - Get all configuration
- `GET /api/config/<key>` - Get specific config value
- `PUT /api/config/<key>` - Update configuration
- `GET /api/config/cloud-storage` - Get cloud storage configuration (masked)
- `POST /api/config/cloud-storage/test` - Test cloud storage connection
- `GET /api/config/cloud-storage/status` - Get upload queue status

## CRDT Synchronization
Uses cr-sqlite for conflict-free replicated data types. Hub-and-spoke architecture:
- Server acts as central CRDT hub
- Clients sync changesets when online
- Automatic conflict resolution
- True offline-first operation

### Change Object Format
CRDT changes must include these required fields:
```json
{
  "table": "projects|sites|survey|survey_response|survey_template|template_field|photo",
  "pk": "{\"id\": 123}",  // JSON string with primary key
  "cid": "column_name",   // Column that changed
  "val": "new_value",     // New value (can be any type)
  "col_version": 1,       // Column version number
  "db_version": 5,        // Database version when change occurred
  "site_id": "uuid-string" // Unique identifier for the client instance
}
```

### Site ID Generation
- Each client app instance gets a unique `site_id` (UUID4)
- Used to track which client originated changes
- Prevents syncing back changes to the originating client
- Stored in `LocalDatabase.site_id` for frontend, passed in API calls for backend

### CRR-Enabled Tables
All main tables are Conflict-free Replicated Relations (CRR) except `app_config`:
- `projects` ✓ CRR
- `sites` ✓ CRR
- `survey` ✓ CRR
- `survey_response` ✓ CRR
- `survey_template` ✓ CRR
- `template_field` ✓ CRR
- `photo` ✓ CRR
- `app_config` ❌ Not CRR (server-only configuration)

### Photo Integrity Verification
During sync, photos are validated by:
1. Extracting photo ID from change `pk` field
2. Checking if existing photo record has a hash
3. Computing hash of incoming image data
4. Rejecting changes where hashes don't match
5. Logging integrity issues without blocking sync

### Sync Flow
1. **Client → Server**: `POST /api/changes` with local changes
2. **Server Processing**: Validates changes, applies to central DB
3. **Client → Server**: `GET /api/changes?version=X&site_id=Y` for remote changes
4. **Server Response**: Returns changes from other clients since last sync
5. **Client Processing**: Applies remote changes to local DB

### Foreign Key Handling
- Foreign keys are **disabled** during CRR table creation (`PRAGMA foreign_keys = OFF`)
- Referential integrity maintained at application level
- Required for CRDT merge operations to work properly

### Cloud Storage Integration
- **Local-First Architecture**: Photos stored locally first, uploaded to cloud when online
- **Upload Queue**: Background service processes pending uploads with retry logic
- **Verification**: Uploaded photos are downloaded and hash-verified before database update
- **CRDT Sync**: Syncs cloud URLs instead of binary data, downloads on demand
- **Caching**: Local caching of downloaded photos for offline viewing

#### Upload Flow
1. Photo captured → stored locally in pending directory
2. Database record created with `upload_status='pending'`
3. Background queue uploads to cloud storage
4. **CRITICAL**: Downloads uploaded photo and verifies hash matches original
5. Only after verification passes → updates database with cloud URLs and `upload_status='completed'`
6. Local file cleaned up (optional, can keep as additional cache)

#### Supported Cloud Providers
- **Amazon S3** (recommended, most tested)
- **Google Cloud Storage**
- **Azure Blob Storage**
- **MinIO** (S3-compatible)

## Validation & Constraints

### Input Validation Patterns
The app uses comprehensive validation from `shared/validation.py`:

#### String Validation
- **Required Fields**: No empty strings or whitespace-only values
- **Length Limits**: Enforced per field type (see Field Length Limits above)
- **HTML Sanitization**: Removes dangerous tags, scripts, and event handlers
- **Trimming**: Automatic whitespace removal from string inputs

#### Numeric Validation
- **Coordinates**: Latitude (-90 to 90), Longitude (-180 to 180)
- **Compression Quality**: 1-100 range for JPEG quality
- **Auto-sync Interval**: Non-negative integers (seconds)
- **Photo Sizes**: Valid file sizes in bytes

#### Choice Validation
- **Enums**: Strict validation against allowed values
- **Status Fields**: Must match predefined enum values
- **Priority Levels**: low/medium/high only

### Database Constraints
Applied during `flask init-db`:

#### Photo Hash Validation
```sql
ALTER TABLE photo ADD CONSTRAINT chk_photo_hash_length
CHECK (length(hash_value) = 64);
```
- SHA-256 hashes must be exactly 64 characters

#### Image Compression Quality
```sql
ALTER TABLE app_config ADD CONSTRAINT chk_compression_quality_range
CHECK (key != 'image_compression_quality' OR (CAST(value AS INTEGER) >= 1 AND CAST(value AS INTEGER) <= 100));
```
- JPEG quality must be 1-100

#### Performance Indexes
- `idx_photos_*`: Photo table indexes for survey_id, site_id, created_at, category
- `idx_responses_*`: Response table indexes for survey_id, question_id
- `idx_*_*`: Hierarchy indexes for site←→project, survey←→site relationships

### Validation Error Handling
- **ValidationError Exception**: Raised for all validation failures
- **Field-Specific Messages**: Clear error messages indicating which field failed
- **Type Validation**: Strict type checking (strings, numbers, etc.)
- **Sanitization**: HTML/script injection prevention

### Coordinate Precision
- GPS coordinates stored as FLOAT with 6-8 decimal places
- Input validation accepts various formats (decimal degrees, DMS)
- Automatic conversion to decimal degrees for storage

## Architecture Patterns

### Flask App Factory Pattern
The backend uses the application factory pattern:
```python
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # ... configuration and setup ...
    return app
```
- **Instance-relative config**: Configuration stored in `instance/` directory
- **Test config injection**: Allows test-specific configuration overrides
- **Blueprint registration**: Modular route organization

### Blueprint Organization
API routes organized into focused blueprints in `backend/blueprints/`:
- `config.py` - Configuration management endpoints
- `crdt.py` - CRDT synchronization endpoints
- `photos.py` - Photo upload/download and management
- `projects.py` - Project CRUD operations
- `sites.py` - Site CRUD operations
- `surveys.py` - Survey CRUD operations
- `templates.py` - Survey template management

### Shared Models Pattern
Models defined in `shared/models.py` for cross-platform compatibility:
- Used by both backend (Flask-SQLAlchemy) and frontend (local SQLite)
- Consistent field definitions and relationships
- Enum definitions shared between components
- Validation logic can reference shared types

### Local Database Initialization
Frontend uses custom database setup in `src/survey_app/local_db.py`:
```python
class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        self.site_id = str(uuid.uuid4())  # Unique client ID
        # ... cr-sqlite extension loading ...
        # ... CRR table setup ...
```
- **cr-sqlite extension**: Loaded dynamically from user data directory
- **Site ID generation**: Each app instance gets unique UUID
- **CRR table creation**: All tables made conflict-free replicated
- **Foreign keys disabled**: Required for CRDT operations

### Session Management Patterns
- **Backend**: SQLAlchemy sessions with proper commit/rollback handling
- **Frontend**: Local SQLite sessions with transaction management
- **Error handling**: Automatic rollback on exceptions
- **Connection pooling**: Efficient database connection reuse

### Extension Loading
cr-sqlite extension loaded with fallback paths:
```python
lib_path = os.path.join(user_data_dir("crsqlite", "vlcn.io"), 'crsqlite.so')
if not os.path.exists(lib_path):
    lib_path = os.path.join(os.path.dirname(__file__), 'lib', 'crsqlite.so')
db_conn.enable_load_extension(True)
db_conn.load_extension(lib_path)
```

## Important Conventions & Gotchas

### Photo Management
- **SHA-256 Hashing**: All photos hashed at capture time, exactly 64 hex characters
- **Compression**: JPEG quality defaults to 75%, configurable via `image_compression_quality`
- **Cloud Storage**: Photos stored in cloud storage (S3, GCS, Azure) using Apache Libcloud
- **Thumbnails**: Generated automatically, stored in cloud alongside full images
- **GPS Tagging**: Latitude/longitude captured and stored with each photo
- **Categories**: Photos tagged with: general, interior, exterior, issues, progress
- **Upload Queue**: Background service processes pending uploads when online
- **Integrity**: Photo data validated against hash during upload and CRDT sync
- **Offline-First**: Photos stored locally first, uploaded to cloud when connectivity available

### Auto-Save Protection
- **Debounced Save**: Triggers after 2 seconds of user inactivity
- **Throttle Protection**: Won't save more than once per 30 seconds of continuous typing
- **Draft Management**: Unsaved changes preserved in memory
- **Crash Recovery**: Survives app crashes and battery issues

### Sync Behavior
- **Background Sync**: Runs every 5 minutes by default (`auto_sync_interval`)
- **Exponential Backoff**: Failed syncs retry with increasing delays
- **Offline Queue**: Operations queue when offline, process when connectivity returns
- **Health Indicators**: Visual status shows sync state (🟢🟡🔴)
- **Version Tracking**: Each client tracks last synced database version

### Database Locations
- **Backend**: `instance/backend_main.db` (Flask app)
- **Frontend**: `local_surveys.db` (BeeWare app, location varies by platform)
- **Instance Directory**: `instance/` contains Flask-specific config and database
- **Backups**: `backups/` directory with timestamped ZIP files

### Common Gotchas
- **Foreign Keys Disabled**: Required for CRDT but means referential integrity is app-level
- **App Config Not CRR**: Configuration changes don't sync between clients
- **Photo IDs are Strings**: Unlike other models that use integers
- **Timestamps are UTC**: Always timezone-aware datetime objects
- **Session Management**: Always use proper commit/rollback patterns
- **Extension Loading**: cr-sqlite must be loaded before any CRR operations
- **Site ID Uniqueness**: Each app instance must have unique site_id for proper sync

### Performance Considerations
- **Photo Thumbnails**: Always load thumbnails before full-size images
- **Lazy Loading**: Photos loaded on-demand to reduce memory usage
- **Database Indexes**: Critical for performance on large datasets
- **Sync Batching**: Large changesets processed in batches
- **Connection Pooling**: Reuse database connections efficiently

### Error Handling Patterns
- **ValidationError**: For input validation failures (field-specific messages)
- **RequestException**: For network/API failures (with retry logic)
- **IntegrityError**: For database constraint violations
- **Rollback on Error**: Always rollback transactions on exceptions
- **Graceful Degradation**: App continues to work offline when sync fails

## Current Status & Roadmap

### Completed Phases ✅

#### MVP Complete (Phase 1)
- ✅ Basic offline-first architecture with SQLite
- ✅ Image compression (75% quality) and storage
- ✅ CRDT-based sync with `cr-sqlite` for multi-client synchronization
- ✅ Survey templates and configuration management
- ✅ BeeWare cross-platform app (iOS, Android, Desktop)
- ✅ Flask REST API backend
- ✅ Complete MVP survey workflow (create, answer, save, sync)
- ✅ All question types working (text, yes/no, multiple choice, photo)
- ✅ GPS photo tagging and metadata storage
- ✅ Immediate response saving to prevent data loss

#### Enhanced Photo Management & Survey UI (Phase 2)
- ✅ GPS Integration: Auto-tag photos with location data from device
- ✅ Photo Metadata: Store EXIF data, device info, and capture conditions
- ✅ Photo Quality Assessment: Basic blur detection and warnings
- ✅ Bulk Photo Operations: Select multiple photos for batch operations
- ✅ Photo Gallery: Grid view with thumbnails, sorting by date/location
- ✅ Photo Categories: Tag photos (interior, exterior, issues, progress, etc.)
- ✅ Photo Captions: Add notes and descriptions to individual photos
- ✅ Photo Search: Filter by location, date, tags, or survey section
- ✅ Progress Tracking: Visual progress indicators for survey completion
- ✅ Required Field Validation: Clear indicators for required vs. optional fields
- ✅ Conditional Logic: Show/hide fields based on previous answers
- ✅ Photo Requirements: Visual checklists for required photos per survey section

#### Project & Site Management (Phase 3)
- ✅ Project Hierarchy: Projects → Sites → Surveys → Photos
- ✅ Project Templates: Standardized project structures for different industries
- ✅ Project Status Tracking: Draft, In Progress, Completed, Archived
- ✅ Project Metadata: Client info, due dates, priority levels
- ✅ Site Addresses: Full address with GPS coordinates
- ✅ Site Photos: Dedicated site overview photos (Photo model extended with site_id)
- ✅ Site Notes: General site information and access instructions
- ✅ Site History: Track all visits and changes over time (via timestamps)

#### Performance & Reliability (Phase 4)
- ✅ Auto-save: Never lose data due to crashes or battery issues
- ✅ Data Integrity: Checksums and validation for all stored data
- ✅ Backup & Restore: Local backups and restore functionality
- ✅ Conflict Resolution: Smart merging of conflicting changes
- ✅ Offline Queues: Queue operations for when connectivity returns
- ✅ Photo Integrity Verification: Cryptographic hashing and validation
- ✅ Advanced Sync Reliability: Exponential backoff, health indicators, configurable intervals
- ✅ Lazy Loading: Load photos on demand to reduce memory usage
- ✅ Photo Thumbnails: Generate and cache small preview images
- ✅ Database Optimization: Indexing, query optimization, efficient storage

### Next Priorities (Phase 5.5+)

#### CompanyCam API Integration (COMPLETED ✅)
- ✅ Direct API Integration: Implement the CompanyCam v2 REST API
- ✅ OAuth 2.0 Authentication: Handle CompanyCam OAuth 2.0 flow
- ✅ Smart Project Creation: `POST /v2/projects` with duplicate checking
- ✅ Batch Photo Upload: `POST /v2/projects/{project_id}/photos` with metadata
- ✅ Data Mapping UI: Configure survey→CompanyCam field mappings

#### Enhanced Survey Progress Tracking
- 📋 Detailed section breakdowns with completion percentages
- 📋 Survey versioning and change tracking
- 📋 Survey archiving with retention policies

#### Collaboration Features (MEDIUM PRIORITY)
- 👥 Selective data sync based on project ownership
- 👥 Metadata-only sync for cross-team visibility
- 👥 Lazy loading of survey data on-demand

### Known Limitations & Future Work
- **Analytics Database**: PostgreSQL integration is low priority (optional ETL)
- **Team Collaboration**: Current sync is all-or-nothing (no selective sharing)
- **Advanced Analytics**: Reporting features not yet implemented
- **Mobile Optimizations**: Could benefit from platform-specific enhancements
- **Offline Map Support**: GPS coordinates but no offline map tiles

### Risk Mitigation
- **CRDT-First Design**: Multi-client sync reliability over feature complexity
- **BeeWare Stability**: Focus on proven cross-platform framework capabilities
- **Incremental Development**: Build and validate each feature before adding complexity
- **Data Integrity**: Extensive validation and CRDT conflict resolution

## API Endpoints

### Request/Response Format Standards
- **Content-Type**: `application/json` for all requests/responses
- **Error Format**: `{"error": "error message"}` with appropriate HTTP status codes
- **Success Format**: JSON objects or arrays as documented
- **Validation Errors**: `{"error": "field_name: error message"}` for field-specific issues

### Configuration
- `GET /api/config`
  - Returns: `{"key": "value", ...}` - All configuration key-value pairs
- `GET /api/config/<key>`
  - Returns: `"value"` - Specific configuration value
  - Error: 404 if key doesn't exist
- `PUT /api/config/<key>`
  - Body: `"new_value"` or `{"value": "new_value", "description": "optional"}`
  - Returns: `{"key": "value", "description": "..."}`

### Templates
- `GET /api/templates`
  - Returns: `[{"id": 1, "name": "...", "description": "..."}, ...]`
- `GET /api/templates/<id>`
  - Returns: Template object with fields array
- `POST /api/templates`
  - Body: `{"name": "...", "description": "...", "fields": [...]}`
  - Returns: Created template object
- `PUT /api/templates/<id>`
  - Body: Template update data
  - Returns: Updated template object
- `DELETE /api/templates/<id>`
  - Returns: 204 No Content

### Projects
- `GET /api/projects`
  - Returns: Array of project objects with status, client_info, etc.
- `POST /api/projects`
  - Body: `{"name": "...", "description": "...", "status": "draft|in_progress|completed|archived", "priority": "low|medium|high", "client_info": "...", "due_date": "2024-01-01T00:00:00Z"}`
  - Returns: Created project object
- `GET /api/projects/<id>`
  - Returns: Full project object with sites relationship
- `PUT /api/projects/<id>`
  - Body: Project update data
  - Returns: Updated project object
- `DELETE /api/projects/<id>`
  - Returns: 204 No Content (cascades to sites/surveys/photos)

### Sites
- `GET /api/projects/<project_id>/sites`
  - Returns: Array of site objects for the project
- `POST /api/projects/<project_id>/sites`
  - Body: `{"name": "...", "address": "...", "latitude": 0.0, "longitude": 0.0, "notes": "..."}`
  - Returns: Created site object
- `GET /api/sites/<id>`
  - Returns: Site object with surveys relationship
- `PUT /api/sites/<id>`
  - Body: Site update data
  - Returns: Updated site object
- `DELETE /api/sites/<id>`
  - Returns: 204 No Content (cascades to surveys/photos)

### Surveys
- `GET /api/sites/<site_id>/surveys`
  - Returns: Array of survey objects with template info
- `POST /api/sites/<site_id>/surveys`
  - Body: `{"title": "...", "description": "...", "template_id": 1}`
  - Returns: Created survey object with responses array
- `GET /api/surveys/<id>`
  - Returns: Full survey object with responses and photos
- `PUT /api/surveys/<id>`
  - Body: Survey update data
  - Returns: Updated survey object
- `DELETE /api/surveys/<id>`
  - Returns: 204 No Content (cascades to responses/photos)

### Photos
- `GET /api/surveys/<survey_id>/photos`
  - Returns: Array of photo metadata (no image_data)
- `POST /api/surveys/<survey_id>/photos`
  - Body: Form data with `image` file, `description`, `category`, `latitude`, `longitude`
  - Returns: Created photo metadata object (initially with upload_status='pending')
- `GET /api/photos/<id>`
  - Returns: Photo metadata including cloud URLs and upload_status
  - Query param `include_data=true`: Downloads and returns image_data from cloud
- `DELETE /api/photos/<id>`
  - Returns: 204 No Content (deletes from cloud if uploaded)
- `GET /api/photos/<id>/integrity`
  - Returns: Integrity status (downloads from cloud for verification if needed)

### CRDT Sync
- `POST /api/changes`
  - Body: `[{"table": "...", "pk": "...", "cid": "...", "val": "...", "col_version": 1, "db_version": 5, "site_id": "..."}]`
  - Returns: `{"message": "...", "integrity_issues": [...]}` or error
- `GET /api/changes?version=<int>&site_id=<uuid>`
  - Returns: Array of change objects from other clients since specified version

## Building for Different Platforms
```bash
# Android APK
uv run briefcase create android
uv run briefcase build android
uv run briefcase run android  # Run on connected device/emulator
uv run briefcase package android  # For Play Store distribution

# iOS app (macOS only)
uv run briefcase create iOS
uv run briefcase open iOS  # Open in Xcode for testing
uv run briefcase run iOS  # Run in simulator
uv run briefcase package iOS  # For App Store

# Windows app
uv run briefcase create windows
uv run briefcase build windows
uv run briefcase run windows

# Linux app
uv run briefcase create linux
uv run briefcase build linux
uv run briefcase run linux
```

## Debugging & Troubleshooting

### Common Issues & Solutions

#### CRDT Sync Problems
**Issue**: Changes not syncing between clients
- **Check**: Verify `site_id` uniqueness across all clients
- **Fix**: Each app instance must have unique UUID in `LocalDatabase.site_id`
- **Debug**: Check logs for "site_id" in sync operations

**Issue**: Photo integrity validation failures
- **Check**: Compare hash values in `backend.log`
- **Fix**: Run `uv run flask check-photo-integrity --fix`
- **Prevent**: Ensure photos are hashed immediately after capture

**Issue**: Foreign key constraint errors during sync
- **Check**: This should not happen - foreign keys are disabled for CRDT
- **Fix**: Verify `PRAGMA foreign_keys = OFF` during CRR table creation
- **Debug**: Check backend startup logs for CRR initialization

#### Database Issues
**Issue**: `crsqlite` extension not loading
- **Check**: File exists at `~/.local/share/crsqlite/vlcn.io/crsqlite.so`
- **Fix**: Run `./setup_crsqlite.sh` to download extension
- **Alternative**: Check fallback path in `backend/lib/crsqlite.so`

**Issue**: Database locked errors
- **Check**: Multiple processes accessing same database file
- **Fix**: Close all app instances, restart Flask server
- **Prevent**: Use separate databases for development/production

**Issue**: CRR table creation fails
- **Check**: SQLite version compatibility (requires SQLite 3.35+)
- **Fix**: Update SQLite or use `pysqlite3-binary` in requirements
- **Debug**: Check for "Failed to make X CRR" in logs

#### Photo Management Issues
**Issue**: Photos not displaying correctly
- **Check**: Thumbnail generation and storage
- **Fix**: Verify Pillow is installed (`uv sync`)
- **Debug**: Check for image corruption in integrity logs

**Issue**: GPS coordinates not saving
- **Check**: Device permissions and GPS accuracy
- **Fix**: Grant location permissions to app
- **Debug**: Check coordinate validation in logs

### Debugging Commands
```bash
# Enable debug logging
export FLASK_ENV=development
uv run flask --app backend.app run --debug

# View backend logs in real-time
tail -f logs/backend.log

# Search for specific events
grep "ERROR" logs/backend.log
grep "sync" logs/backend.log
grep "CRDT" logs/backend.log
grep "integrity" logs/backend.log

# Check database schema
sqlite3 instance/backend_main.db ".schema"

# Verify CRR tables
sqlite3 instance/backend_main.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'crsql_%';"

# Check foreign keys status
sqlite3 instance/backend_main.db "PRAGMA foreign_keys;"

# Run tests with verbose output and stop on first failure
uv run pytest -v -s --tb=short

# Check database integrity
uv run flask check-photo-integrity --fix

# Debug sync issues
uv run flask --app backend.app run --debug &
curl -X GET "http://localhost:5000/api/changes?version=0&site_id=test-site-id"
```

### Performance Debugging
```bash
# Profile slow queries
uv run pytest --durations=10

# Check database indexes
sqlite3 instance/backend_main.db ".indexes"

# Monitor sync performance
grep "sync.*took" logs/backend.log

# Check photo processing times
grep "photo.*processed" logs/backend.log
```

### Error Patterns & Solutions

#### ValidationError
- **Cause**: Input data doesn't meet validation requirements
- **Solution**: Check field constraints in `shared/validation.py`
- **Debug**: Look for specific field names in error messages

#### IntegrityError
- **Cause**: Database constraint violations (unique keys, check constraints)
- **Solution**: Check data against schema constraints
- **Debug**: Verify hash lengths (64 chars), coordinate ranges, enum values

#### RequestException
- **Cause**: Network/API failures during sync
- **Solution**: Check server connectivity, retry with exponential backoff
- **Debug**: Monitor sync status indicators (🟢🟡🔴)

#### Extension Loading Errors
- **Cause**: cr-sqlite library not found or incompatible
- **Solution**: Re-run setup script, check architecture compatibility
- **Debug**: Check library paths in database connection logs

## Environment Variables
```bash
# Development
export FLASK_ENV=development
export FLASK_APP=backend/app.py

# Production
export FLASK_ENV=production
export DATABASE_URL=postgresql://survey_user:password@localhost/site_survey  # For PostgreSQL
```

## Logging
- Backend: Structured logs in `logs/backend.log` (rotation: 10MB, 5 backups)
- Frontend: Console output only
- Log levels: DEBUG, INFO, WARNING, ERROR

## Project Structure Details
```
backend/
├── app.py              # Main Flask application
├── blueprints/         # API route handlers
│   ├── config.py       # Configuration endpoints
│   ├── crdt.py         # CRDT sync endpoints
│   ├── photos.py       # Photo management
│   ├── projects.py     # Project CRUD
│   ├── sites.py        # Site CRUD
│   ├── surveys.py      # Survey CRUD
│   └── templates.py    # Template management
├── models.py           # Database models
├── utils.py            # Backend utilities
└── logging_config.py   # Logging configuration

src/survey_app/
├── app.py              # BeeWare main application
├── local_db.py         # Local SQLite with CRDT
├── handlers/           # UI event handlers
├── services/           # API and database services
├── ui/                 # UI components
└── ui_manager.py       # UI state management

tests/
├── conftest.py         # Shared test fixtures
├── test_backend/       # Backend unit tests
└── test_frontend/      # Frontend unit tests
```

## IMPORTANT: Always activate .venv first
**CRITICAL**: Remember to activate the virtual environment with `source .venv/bin/activate` before running ANY commands. All `uv run` commands must be executed from within the activated virtual environment.
