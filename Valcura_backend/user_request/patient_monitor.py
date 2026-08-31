import os
import time
import threading
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.management import call_command
from .patient_automation import PatientAutomationService


class PatientMonitorService:
    """
    Background monitoring service that continuously checks patient status
    and triggers automated communications based on schedules and conditions.
    """

    def __init__(self, check_interval_minutes: int = 30):
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.automation_service = PatientAutomationService()
        self.running = False
        self.monitor_thread = None

    def start_monitoring(self):
        """Start the background monitoring service."""
        if self.running:
            print("Monitoring service is already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"Patient monitoring service started (checking every {self.check_interval/60} minutes)")

    def stop_monitoring(self):
        """Stop the background monitoring service."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        print("Patient monitoring service stopped")

    def _monitor_loop(self):
        """Main monitoring loop that runs in background thread."""
        while self.running:
            try:
                print(f"\n[{datetime.now()}] Running patient monitoring cycle...")
                
                # Run different types of checks
                self._check_followup_schedule()
                self._check_appointment_reminders()
                self._check_workflow_sync()
                
                print(f"[{datetime.now()}] Monitoring cycle completed")
                
                # Wait for next cycle
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"[{datetime.now()}] Error in monitoring cycle: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying on error

    def _check_followup_schedule(self):
        """Check and process patient follow-ups based on schedule."""
        current_hour = datetime.now().hour
        
        # Only process follow-ups during business hours (9 AM - 6 PM)
        if 9 <= current_hour < 18:
            print("Processing scheduled follow-ups...")
            results = self.automation_service.process_patient_followups()
            print(f"Follow-up results: {results['patients_processed']} processed, {results['messages_sent']} sent")

    def _check_appointment_reminders(self):
        """Check and send appointment reminders."""
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        # Check for 24-hour reminders at 9 AM
        if current_hour == 9 and current_minute == 0:
            print("Processing 24-hour appointment reminders...")
            results = self.automation_service.process_appointment_reminders()
            print(f"Reminder results: {results['reminders_sent']} reminders sent")
        
        # Check for 6-hour reminders throughout the day
        elif current_hour in [8, 9, 10, 11, 12, 13, 14, 15, 16] and current_minute == 0:
            print("Processing 6-hour appointment reminders...")
            results = self.automation_service.process_appointment_reminders()
            print(f"Reminder results: {results['reminders_sent']} reminders sent")

    def _check_workflow_sync(self):
        """Sync workflow state to Google Sheets periodically."""
        current_hour = datetime.now().hour
        
        # Sync every 6 hours
        if current_hour % 6 == 0:
            print("Syncing workflow state to Google Sheets...")
            results = self.automation_service.sync_workflow_state_to_sheets()
            print(f"Sync results: {results['synced_count']} states synced")

    def run_manual_check(self, check_type: str = 'all'):
        """Run a manual check of a specific type."""
        print(f"Running manual check: {check_type}")
        
        if check_type == 'followups':
            results = self.automation_service.process_patient_followups()
        elif check_type == 'reminders':
            results = self.automation_service.process_appointment_reminders()
        elif check_type == 'sync':
            results = self.automation_service.sync_workflow_state_to_sheets()
        elif check_type == 'all':
            results = {
                'followups': self.automation_service.process_patient_followups(),
                'reminders': self.automation_service.process_appointment_reminders(),
                'sync': self.automation_service.sync_workflow_state_to_sheets()
            }
        else:
            print(f"Unknown check type: {check_type}")
            return
        
        print(f"Manual check completed: {results}")
        return results


class ScheduledTaskRunner:
    """
    Utility class for running scheduled tasks using Django management commands.
    Can be integrated with cron jobs or task schedulers.
    """

    @staticmethod
    def run_followup_tasks():
        """Run follow-up automation tasks."""
        print(f"[{datetime.now()}] Running follow-up tasks...")
        call_command('run_automation', type='followups')

    @staticmethod
    def run_reminder_tasks():
        """Run appointment reminder tasks."""
        print(f"[{datetime.now()}] Running reminder tasks...")
        call_command('run_automation', type='reminders')

    @staticmethod
    def run_sync_tasks():
        """Run workflow sync tasks."""
        print(f"[{datetime.now()}] Running sync tasks...")
        call_command('run_automation', type='sync')

    @staticmethod
    def run_all_tasks():
        """Run all automation tasks."""
        print(f"[{datetime.now()}] Running all automation tasks...")
        call_command('run_automation', type='all')


# Global monitor instance
_monitor_instance = None

def get_monitor_service(check_interval_minutes: int = 30) -> PatientMonitorService:
    """Get or create the global monitor service instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PatientMonitorService(check_interval_minutes)
    return _monitor_instance
