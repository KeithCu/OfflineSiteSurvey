#!/usr/bin/env python3
"""
Backup and restore utility for Site Survey App
"""
import sys
import os
import argparse
from datetime import datetime

# Add src to path so we can import the local database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from survey_app.local_db import LocalDatabase

def main():
    parser = argparse.ArgumentParser(description='Site Survey App Backup/Restore Utility')
    parser.add_argument('action', choices=['backup', 'restore', 'cleanup'], help='Action to perform')
    parser.add_argument('--db-path', default='local_surveys.db', help='Path to database file')
    parser.add_argument('--backup-dir', help='Directory for backups (default: backups/)')
    parser.add_argument('--backup-file', help='Specific backup file to restore from')
    parser.add_argument('--no-validate', action='store_true', help='Skip hash validation during restore')
    parser.add_argument('--no-media', action='store_true', help='Exclude media files from backup')
    parser.add_argument('--max-backups', type=int, default=10, help='Maximum number of backups to keep')

    args = parser.parse_args()

    # Initialize database
    db = LocalDatabase(args.db_path)

    try:
        if args.action == 'backup':
            include_media = not args.no_media
            backup_path = db.backup(args.backup_dir, include_media=include_media)
            if backup_path:
                print(f"✅ Backup completed: {backup_path}")
                # Cleanup old backups
                db.cleanup_old_backups(args.backup_dir, args.max_backups)
            else:
                print("❌ Backup failed")
                sys.exit(1)

        elif args.action == 'restore':
            if not args.backup_file:
                print("❌ --backup-file is required for restore")
                sys.exit(1)

            validate = not args.no_validate
            db.restore(args.backup_file, validate_hashes=validate)
            print(f"✅ Restore completed from: {args.backup_file}")

        elif args.action == 'cleanup':
            db.cleanup_old_backups(args.backup_dir, args.max_backups)
            print("✅ Cleanup completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
