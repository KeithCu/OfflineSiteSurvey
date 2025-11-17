# Site Survey App - Development Roadmap

## Overview
Build a robust, offline-first survey application using BeeWare and CRDT-based synchronization. Focus on reliable offline functionality with seamless multi-client sync when connectivity returns.

## Phase 1: Core Infrastructure & MVP (COMPLETED ✅)
- [x] Basic offline-first architecture with SQLite
- [x] Image compression (75% quality) and storage
- [x] CRDT-based sync with `cr-sqlite` for multi-client synchronization
- [x] Survey templates and configuration management
- [x] BeeWare cross-platform app (iOS, Android, Desktop)
- [x] Flask REST API backend
- [x] Complete MVP survey workflow (create, answer, save, sync)
- [x] All question types working (text, yes/no, multiple choice, photo)
- [x] GPS photo tagging and metadata storage
- [x] Immediate response saving to prevent data loss
- [x] Template field ordering and validation
- [] PostgreSQL optional analytics database

## Phase 2: Enhanced Photo Management & Survey UI 🚀 (COMPLETED ✅)

### Photo Capture & Processing
- [x] **GPS Integration**: Auto-tag photos with location data from device
- [x] **Photo Metadata**: Store EXIF data, device info, and capture conditions
- [x] **Photo Quality Assessment**: Basic blur detection and warnings
- [x] **Bulk Photo Operations**: Select multiple photos for batch operations

### Photo Organization & UI
- [x] **Photo Gallery**: Grid view with thumbnails, sorting by date/location
- [x] **Photo Categories**: Tag photos (interior, exterior, issues, progress, etc.)
- [x] **Photo Captions**: Add notes and descriptions to individual photos
- [x] **Photo Search**: Filter by location, date, tags, or survey section

### Survey UI Improvements
- [x] **Progress Tracking**: Visual progress indicators for survey completion
- [x] **Required Field Validation**: Clear indicators for required vs. optional fields
- [x] **Conditional Logic**: Show/hide fields based on previous answers
- [x] **Photo Requirements**: Visual checklists for required photos per survey section

## Phase 3: Project & Site Management 📁 (COMPLETED ✅)

### Project Structure
- [x] **Project Hierarchy**: Projects → Sites → Surveys → Photos
- [x] **Project Templates**: Standardized project structures for different industries
- [x] **Project Status Tracking**: Draft, In Progress, Completed, Archived
- [x] **Project Metadata**: Client info, due dates, priority levels

### Site Management
- [x] **Site Addresses**: Full address with GPS coordinates
- [x] **Site Photos**: Dedicated site overview photos (Photo model extended with site_id)
- [x] **Site Notes**: General site information and access instructions
- [x] **Site History**: Track all visits and changes over time (via timestamps)

### Survey Management
- [ ] **Survey Progress Tracking**: Completion percentages, required vs. optional fields
- [ ] **Survey Versions**: Track changes and updates to surveys
- [ ] **Survey Archiving**: Archive completed surveys with retention policies

## Phase 4: User Experience & Reliability ⚡ (COMPLETED ✅)

### User Interface
- [x] **Intuitive Navigation**: Clear project → site → survey → photo hierarchy
- [x] **Offline Indicators**: Clear visual indicators of connectivity status
- [x] **Progress Indicators**: Show sync progress, upload/download status
- [x] **Error Recovery**: User-friendly error messages with recovery options
- [x] **Dark Mode**: Eye-friendly interface for outdoor use

### Performance Optimizations
- [x] **Lazy Loading**: Load photos on demand to reduce memory usage
- [x] **Photo Thumbnails**: Generate and cache small preview images
- [x] **Database Optimization**: Indexing, query optimization, efficient storage
- [x] **Background Processing**: Handle uploads/downloads in background
- [x] **Memory Management**: Proper cleanup and garbage collection

### Reliability Features
- [x] **Auto-save**: Never lose data due to crashes or battery issues
- [x] **Data Integrity**: Checksums and validation for all stored data
- [x] **Backup & Restore**: Local backups and restore functionality
- [x] **Conflict Resolution**: Smart merging of conflicting changes
- [x] **Offline Queues**: Queue operations for when connectivity returns

## Phase 5.5: CompanyCam API Integration 🔄 (HIGH PRIORITY - COMPETITIVE ADVANTAGE)

### Overview
Create a direct, one-way sync bridge from this app to CompanyCam using their robust v2 REST API. This positions the app as a "CompanyCam Offline Companion," solving connectivity issues by queuing data (projects, photos, and metadata) locally and seamlessly pushing it to the user's CompanyCam account when connectivity is restored.

### Core Integration Features
- [ ] **Direct API Integration**: Implement the CompanyCam v2 REST API
- [ ] **OAuth 2.0 Authentication**: Handle CompanyCam OAuth 2.0 flow to securely connect user accounts
- [ ] **Smart Project Creation**: `POST /v2/projects` to create new projects with duplicate checking
- [ ] **Batch Photo Upload**: `POST /v2/projects/{project_id}/photos` for photo uploads with metadata
- [ ] **Metadata & Tag Mapping**: Map survey data to CompanyCam tags and notepad fields

### User Experience
- [ ] **One-Time OAuth Connection**: "Connect to CompanyCam" button with OAuth 2.0 browser flow
- [ ] **Project Export**: "Send to CompanyCam" button in completed surveys
- [ ] **Offline Queue Integration**: Export works without active connection using background sync
- [ ] **Sync Status**: Clear status indicators ("Pending," "Uploading (3/15)", "Complete", "Failed")
- [ ] **Error Handling**: Graceful handling of auth expiry, quota limits, plan restrictions

### Technical Implementation
- [ ] **OAuth 2.0 Flow**: Implement Authorization Code grant with custom URL scheme redirect
- [ ] **Token Management**: Secure storage and automatic refresh of access/refresh tokens
- [ ] **Background Upload Queue**: Sequential project and photo uploads with progress tracking
- [ ] **Rate Limiting**: Exponential backoff for API rate limits (429 responses)
- [ ] **Tag Creation**: `POST /v2/tags` to create CompanyCam tags matching survey categories

### Challenges & Solutions (API-Plan Specific)

#### Challenge: API Plan Requirements
**Issue**: CompanyCam API only available on Pro, Premium, and Elite plans (not Basic)
**Solutions**:
- **Plan Check UI**: Inform users that "CompanyCam Pro or higher" is required
- **Graceful Degradation**: Clear error messages for insufficient plans
- **Fallback to CSV**: Keep CSV export as backup for Basic plan users

#### Challenge: OAuth in Cross-Platform Apps
**Issue**: OAuth redirect flow requires browser handling in mobile/desktop apps
**Solutions**:
- **In-App Web View**: Use embedded browser for OAuth authorization
- **Custom URL Scheme**: Register app-specific URL scheme (e.g., `mysurveyapp://auth`)
- **Platform-Specific Handling**: Different implementations for iOS, Android, desktop

#### Challenge: Data Structure Mapping
**Issue**: Survey fields don't perfectly match CompanyCam's structure
**Solutions**:
- **Tag-Based Mapping**: Use CompanyCam tags for flexible categorization
- **Notepad for Complex Data**: Store structured survey data in project notepad
- **User-Configurable Mapping**: Allow users to define field→tag mappings

### Implementation Priority (API-First Approach)
1. **OAuth 2.0 Authentication**: Implement full OAuth flow with token management
2. **Project & Photo Upload**: Background queue for `POST /v2/projects` and photo uploads
3. **Data Mapping UI**: Interface for configuring survey→CompanyCam field mappings
4. **Error Handling**: Robust error recovery for auth, quotas, and plan issues
5. **CSV Fallback**: Keep CSV export only for users without API access

### API Endpoints to Implement
- `POST /oauth/authorize` - OAuth authorization flow
- `POST /v2/projects` - Create CompanyCam projects
- `GET /v2/projects?query=...` - Check for existing projects
- `POST /v2/projects/{project_id}/photos` - Upload photos with metadata
- `POST /v2/tags` - Create tags for categorization

### Success Metrics
- [ ] **Authentication Success**: 98% successful OAuth connections
- [ ] **Upload Reliability**: Successfully sync 95% of projects/photos
- [ ] **Data Preservation**: 100% retention of GPS, timestamps, and survey metadata
- [ ] **User Experience**: Export completes in < 3 minutes for typical projects
- [ ] **Error Recovery**: Automatic handling of 90% of common error scenarios

### Business Value
- **Seamless Integration**: Native CompanyCam compatibility vs. manual import
- **Market Positioning**: "CompanyCam's missing offline capability"
- **User Retention**: Easy migration path for existing CompanyCam users
- **Revenue Model**: Premium feature or partnership opportunity

## Phase 6: Collaboration & Team Features 👥 (MEDIUM PRIORITY)

### Selective Data Sync & Visibility (HIGH PRIORITY SUBTASK)
**Problem**: Current CRDT implementation syncs ALL data to ALL clients, causing:
- Excessive storage usage on mobile devices (photos from other sites/projects)
- High bandwidth consumption on slow/expensive connections
- Privacy concerns (surveyors seeing data from other teams)
- Performance issues with large datasets

**Requirements**:
- Clients can SEE metadata (survey titles, site names, project info) from other teams
- Full data (responses, photos) only downloaded when explicitly requested
- "Data ownership" model: each client owns their created data, can share others' data on-demand
- UI indicators for "available locally" vs "available remotely"

**Proposed Solution**:
1. **Metadata-Only Sync**: Modify CRDT to sync metadata tables (projects, sites, surveys) to all clients, but exclude response/photo data unless owned by that client
2. **Lazy Loading API**: Add `/api/surveys/{id}/request-data` endpoint that triggers selective sync of specific survey data
3. **Ownership Tracking**: Add `owner_site_id` field to surveys/responses/photos to track which client created the data
4. **UI Enhancements**:
   - Survey list shows "🔄 Download Data" button for remote surveys
   - Photo gallery shows placeholders for remote photos with "Load" option
   - Progress indicators for data downloads
5. **Sync Protocol Changes**:
   - Clients send `site_id` in sync requests
   - Server filters changesets: send full data only for owned records, metadata-only for others
   - Add "data request" messages to trigger selective downloads

**Implementation Steps**:
1. Add ownership fields to models (`owner_site_id`)
2. Modify sync logic in `crdt.py` to filter by ownership
3. Create selective sync endpoints
4. Update frontend to handle partial data states
5. Add download progress UI
6. Test with multiple clients to ensure data isolation

**Benefits**: 90%+ reduction in default data transfer, improved privacy, better mobile performance.

### User Management
- [ ] **User Authentication**: Secure login with password/biometric options
- [ ] **User Roles**: Admin, Manager, Surveyor with appropriate permissions
- [ ] **Team Management**: Add/remove team members, assign roles
- [ ] **User Profiles**: Contact info, preferences, assigned projects

### Collaboration Features
- [ ] **Photo Comments**: Team members can comment on photos
- [ ] **Task Assignment**: Assign specific surveys/photos to team members
- [ ] **Change Tracking**: See who made what changes and when
- [ ] **Real-time Sync**: Push notifications for team updates (when online)

### Communication
- [ ] **In-app Messaging**: Communicate about projects and issues
- [ ] **Photo Sharing**: Share specific photos with team members
- [ ] **Report Sharing**: Share completed reports with stakeholders

## Phase 4: Data Export & Analytics 📊 (MEDIUM PRIORITY)

### Export Features
- [ ] **PDF Reports**: Generate professional reports with photos and survey data
- [ ] **Excel/CSV Export**: Export survey data for analysis in other tools
- [ ] **Photo Export**: Bulk download of survey photos with metadata
- [ ] **Data Backup**: Complete survey data backup and restore functionality

### Analytics Dashboard
- [ ] **Survey Completion Rates**: Track completion statistics over time
- [ ] **Photo Quality Metrics**: Statistics on photo count, size, and quality
- [ ] **Survey Performance**: Average completion times and common issues
- [ ] **Geographic Analysis**: Map view of survey locations and coverage

### PostgreSQL Integration (Optional)
- [ ] **Automated ETL**: Background sync from SQLite to PostgreSQL for analytics
- [ ] **Advanced Queries**: Complex reporting queries not suitable for SQLite
- [ ] **Data Archiving**: Long-term storage and historical trend analysis

## Phase 5: Mobile-Specific Features 📱 (MEDIUM PRIORITY)

### iOS/Android Optimizations
- [ ] **Platform-Specific UI**: Native look and feel for each platform
- [ ] **Camera Integration**: Direct camera access with preview and controls
- [ ] **Offline Maps**: Cache maps for GPS coordinates without internet
- [ ] **Push Notifications**: Background sync status and completion reminders
- [ ] **Biometric Authentication**: Face ID/Touch ID for secure access

### Performance & Battery
- [ ] **Background Sync**: Efficient background synchronization when on WiFi
- [ ] **Battery Optimization**: Minimize battery drain during surveys
- [ ] **Storage Management**: Smart photo compression based on device storage
- [ ] **Memory Optimization**: Handle large photo libraries without crashes

## Phase 6: Advanced Features 🔧 (LOW PRIORITY)

### Template System Enhancements
- [ ] **Dynamic Templates**: Create survey templates programmatically
- [ ] **Template Marketplace**: Share and download community templates
- [ ] **Custom Field Types**: Advanced field types (GPS, signatures, etc.)
- [ ] **Template Versioning**: Track changes and updates to templates

### Integration APIs
- [ ] **REST API**: Full API for third-party integrations
- [ ] **Webhook Support**: Real-time notifications for external systems
- [ ] **Import/Export**: Bulk operations and data migration tools

## Technical Debt & Maintenance 🔄 (ONGOING)

### Code Quality
- [ ] **Unit Tests**: Test coverage for core survey and sync functionality
- [ ] **Integration Tests**: Test CRDT sync scenarios and multi-client conflicts
- [ ] **UI Tests**: Test BeeWare UI components across platforms
- [ ] **Performance Testing**: Benchmark sync performance and photo handling

### BeeWare Ecosystem
- [ ] **BeeWare Updates**: Keep up with Toga and Briefcase framework updates
- [ ] **Platform SDK Updates**: iOS/Android SDK compatibility and optimizations
- [ ] **Dependency Management**: Regular updates to Python packages and libraries
- [ ] **Cross-Platform Testing**: Ensure consistent behavior across all platforms

## Success Metrics 📊

### Core Functionality
- [ ] **CRDT Sync Reliability**: 99.9% successful multi-client synchronization
- [ ] **Offline Operation**: Full functionality for 30+ days without connectivity
- [ ] **Data Integrity**: Zero data loss or corruption in normal usage
- [ ] **Cross-Platform Consistency**: Identical core functionality on iOS, Android, Desktop

### Performance
- [ ] **Photo Handling**: Process and store photos < 2 seconds after capture
- [ ] **Sync Performance**: Sync 100 photos in < 30 seconds on good connection
- [ ] **Storage Efficiency**: 1000+ photos in < 500MB with compression
- [ ] **App Responsiveness**: < 100ms UI response times

### User Experience
- [ ] **Intuitive Interface**: Complete basic surveys without documentation
- [ ] **Survey Completion**: 95% survey completion rate in field conditions
- [ ] **Error Recovery**: Automatic recovery from 90% of common error scenarios
- [ ] **Battery Efficiency**: < 25% battery drain during 8-hour survey sessions

## Implementation Priority Guidelines

1. **Must-Have**: CRDT sync reliability, photo capture/storage, survey completion workflow
2. **Should-Have**: Enhanced photo management, cross-platform optimizations, data export
3. **Nice-to-Have**: Advanced analytics, team collaboration, integration APIs
4. **Never**: Features that compromise offline functionality or sync reliability

## Current Status Summary

✅ **MVP COMPLETE**: Full survey workflow functional - create surveys from templates, answer all question types (text, yes/no, multiple choice, photo), immediate response saving, GPS photo tagging, CRDT sync, and complete data persistence.
✅ **Phase 2 COMPLETE**: Enhanced survey UI with conditional logic (fields show/hide based on answers), photo requirements checklists, visual progress tracking, required field validation, and comprehensive photo management with categories, search, metadata storage, and quality assessment.
✅ **Phase 3 COMPLETE**: Comprehensive project and site management with status tracking (Draft/In Progress/Completed/Archived), metadata (client info, due dates, priority), templates, and enhanced site features (notes, GPS coordinates, dedicated photos).
✅ **Phase 4 COMPLETE**: Enterprise-grade performance and reliability features including photo integrity verification, advanced sync with exponential backoff, auto-save protection, thumbnail caching with pagination, and comprehensive backup/restore tooling.
📋 **Next Priority**: Enhanced survey progress tracking with detailed section breakdowns, user experience improvements, and team collaboration features.

## Risk Mitigation

- **CRDT-First Design**: Multi-client sync reliability over feature complexity
- **BeeWare Stability**: Focus on proven cross-platform framework capabilities
- **Incremental Development**: Build and validate each feature before adding complexity
- **Data Integrity**: Extensive validation and CRDT conflict resolution
- **User-Centric Testing**: Regular field testing with actual survey workflows

---

*The MVP is now complete and ready for field testing! This roadmap continues with enhanced features for photo management, project organization, and user experience improvements while maintaining the proven offline-first architecture.*
