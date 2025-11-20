#!/usr/bin/env python3
"""
Script to concatenate all Python source files in logical order.
Automatically includes current date in filename.
"""
import os
from datetime import datetime

def main():
    # Define the ordered list of files
    ordered_files = [
        # Shared code
        'shared/__init__.py',
        'shared/enums.py',
        'shared/models.py',
        'shared/utils.py',
        'shared/validation.py',
        
        # Backend core
        'backend/models.py',
        'backend/app.py',
        'backend/utils.py',
        'backend/logging_config.py',
        
        # Backend base
        'backend/base/__init__.py',
        'backend/base/crud_base.py',
        
        # Backend services
        'backend/services/__init__.py',
        'backend/services/cloud_storage.py',
        'backend/services/upload_queue.py',
        
        # Backend blueprints
        'backend/blueprints/__init__.py',
        'backend/blueprints/auth.py',
        'backend/blueprints/config.py',
        'backend/blueprints/crdt.py',
        'backend/blueprints/photos.py',
        'backend/blueprints/projects.py',
        'backend/blueprints/sites.py',
        'backend/blueprints/surveys.py',
        'backend/blueprints/templates.py',
        
        # Backend CLI
        'backend/cli.py',
        
        # Backend template storage
        'backend/store_survey_template.py',
        
        # Frontend core
        'src/survey_app/__main__.py',
        'src/survey_app/app.py',
        'src/survey_app/local_db.py',
        'src/survey_app/config_manager.py',
        'src/survey_app/ui_manager.py',
        'src/survey_app/logging_config.py',
        'src/survey_app/toga_mock.py',
        
        # Frontend services
        'src/survey_app/services/__init__.py',
        'src/survey_app/services/api_service.py',
        'src/survey_app/services/companycam_service.py',
        'src/survey_app/services/db_service.py',
        'src/survey_app/services/tag_mapper.py',
        
        # Frontend handlers
        'src/survey_app/handlers/__init__.py',
        'src/survey_app/handlers/companycam_handler.py',
        'src/survey_app/handlers/photo_handler.py',
        'src/survey_app/handlers/project_handler.py',
        'src/survey_app/handlers/site_handler.py',
        'src/survey_app/handlers/survey_handler.py',
        'src/survey_app/handlers/sync_handler.py',
        'src/survey_app/handlers/tag_management_handler.py',
        'src/survey_app/handlers/template_handler.py',
        
        # Frontend UI
        'src/survey_app/ui/__init__.py',
        'src/survey_app/ui/survey_ui.py',
        
        # Utility scripts
        'backup_restore.py',
        'run.py'
    ]
    
    # Create output filename with current date
    current_date = datetime.now().strftime('%Y%m%d')
    output_file = f'source_code_{current_date}.txt'
    
    with open(output_file, 'w') as outfile:
        # Write header
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"""================================================================================
Site Survey App - Complete Python Source Code
Generated: {current_time}
================================================================================

"""
        outfile.write(header)
        
        # Process each file
        for file_path in ordered_files:
            if os.path.exists(file_path):
                outfile.write(f"\n================================================================================\n")
                outfile.write(f"FILE: {file_path}\n")
                outfile.write("================================================================================\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        outfile.write(content)
                        outfile.write('\n')
                    print(f"Added: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    outfile.write(f"# Error reading file: {e}\n\n")
            else:
                print(f"File not found: {file_path}")
                outfile.write(f"\n================================================================================\n")
                outfile.write(f"FILE: {file_path} (NOT FOUND)\n")
                outfile.write("================================================================================\n\n")
    
    print(f"\nConcatenation complete! Output written to: {output_file}")
    print(f"Total files processed: {len(ordered_files)}")

if __name__ == '__main__':
    main()
