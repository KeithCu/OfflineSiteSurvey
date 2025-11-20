#!/usr/bin/env python3
"""
Startup script for KoboToolbox Bridge MVP
"""
from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
