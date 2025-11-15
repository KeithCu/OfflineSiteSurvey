# Site Survey App Project

This project contains a comprehensive offline-first site survey application with advanced features.

## Overview

- **Backend:** Flask REST API with configuration management and survey templates
- **Frontend:** BeeWare cross-platform app (iOS, Android, Desktop) with offline functionality
- **Database:** PostgreSQL/SQLite backend, local SQLite frontend for offline-first operation
- **Features:** Automatic image compression, configurable settings, template-based surveys, and robust offline sync

## Key Features

- **Offline-First Architecture**: Works without internet connectivity, syncs when available
- **Automatic Image Compression**: Reduces photo sizes to 75% quality to save storage
- **Configurable Settings**: Server-managed configuration for image quality, sync intervals, etc.
- **Survey Templates**: Create and manage reusable survey templates for different property types
- **Cross-Platform**: Native apps for iOS, Android, Windows, macOS, and Linux

## File Structure

- `pyproject.toml` (Project config)
- `README.md` (This file)
- `backend/app.py` (Flask backend with config & template APIs)
- `backend/store_survey_template.py` (Comprehensive store survey template)
- `src/survey_app/app.py` (BeeWare frontend with image compression)
- `src/survey_app/local_db.py` (Local DB with image processing)

## New Features

### Image Compression
- Automatically compresses photos to 75% JPEG quality
- Maintains original dimensions to preserve aspect ratios
- Reduces storage usage for offline surveys

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

### Enhanced UI
- Settings panel for configuration management
- Templates browser for creating surveys from templates
- Improved offline handling and sync status

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

## How to Run

### Backend (Flask)

#### Option 1: Using uv (recommended)
1. Install uv if you haven't: `pip install uv`
2. Create and activate environment: `uv venv`
3. Activate it: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
4. Install dependencies: `uv pip install -e .`
5. Set Flask environment: `export FLASK_APP=backend/app.py` (or `set FLASK_APP=backend/app.py` on Windows)
6. Run the server: `flask run`

#### Option 2: Using pip and venv
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3. Install dependencies: `pip install Flask Flask-SQLAlchemy requests`
4. Set Flask environment: `export FLASK_APP=backend/app.py` (or `set FLASK_APP=backend/app.py` on Windows)
5. Run the server: `flask run`

### Complete Arch Linux Backend Deployment

For production deployment on Arch Linux, here's a complete setup:

#### 1. System Dependencies
```bash
# Update system
sudo pacman -Syu

# Install Python and pip
sudo pacman -S python python-pip

# Install PostgreSQL (if using instead of SQLite)
sudo pacman -S postgresql
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Initialize PostgreSQL database
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl restart postgresql

# Create database user and database
sudo -u postgres createuser --interactive --pwprompt survey_user
sudo -u postgres createdb -O survey_user site_survey
```

#### 2. Application Setup
```bash
# Clone/download your project
cd /home/keithcu/Desktop/Python/OfflineSiteSurvey

# Install uv (if not already installed)
pip install uv

# Create production environment
uv venv --python 3.11  # Use stable Python version

# Activate environment
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Set environment variables
export FLASK_APP=backend/app.py
export FLASK_ENV=production

# For PostgreSQL (if using instead of SQLite):
export DATABASE_URL=postgresql://survey_user:password@localhost/site_survey
```

#### 3. Database Setup
```bash
# Initialize database
flask db upgrade  # If using Flask-Migrate

# Or create tables directly
python -c "from backend.app import db; db.create_all()"
```

#### 4. Production Server Setup
```bash
# Install Gunicorn for production WSGI server
uv pip install gunicorn

# Test Gunicorn locally
gunicorn --bind 0.0.0.0:8000 backend.app:app

# For production, use a process manager like systemd
```

#### 5. Systemd Service (Production)
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

Enable and start the service:
```bash
sudo systemctl enable site-survey
sudo systemctl start site-survey
sudo systemctl status site-survey
```

#### 6. Apache Reverse Proxy (Alternative to Nginx)

For Apache instead of Nginx, use these instructions:

```bash
# Install Apache and mod_wsgi
sudo pacman -S apache python-mod_wsgi

# Create Apache configuration
sudo nano /etc/httpd/conf/extra/site-survey.conf
```

Add to the configuration file:
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

Create the WSGI file:
```bash
nano /home/keithcu/Desktop/Python/OfflineSiteSurvey/backend/app.wsgi
```

Add to app.wsgi:
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

Enable the site and restart Apache:
```bash
# Include the configuration
echo "Include conf/extra/site-survey.conf" | sudo tee -a /etc/httpd/conf/httpd.conf

# Enable and start Apache
sudo systemctl enable httpd
sudo systemctl start httpd

# Test the configuration
sudo apachectl configtest
```

#### 7. Nginx Reverse Proxy (Alternative to Apache)
```bash
# Install Nginx
sudo pacman -S nginx

# Create site configuration
sudo nano /etc/nginx/sites-available/site-survey
```

Add to the file:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/site-survey /etc/nginx/sites-enabled/
sudo systemctl enable nginx
sudo systemctl start nginx
```

#### 8. SSL with Let's Encrypt (Optional)
```bash
# Install certbot
sudo pacman -S certbot certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### Frontend (BeeWare)

#### Prerequisites for Mobile Development

##### For Android Development:
1. **Install Android SDK and NDK:**
   ```bash
   # Install JDK
   sudo pacman -S jdk17-openjdk

   # Install Android SDK tools
   yay -S android-sdk-cmdline-tools-latest
   yay -S android-platform-tools
   yay -S android-ndk

   # Set up Android SDK (replace with your preferred location)
   export ANDROID_HOME=$HOME/Android/Sdk
   export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
   ```

2. **Accept Android SDK licenses:**
   ```bash
   yes | sdkmanager --licenses
   ```

##### For iOS Development (macOS only):
1. **Install Xcode from App Store**
2. **Install command line tools:**
   ```bash
   xcode-select --install
   ```

#### Mobile Deployment Steps

##### Android Deployment:
```bash
# 1. Create Android app
uv run briefcase create android

# 2. Build the APK
uv run briefcase build android

# 3. Run on connected device/emulator
uv run briefcase run android

# 4. Or package for distribution
uv run briefcase package android
```

##### iOS Deployment:
```bash
# 1. Create iOS app (requires macOS)
uv run briefcase create iOS

# 2. Open in Xcode for testing
uv run briefcase open iOS

# 3. Build and run (requires iOS device/simulator)
uv run briefcase run iOS
```

#### Desktop Testing (Linux/macOS/Windows):
```bash
# Quick development testing
uv run briefcase dev

# Or full packaged app
uv run briefcase run linux  # or macOS/windows
```

#### Testing Your Mobile App

After building your app, test it thoroughly:

1. **Desktop testing first:**
   ```bash
   uv run briefcase dev  # Quick development mode
   uv run briefcase run linux  # Full packaged desktop app
   ```

2. **Android testing:**
   ```bash
   # Connect Android device or start emulator
   adb devices

   # Run on device
   uv run briefcase run android
   ```

3. **iOS testing (macOS only):**
   ```bash
   # Open in Xcode
   uv run briefcase open iOS

   # Run in simulator
   uv run briefcase run iOS
   ```

#### Troubleshooting

**Android Issues:**
- **SDK licenses:** Run `yes | sdkmanager --licenses`
- **Device not found:** Ensure USB debugging is enabled and device is authorized
- **Build fails:** Check that ANDROID_HOME is set correctly

**iOS Issues:**
- **Xcode version:** Ensure Xcode is up to date
- **Code signing:** For physical devices, you need an Apple Developer account
- **Simulator issues:** Try resetting the simulator

**Common Issues:**
- **Dependencies:** Make sure all required system packages are installed
- **Python version:** BeeWare works best with Python 3.8-3.11
- **Network:** Mobile apps need proper permissions for network access

#### Distribution

**Android:**
```bash
# Create signed APK for Play Store
uv run briefcase package android

# The APK will be in: android/gradle/app/build/outputs/apk/release/
```

**iOS:**
```bash
# Create IPA for App Store (requires Apple Developer account)
uv run briefcase package iOS

# The IPA will be in: iOS/build/
```
