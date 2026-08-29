import csv
import ast
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from user_request.models import MetaTemplate


class Command(BaseCommand):
    help = 'Import Meta Templates from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            help='Path to the CSV file containing meta templates',
            default='Meta Templates - Sheet1.csv'
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        # Try to find the CSV file in common locations
        possible_paths = [
            csv_file_path,
            os.path.join(settings.BASE_DIR, '..', csv_file_path),
            os.path.join(settings.BASE_DIR, csv_file_path),
            os.path.join(os.path.dirname(settings.BASE_DIR), csv_file_path),
        ]
        
        actual_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_path = path
                break
        
        if not actual_path:
            self.stdout.write(self.style.ERROR(f'CSV file not found. Tried: {possible_paths}'))
            return
        
        self.stdout.write(f'Importing templates from: {actual_path}')
        
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        with open(actual_path, 'r', encoding='utf-8') as csvfile:
            # Skip the first empty line
            first_line = csvfile.readline()
            
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                try:
                    template_id = row.get('Template ID', '').strip()
                    if not template_id:
                        self.stdout.write(self.style.WARNING('Skipping row with no Template ID'))
                        continue
                    
                    # Parse meta_mapping from string to list
                    meta_mapping_str = row.get('Meta Mapping', '[]')
                    try:
                        meta_mapping = ast.literal_eval(meta_mapping_str)
                        if not isinstance(meta_mapping, list):
                            meta_mapping = []
                    except (ValueError, SyntaxError):
                        meta_mapping = []
                    
                    template_data = {
                        'template_id': template_id,
                        'meta_template_name': row.get('Meta Template Name', '').strip(),
                        'library': row.get('Library', '').strip(),
                        'message_name': row.get('Message Name', '').strip(),
                        'category': row.get('Category', '').strip(),
                        'treatment': row.get('Treatment', '').strip(),
                        'objection': row.get('Objection', '').strip(),
                        'trigger': row.get('Trigger', '').strip(),
                        'day': row.get('Day', '').strip(),
                        'header_type': row.get('Header Type', '').strip(),
                        'header_text': row.get('Header Text', '').strip(),
                        'meta_approved_body': row.get('Meta Approved Body', '').strip(),
                        'cta_type': row.get('CTA Type', '').strip(),
                        'cta_value': row.get('CTA Value', '').strip(),
                        'media_type': row.get('Media Type', '').strip(),
                        'media_asset_id': row.get('Media Asset ID', '').strip(),
                        'variable_mapping': row.get('Variable Mapping', '').strip(),
                        'objective': row.get('Objective', '').strip(),
                        'ai_personalization_inputs': row.get('AI Personalization Inputs', '').strip(),
                        'ai_writing_rules': row.get('AI Writing Rules', '').strip(),
                        'workflow_exit_condition': row.get('Workflow Exit Condition', '').strip(),
                        'internal_notes': row.get('Internal Notes', '').strip(),
                        'meta_templates': row.get('Meta Templates', '').strip(),
                        'meta_mapping': meta_mapping,
                    }
                    
                    # Check if template exists
                    existing_template = MetaTemplate.objects.filter(template_id=template_id).first()
                    
                    if existing_template:
                        # Update existing template
                        for key, value in template_data.items():
                            setattr(existing_template, key, value)
                        existing_template.save()
                        updated_count += 1
                        self.stdout.write(f'Updated: {template_id}')
                    else:
                        # Create new template
                        MetaTemplate.objects.create(**template_data)
                        imported_count += 1
                        self.stdout.write(f'Imported: {template_id}')
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'Error processing row: {str(e)}'))
                    self.stdout.write(self.style.ERROR(f'Row data: {row.get("Template ID", "N/A")}'))
                    continue
        
        self.stdout.write(self.style.SUCCESS(
            f'\nImport complete:\n'
            f'- Imported: {imported_count}\n'
            f'- Updated: {updated_count}\n'
            f'- Errors: {error_count}'
        ))
