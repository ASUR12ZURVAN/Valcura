from django.core.management.base import BaseCommand
from user_request.excel_importer import ExcelImporterService


class Command(BaseCommand):
    help = 'Import data from Valcura Master Revenue Intelligence Database Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--excel-file',
            type=str,
            help='Path to the Excel file (default: Valcura - Master Revenue Intelligence Database.xlsx)'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            choices=['all', 'Clinic_Profile', 'Team_Master', 'Patient_Contact', 'Opportunities', 
                     'Interaction_Log', 'Treatment_Config', 'System_Config', 'Monthly_Metrics'],
            default='all',
            help='Specific sheet to import (default: all)'
        )

    def handle(self, *args, **options):
        excel_file = options.get('excel_file')
        sheet = options['sheet']

        self.stdout.write('Starting Excel import...')
        
        try:
            importer = ExcelImporterService(excel_file)
            
            if sheet == 'all':
                results = importer.import_all_sheets()
                
                if results['success']:
                    self.stdout.write(self.style.SUCCESS('Excel import completed successfully'))
                    
                    for sheet_name, counts in results['imported'].items():
                        self.stdout.write(
                            f"{sheet_name}: "
                            f"Imported {counts['imported']}, Updated {counts['updated']}"
                        )
                else:
                    self.stdout.write(self.style.ERROR('Excel import failed'))
                    for error in results['errors']:
                        self.stdout.write(self.style.ERROR(f"  - {error}"))
            else:
                importer.load_workbook()
                # Map sheet names to method names
                sheet_method_map = {
                    'Clinic_Profile': 'import_clinic_profile',
                    'Team_Master': 'import_team_master',
                    'Patient_Contact': 'import_patient_contact',
                    'Opportunities': 'import_opportunities',
                    'Interaction_Log': 'import_interaction_log',
                    'Treatment_Config': 'import_treatment_config',
                    'System_Config': 'import_system_config',
                    'Monthly_Metrics': 'import_monthly_metrics',
                }
                method_name = sheet_method_map.get(sheet, f'import_{sheet.lower()}')
                import_method = getattr(importer, method_name)
                counts = import_method()
                
                self.stdout.write(self.style.SUCCESS(f'{sheet} import completed'))
                self.stdout.write(f"Imported {counts['imported']}, Updated {counts['updated']}")
                
        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import failed: {str(e)}'))
            import traceback
            traceback.print_exc()
