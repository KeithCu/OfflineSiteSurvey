#!/usr/bin/env python3
"""
Startup script for KoboToolbox Bridge MVP
"""
from src.kobo_bridge.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
