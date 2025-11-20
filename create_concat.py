#!/usr/bin/env python3
"""
Script to concatenate all Python source files in logical order.
Automatically includes current date in filename.
"""
import os
import argparse
from datetime import datetime

def remove_comments(content):
    """Remove comments and docstrings from Python code to reduce token count."""
    lines = content.split('\n')
    result = []
    in_triple_quote = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check for single-line docstrings (starts and ends with triple quotes)
        if (stripped.startswith('"""') and stripped.endswith('"""') and len(stripped) > 6) or \
           (stripped.startswith("'''") and stripped.endswith("'''") and len(stripped) > 6):
            # Single-line docstring - skip it
            continue
        
        # Track triple-quoted strings (docstrings) that span multiple lines
        triple_double = line.count('"""')
        triple_single = line.count("'''")
        
        # Check if we're entering or exiting a triple-quoted string
        if triple_double > 0:
            if triple_double % 2 == 1:
                in_triple_quote = not in_triple_quote
        if triple_single > 0:
            if triple_single % 2 == 1:
                in_triple_quote = not in_triple_quote
        
        # If we're inside a triple-quoted string, skip the line entirely
        if in_triple_quote:
            continue
        
        # Remove single-line comments (# ...) but preserve # inside strings
        in_string = False
        string_char = None
        comment_pos = -1
        
        i = 0
        while i < len(line):
            char = line[i]
            
            # Handle escape sequences
            if char == '\\' and i + 1 < len(line):
                i += 2
                continue
            
            # Track string boundaries (single and double quotes)
            if char in ('"', "'"):
                # Check for triple quotes first
                if i + 2 < len(line) and line[i:i+3] == char * 3:
                    i += 3
                    continue
                # Regular string quote
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            # Found # outside of string - this is a comment
            if char == '#' and not in_string:
                comment_pos = i
                break
            
            i += 1
        
        # Remove comment if found
        if comment_pos >= 0:
            line = line[:comment_pos].rstrip()
        
        # Keep the line (even if empty, to preserve structure)
        result.append(line)
    
    return '\n'.join(result)

def main():
    parser = argparse.ArgumentParser(description='Concatenate Python source files')
    parser.add_argument('--keep-comments', action='store_true', 
                       help='Keep comments in output (default: remove comments)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output filename (default: source_code_YYYYMMDD.txt)')
    args = parser.parse_args()
    
    remove_comments_flag = not args.keep_comments
    
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
        
        # Database migrations
        'migrations/versions/001_add_phase2_fields.py',
        'migrations/versions/002_section_tags.py',
        
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
        'src/survey_app/services/network_queue.py',
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
    if args.output:
        output_file = args.output
    else:
        suffix = '_no_comments' if remove_comments_flag else ''
        output_file = f'source_code_{current_date}{suffix}.txt'
    
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
                        if remove_comments_flag:
                            content = remove_comments(content)
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
    if remove_comments_flag:
        print("Comments and docstrings removed for API usage")

if __name__ == '__main__':
    main()
