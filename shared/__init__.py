"""Shared utilities package for Site Survey application.

This package contains shared code used by both the backend Flask API and the frontend
BeeWare application. It includes:

- Database models (models.py) - SQLAlchemy models with cross-platform compatibility
- Enums (enums.py) - Shared enumeration definitions for status values and categories
- Validation utilities (validation.py, schemas.py) - Input validation and sanitization
- Utility functions (utils.py) - Photo processing, conditional logic, and helpers

All shared components are designed to work identically in both backend and frontend contexts.
"""
