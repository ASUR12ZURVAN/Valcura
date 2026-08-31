from django.core.management.base import BaseCommand
from django.utils import timezone
from user_request.patient_automation import PatientAutomationService
from user_request.database_automation import DatabaseAutomationService


class Command(BaseCommand):
    help = 'Run automated patient communication workflows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['followups', 'reminders', 'sync', 'all'],
            default='all',
            help='Type of automation to run'
        )
        parser.add_argument(
            '--data-source',
            type=str,
            choices=['database', 'sheets', 'both'],
            default='database',
            help='Data source for automation (database, sheets, or both)'
        )

    def handle(self, *args, **options):
        automation_type = options['type']
        data_source = options['data_source']
        
        self.stdout.write(f'Starting automation: {automation_type}')
        self.stdout.write(f'Data source: {data_source}')
        self.stdout.write(f'Time: {timezone.now()}')

        if data_source in ['database', 'both']:
            db_service = DatabaseAutomationService()
            self.stdout.write('\n=== Using Database Data Source ===')
            self._run_automation(db_service, automation_type, 'database')

        if data_source in ['sheets', 'both']:
            sheets_service = PatientAutomationService()
            self.stdout.write('\n=== Using Google Sheets Data Source ===')
            self._run_automation(sheets_service, automation_type, 'sheets')

        self.stdout.write(self.style.SUCCESS('\n=== Automation Complete ==='))

    def _run_automation(self, service, automation_type, source_name):
        """Run automation for a specific service."""
        if automation_type in ['followups', 'all']:
            self.stdout.write(f'\n=== Processing Follow-ups ({source_name}) ===')
            
            if source_name == 'database':
                results = service.process_opportunity_followups()
                entity_name = 'opportunities'
                entity_results = 'opportunity_results'
            else:
                results = service.process_patient_followups()
                entity_name = 'patients'
                entity_results = 'patient_results'
            
            if results['success']:
                self.stdout.write(self.style.SUCCESS(
                    f"Processed {results[f'{entity_name}_processed']} {entity_name}, "
                    f"sent {results['messages_sent']} messages"
                ))
                
                for result in results[entity_results]:
                    if result['message_sent']:
                        self.stdout.write(
                            f"✓ Sent to {result['phone_number']} "
                            f"({result['template_used']})"
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"✗ Failed for {result['phone_number']}: "
                                f"{result['error']}"
                            )
                        )
                
                if results['errors']:
                    self.stdout.write(self.style.ERROR(f"\nErrors: {len(results['errors']}"))
                    for error in results['errors']:
                        self.stdout.write(self.style.ERROR(f"  - {error}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed: {results['message']}"))

        if automation_type in ['reminders', 'all']:
            self.stdout.write(f'\n=== Processing Appointment Reminders ({source_name}) ===')
            results = service.process_appointment_reminders()
            
            if results['success']:
                self.stdout.write(self.style.SUCCESS(
                    f"Sent {results['reminders_sent']} appointment reminders"
                ))
                
                for reminder_result in results['opportunity_results']:
                    if reminder_result['message_sent']:
                        self.stdout.write(
                            f"✓ {reminder_result['reminder_type']} sent to "
                            f"{reminder_result['phone_number']}"
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"✗ Failed {reminder_result['reminder_type']} for "
                                f"{reminder_result['phone_number']}: {reminder_result['error']}"
                            )
                        )
            else:
                self.stdout.write(self.style.ERROR(f"Failed: {results['message']}"))

        if automation_type in ['sync', 'all'] and source_name == 'sheets':
            self.stdout.write('\n=== Syncing Workflow State to Sheets ===')
            results = service.sync_workflow_state_to_sheets()
            
            if results['success']:
                self.stdout.write(self.style.SUCCESS(
                    f"Synced {results['synced_count']} workflow states"
                ))
                
                if results['errors']:
                    self.stdout.write(self.style.ERROR(f"\nSync errors: {len(results['errors']}"))
                    for error in results['errors']:
                        self.stdout.write(self.style.ERROR(f"  - {error}"))
            else:
                self.stdout.write(self.style.ERROR(f"Sync failed"))
