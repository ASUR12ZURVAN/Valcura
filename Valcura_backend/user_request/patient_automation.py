import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from .google_sheets_service import GoogleSheetsService
from .workflow_service import WorkflowOrchestrator, WorkflowService
from .services import WhatsAppService, TemplateService
from .models import WorkflowState


class PatientAutomationService:
    """
    Automated patient communication service that integrates Google Sheets patient data
    with the template workflow system to send automated WhatsApp messages.
    """

    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.workflow_orchestrator = WorkflowOrchestrator()
        self.whatsapp_service = WhatsAppService()
        self.template_service = TemplateService()

    def process_patient_followups(self) -> Dict[str, Any]:
        """
        Process all patients requiring follow-up based on Google Sheets data.
        Returns summary of actions taken.
        """
        # Get patients requiring follow-up
        success, patients, message = self.sheets_service.get_patients_requiring_followup()
        
        if not success:
            return {
                'success': False,
                'message': message,
                'patients_processed': 0,
                'messages_sent': 0,
                'errors': []
            }

        results = {
            'success': True,
            'message': f'Processing {len(patients)} patients requiring follow-up',
            'patients_processed': 0,
            'messages_sent': 0,
            'errors': [],
            'patient_results': []
        }

        for patient in patients:
            try:
                patient_result = self._process_single_patient(patient)
                results['patient_results'].append(patient_result)
                results['patients_processed'] += 1
                if patient_result['message_sent']:
                    results['messages_sent'] += 1
                else:
                    results['errors'].append(patient_result['error'])
            except Exception as e:
                results['errors'].append(f"Error processing patient {patient.get('phone_number')}: {str(e)}")

        return results

    def _process_single_patient(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single patient based on their status and data.
        Returns result dict with message_sent status.
        """
        phone_number = patient.get('phone_number', '')
        status = patient.get('status', '').lower()
        treatment = patient.get('treatment', '')
        objection = patient.get('objection', '')
        patient_name = patient.get('patient_name', '')
        
        result = {
            'phone_number': phone_number,
            'patient_name': patient_name,
            'status': status,
            'message_sent': False,
            'template_used': None,
            'error': None
        }

        try:
            # Determine the appropriate action based on patient status
            if status in ['new', 'inquiry']:
                # Send initial engagement message
                workflow_result = self.workflow_orchestrator.process_event(
                    phone_number=phone_number,
                    is_missed_call=False,
                    treatment=treatment
                )
            elif status == 'consultation_scheduled':
                # Send consultation reminder
                workflow_result = self.workflow_orchestrator.process_event(
                    phone_number=phone_number,
                    appointment_booked=False,
                    treatment=treatment
                )
            elif status == 'treatment_discussed':
                # Handle potential objections
                if objection:
                    workflow_result = self.workflow_orchestrator.process_event(
                        phone_number=phone_number,
                        user_message=f"Patient has {objection} concern",
                        treatment=treatment,
                        objection=objection
                    )
                else:
                    workflow_result = self.workflow_orchestrator.process_event(
                        phone_number=phone_number,
                        treatment=treatment
                    )
            elif 'days_since_contact' in patient:
                # Follow up based on days since last contact
                days = patient['days_since_contact']
                if days >= 7:
                    # Long-term follow-up
                    workflow_result = self.workflow_orchestrator.process_event(
                        phone_number=phone_number,
                        user_message="Follow up after extended period",
                        treatment=treatment
                    )
                else:
                    # Regular follow-up
                    workflow_result = self.workflow_orchestrator.process_event(
                        phone_number=phone_number,
                        treatment=treatment
                    )
            else:
                result['error'] = f"No specific action for status: {status}"
                return result

            if workflow_result['success']:
                # Send the WhatsApp message
                template = workflow_result['template']
                variables = self._prepare_patient_variables(patient, template)
                
                # Render the message
                message_body = self.template_service.get_message(
                    template['template_id'],
                    variables
                )
                
                # Send via WhatsApp
                message_sent = self.whatsapp_service.send_message(
                    to_number=phone_number,
                    message=message_body,
                    template_name=template['meta_template_name'],
                    template_variables=self.template_service.meta_variables(
                        template['template_id'],
                        variables
                    ),
                    template_components=self.template_service.meta_components(
                        template['template_id']
                    )
                )

                if message_sent:
                    result['message_sent'] = True
                    result['template_used'] = template['template_id']
                    
                    # Update patient status in Google Sheets
                    self.sheets_service.update_patient_status(
                        phone_number,
                        f"followed_up_{datetime.now().strftime('%Y%m%d')}",
                        f"Sent template: {template['template_id']}"
                    )
                else:
                    result['error'] = "WhatsApp message failed to send"
            else:
                result['error'] = workflow_result.get('message', 'Workflow processing failed')

        except Exception as e:
            result['error'] = f"Processing error: {str(e)}"

        return result

    def _prepare_patient_variables(self, patient: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, str]:
        """
        Prepare variable mapping for template rendering based on patient data.
        """
        variables = {}
        
        # Common variable mappings (based on template structure)
        # These should match the variable_mapping in your templates
        variable_map = {
            '1': patient.get('patient_name', 'Patient'),
            '2': patient.get('doctor_name', 'Doctor'),
            '3': patient.get('phone_number', ''),
            '4': patient.get('clinic_name', 'Our Clinic'),
            '5': patient.get('treatment', 'treatment'),
            '6': patient.get('concern', 'your concern'),
            '7': patient.get('visit_highlights', 'Visit details'),
            '8': patient.get('treatment_explanation', 'Treatment explanation'),
            '9': patient.get('next_steps', 'Next steps'),
            '10': patient.get('appointment_date', 'appointment date'),
            '11': patient.get('appointment_time', 'appointment time'),
            '16': patient.get('location_link', 'clinic location'),
        }

        # Get required variables from template
        required_vars = self.template_service.required_variables(template['template_id'])
        
        # Map variables based on template requirements
        for var_num in required_vars:
            if var_num in variable_map:
                variables[var_num] = variable_map[var_num]
            else:
                variables[var_num] = f"[{var_num}]"  # Fallback placeholder

        return variables

    def process_appointment_reminders(self) -> Dict[str, Any]:
        """
        Process appointment reminders for patients with upcoming appointments.
        """
        success, patients, message = self.sheets_service.read_patient_status()
        
        if not success:
            return {'success': False, 'message': message}

        results = {
            'success': True,
            'message': 'Processing appointment reminders',
            'reminders_sent': 0,
            'patient_results': []
        }

        today = timezone.now()
        tomorrow = today + timedelta(days=1)
        in_6_hours = today + timedelta(hours=6)

        for patient in patients:
            appointment_date_str = patient.get('appointment_date', '')
            if not appointment_date_str:
                continue

            try:
                # Parse appointment date (assuming format YYYY-MM-DD)
                appointment_date = datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
                
                # Check if appointment is tomorrow (24-hour reminder)
                if appointment_date == tomorrow.date():
                    reminder_result = self._send_reminder(
                        patient,
                        '24_hour_reminder',
                        appointment_date_str
                    )
                    results['patient_results'].append(reminder_result)
                    if reminder_result['message_sent']:
                        results['reminders_sent'] += 1

                # Check if appointment is today (6-hour reminder)
                elif appointment_date == today.date():
                    reminder_result = self._send_reminder(
                        patient,
                        '6_hour_reminder',
                        appointment_date_str
                    )
                    results['patient_results'].append(reminder_result)
                    if reminder_result['message_sent']:
                        results['reminders_sent'] += 1

            except ValueError:
                continue

        return results

    def _send_reminder(self, patient: Dict[str, Any], reminder_type: str, appointment_date: str) -> Dict[str, Any]:
        """
        Send appointment reminder to patient.
        """
        phone_number = patient.get('phone_number', '')
        
        result = {
            'phone_number': phone_number,
            'reminder_type': reminder_type,
            'message_sent': False,
            'error': None
        }

        try:
            # Get appropriate reminder template
            if reminder_type == '24_hour_reminder':
                template = self.template_service.get_template('UTL-L3-02')
            else:
                template = self.template_service.get_template('UTL-L3-03')

            if not template:
                result['error'] = f"Template not found for {reminder_type}"
                return result

            # Prepare variables
            variables = self._prepare_patient_variables(patient, template)
            variables['10'] = appointment_date  # Appointment date
            variables['11'] = patient.get('appointment_time', 'your appointment time')

            # Render and send message
            message_body = self.template_service.get_message(
                template['template_id'],
                variables
            )

            message_sent = self.whatsapp_service.send_message(
                to_number=phone_number,
                message=message_body,
                template_name=template['meta_template_name'],
                template_variables=self.template_service.meta_variables(
                    template['template_id'],
                    variables
                )
            )

            if message_sent:
                result['message_sent'] = True
            else:
                result['error'] = "WhatsApp message failed to send"

        except Exception as e:
            result['error'] = f"Reminder error: {str(e)}"

        return result

    def handle_incoming_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Handle incoming WhatsApp message from a patient.
        """
        # Get patient data from Google Sheets
        success, patient, patient_message = self.sheets_service.get_patient_by_phone(phone_number)
        
        if success:
            # Process through workflow with patient context
            treatment = patient.get('treatment', '') if patient else ''
            objection = patient.get('objection', '') if patient else ''
            
            workflow_result = self.workflow_orchestrator.process_event(
                phone_number=phone_number,
                user_message=message,
                treatment=treatment,
                objection=objection
            )
        else:
            # Process without patient context
            workflow_result = self.workflow_orchestrator.process_event(
                phone_number=phone_number,
                user_message=message
            )

        if workflow_result['success']:
            template = workflow_result['template']
            variables = self._prepare_patient_variables(
                patient if success else {},
                template
            )
            
            message_body = self.template_service.get_message(
                template['template_id'],
                variables
            )

            message_sent = self.whatsapp_service.send_message(
                to_number=phone_number,
                message=message_body,
                template_name=template['meta_template_name'],
                template_variables=self.template_service.meta_variables(
                    template['template_id'],
                    variables
                )
            )

            return {
                'success': message_sent,
                'message': 'Response sent successfully' if message_sent else 'Failed to send response',
                'template_used': template['template_id'] if message_sent else None
            }
        else:
            return {
                'success': False,
                'message': workflow_result.get('message', 'Workflow processing failed')
            }

    def sync_workflow_state_to_sheets(self) -> Dict[str, Any]:
        """
        Sync local workflow state to Google Sheets for visibility.
        """
        active_states = WorkflowState.objects.all()
        
        results = {
            'success': True,
            'synced_count': 0,
            'errors': []
        }

        for state in active_states:
            try:
                notes = f"Workflow: Library {state.current_library}, Step {state.current_step}, Last template: {state.last_template_id}"
                success, message = self.sheets_service.update_patient_status(
                    state.phone_number,
                    state.current_library,
                    notes
                )
                
                if success:
                    results['synced_count'] += 1
                else:
                    results['errors'].append(f"{state.phone_number}: {message}")
                    
            except Exception as e:
                results['errors'].append(f"{state.phone_number}: {str(e)}")

        return results
