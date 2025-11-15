# KoboToolbox Bridge MVP

A Flask-based bridge that automatically syncs offline survey data from a self-hosted KoboToolbox server to CompanyCam projects.

## Overview

This project implements a **self-hosted KoboToolbox Bridge** for offline site surveys:

- **Private KoboToolbox Server**: Deploy your own KoboToolbox instance for complete data control
- **Automated Sync**: Background scheduler pulls survey data and photos every 5 minutes
- **CompanyCam Integration**: Creates projects and uploads photos automatically
- **Android-Only**: Uses KoBo Collect app for offline data collection

## Quick Start

1. **Deploy KoboToolbox** (see Phase 1 in detailed guide)
2. **Setup Bridge** (see Phase 2 in detailed guide)
3. **Configure OAuth** (see Phase 3 in detailed guide)
4. **Deploy & Test** (see Phase 5 in detailed guide)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  KoBo Collect   │ -> │ Private Kobo    │ -> │   Flask Bridge  │ -> │ CompanyCam API │
│   (Android)     │    │ Toolbox Server  │    │   (Auto Sync)   │    │ (Projects)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Files

- `README_KoboToolbox_MVP.md` - **Complete implementation guide** (authoritative)
- `src/kobo_bridge/` - Flask bridge application
- `alternative_roadmap.md` - Analysis of different approaches
- `roadmap_analysis.md` - Comparison with legacy approach

## Prerequisites

- **Server**: Arch Linux or Debian with Docker
- **Python**: 3.11+ with uv package manager
- **Database**: PostgreSQL (recommended) or SQLite
- **APIs**: KoboToolbox account + CompanyCam Pro plan

## Key Features

✅ **Self-hosted KoboToolbox** - Complete data sovereignty  
✅ **Automated background sync** - No manual intervention needed  
✅ **In-memory photo streaming** - Efficient uploads without disk storage  
✅ **OAuth 2.0 authentication** - Secure CompanyCam integration  
✅ **Status dashboard** - Monitor sync progress and errors  

## Development

```bash
# Install dependencies
uv sync

# Set environment (copy .env.example to .env)
cp .env.example .env
# Edit .env with your configuration

# Run development server
uv run flask --app src.kobo_bridge:create_app --debug run
```

## Production Deployment

See `README_KoboToolbox_MVP.md` for complete Arch/Debian deployment instructions including:

- Docker setup and KoboToolbox installation
- PostgreSQL configuration
- systemd service setup
- SSL certificate configuration

## License

See individual component licenses (KoboToolbox is open source, CompanyCam API terms apply).
