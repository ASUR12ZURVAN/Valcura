import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .workflow_service import WorkflowOrchestrator
from .services import WhatsAppService, TemplateService
from .models import (
    PatientContact, Opportunity, InteractionLog, 
    TreatmentConfig, SystemConfig, ClinicProfile, TeamMaster
)


class DatabaseAutomationService:
    """
    Automated patient communication service that uses the database 
    (Opportunities, Interaction_Log) instead of Google Sheets for patient data.
    """

    def __init__(self):
        self.workflow_orchestrator = WorkflowOrchestrator()
        self.whatsapp_service = WhatsAppService()
        self.template_service = TemplateService()

    def process_opportunity_followups(self) -> Dict[str, Any]:
        """
        Process all opportunities requiring follow-up based on database data.
        Returns summary of actions taken.
        """
        # Get opportunities requiring follow-up
        now = timezone.now()
        followup_opportunities = Opportunity.objects.filter(
            Q(opportunity_status__in=['New', 'Inquiry', 'Consultation_Scheduled', 'Treatment_Discussed']) |
            Q(
                next_followup_date_time__lte=now,
                opportunity_status__in=['Active', 'Follow_Up_Required']
            )
        ).select_related('patient', 'clinic', 'doctor')

        results = {
            'success': True,
            'message': f'Processing {len(followup_opportunities)} opportunities requiring follow-up',
            'opportunities_processed': 0,
            'messages_sent': 0,
            'errors': [],
            'opportunity_results': []
        }

        for opportunity in followup_opportunities:
            try:
                opportunity_result = self._process_single_opportunity(opportunity)
                results['opportunity_results'].append(opportunity_result)
                results['opportunities_processed'] += 1
                if opportunity_result['message_sent']:
                    results['messages_sent'] += 1
                else:
                    results['errors'].append(opportunity_result['error'])
            except Exception as e:
                results['errors'].append(f"Error processing opportunity {opportunity.opportunity_id}: {str(e)}")

        return results

    def _process_single_opportunity(self, opportunity: Opportunity) -> Dict[str, Any]:
        """
        Process a single opportunity based on its status and data.
        """
        patient = opportunity.patient
        phone_number = patient.phone_number
        status = opportunity.opportunity_status
        treatment = opportunity.treatment_advised or opportunity.treatment_concern
        objection = opportunity.current_objection or opportunity.initial_objection
        patient_name = patient.patient_name
        
        result = {
            'opportunity_id': opportunity.opportunity_id,
            'phone_number': phone_number,
            'patient_name': patient_name,
            'status': status,
            'message_sent': False,
            'template_used': None,
            'error': None
        }

        try:
            # Determine the appropriate action based on opportunity status
            if status in ['New', 'Inquiry']:
                # Send initial engagement message
                workflow_result = self.workflow_orchestrator.process_event(
                    phone_number=phone_number,
                    is_missed_call=False,
                    treatment=treatment
                )
            elif status == 'Consultation_Scheduled':
                # Send consultation reminder
                workflow_result = self.workflow_orchestrator.process_event(
                    phone_number=phone_number,
                    appointment_booked=False,
                    treatment=treatment
                )
            elif status == 'Treatment_Discussed':
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
            elif opportunity.next_followup_date_time and opportunity.next_followup_date_time <= timezone.now():
                # Follow up based on scheduled follow-up time
                days_since_last = (timezone.now() - opportunity.last_interaction_date_time).days if opportunity.last_interaction_date_time else 0
                if days_since_last >= 7:
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
                variables = self._prepare_opportunity_variables(opportunity, template)
                
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
                    
                    # Log the interaction
                    self._log_interaction(
                        opportunity=opportunity,
                        interaction_type='WhatsApp Message',
                        outcome='Sent',
                        sequence_name=template['library'],
                        message_variant_id=template['template_id'],
                        call_objective=template['objective']
                    )
                    
                    # Update opportunity status
                    opportunity.last_interaction_date_time = timezone.now()
                    if opportunity.next_followup_date_time:
                        opportunity.next_followup_date_time = self._calculate_next_followup(
                            opportunity, template
                        )
                    opportunity.save()
                else:
                    result['error'] = "WhatsApp message failed to send"
            else:
                result['error'] = workflow_result.get('message', 'Workflow processing failed')

        except Exception as e:
            result['error'] = f"Processing error: {str(e)}"

        return result

    def _prepare_opportunity_variables(self, opportunity: Opportunity, template: Dict[str, Any]) -> Dict[str, str]:
        """
        Prepare variable mapping for template rendering based on opportunity data.
        """
        patient = opportunity.patient
        clinic = opportunity.clinic
        doctor = opportunity.doctor
        
        variables = {}
        
        # Common variable mappings
        variable_map = {
            '1': patient.patient_name,
            '2': doctor.staff_name if doctor else 'Doctor',
            '3': patient.phone_number,
            '4': clinic.clinic_name,
            '5': opportunity.treatment_advised or opportunity.treatment_concern or 'treatment',
            '6': opportunity.current_objection or opportunity.initial_objection or 'your concern',
            '7': opportunity.why_treatment_advised or 'Treatment details',
            '8': opportunity.treatment_concern or 'Your concern',
            '9': 'Next steps for treatment',
            '10': opportunity.appointment_date_time.strftime('%Y-%m-%d') if opportunity.appointment_date_time else 'appointment date',
            '11': opportunity.appointment_date_time.strftime('%H:%M') if opportunity.appointment_date_time else 'appointment time',
            '16': f"{clinic.locality}, {clinic.city}",
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

    def _log_interaction(self, opportunity: Opportunity, interaction_type: str, 
                        outcome: str, sequence_name: str = None, 
                        message_variant_id: str = None, call_objective: str = None):
        """Create an InteractionLog entry for the communication."""
        interaction_id = f"INT-{timezone.now().strftime('%Y%m%d%H%M%S')}-{opportunity.opportunity_id}"
        
        InteractionLog.objects.create(
            interaction_id=interaction_id,
            opportunity=opportunity,
            patient=opportunity.patient,
            clinic=opportunity.clinic,
            event_date_time=timezone.now(),
            channel='WhatsApp',
            direction='Outbound',
            interaction_type=interaction_type,
            sequence_name=sequence_name,
            message_variant_id=message_variant_id,
            call_objective=call_objective,
            outcome=outcome,
            delivery_status='Sent'
        )

    def _calculate_next_followup(self, opportunity: Opportunity, template: Dict[str, Any]) -> datetime:
        """Calculate next follow-up date based on template and opportunity data."""
        # Get treatment config for default follow-up track
        treatment_config = TreatmentConfig.objects.filter(
            clinic=opportunity.clinic,
            treatment=opportunity.treatment_advised
        ).first()
        
        if treatment_config:
            followup_track = treatment_config.followup_track
        else:
            followup_track = 'standard'
        
        # Calculate based on follow-up track
        if followup_track == 'aggressive':
            return timezone.now() + timedelta(days=1)
        elif followup_track == 'standard':
            return timezone.now() + timedelta(days=3)
        elif followup_track == 'conservative':
            return timezone.now() + timedelta(days=7)
        else:
            return timezone.now() + timedelta(days=3)

    def process_appointment_reminders(self) -> Dict[str, Any]:
        """
        Process appointment reminders for patients with upcoming appointments.
        """
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        in_6_hours = now + timedelta(hours=6)

        # Get opportunities with appointments tomorrow or today
        upcoming_appointments = Opportunity.objects.filter(
            appointment_date_time__date__in=[tomorrow.date(), now.date()],
            opportunity_status__in=['Consultation_Scheduled', 'Appointment_Confirmed']
        ).select_related('patient', 'clinic', 'doctor')

        results = {
            'success': True,
            'message': 'Processing appointment reminders',
            'reminders_sent': 0,
            'opportunity_results': []
        }

        for opportunity in upcoming_appointments:
            appointment_date = opportunity.appointment_date_time
            
            # Check if appointment is tomorrow (24-hour reminder)
            if appointment_date.date() == tomorrow.date():
                reminder_result = self._send_reminder(
                    opportunity,
                    '24_hour_reminder',
                    appointment_date
                )
                results['opportunity_results'].append(reminder_result)
                if reminder_result['message_sent']:
                    results['reminders_sent'] += 1

            # Check if appointment is today (6-hour reminder)
            elif appointment_date.date() == now.date():
                reminder_result = self._send_reminder(
                    opportunity,
                    '6_hour_reminder',
                    appointment_date
                )
                results['opportunity_results'].append(reminder_result)
                if reminder_result['message_sent']:
                    results['reminders_sent'] += 1

        return results

    def _send_reminder(self, opportunity: Opportunity, reminder_type: str, appointment_date: datetime) -> Dict[str, Any]:
        """Send appointment reminder to patient."""
        patient = opportunity.patient
        phone_number = patient.phone_number
        
        result = {
            'opportunity_id': opportunity.opportunity_id,
            'phone_number': phone_number,
            'reminder_type': reminder_type,
            'message_sent': False,
            'error': None
        }

        try:
            # Get appropriate reminder template from System_Config
            system_config = SystemConfig.objects.filter(
                config_type='Reminder',
                code=reminder_type,
                active_status=True
            ).first()

            if not system_config:
                # Fallback to template ID
                if reminder_type == '24_hour_reminder':
                    template = self.template_service.get_template('UTL-L3-02')
                else:
                    template = self.template_service.get_template('UTL-L3-03')
            else:
                template = self.template_service.get_template(system_config.meta_template_name)

            if not template:
                result['error'] = f"Template not found for {reminder_type}"
                return result

            # Prepare variables
            variables = self._prepare_opportunity_variables(opportunity, template)
            variables['10'] = appointment_date.strftime('%Y-%m-%d')
            variables['11'] = appointment_date.strftime('%H:%M')

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
                
                # Log the reminder interaction
                self._log_interaction(
                    opportunity=opportunity,
                    interaction_type='Appointment Reminder',
                    outcome='Sent',
                    sequence_name='Reminder',
                    message_variant_id=template['template_id'],
                    call_objective=f'{reminder_type} for {appointment_date}'
                )
            else:
                result['error'] = "WhatsApp message failed to send"

        except Exception as e:
            result['error'] = f"Reminder error: {str(e)}"

        return result

    def handle_incoming_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Handle incoming WhatsApp message from a patient.
        """
        # Find patient by phone number
        patient = PatientContact.objects.filter(phone_number=phone_number).first()
        
        if patient:
            # Get active opportunity for this patient
            opportunity = Opportunity.objects.filter(
                patient=patient,
                opportunity_status__in=['New', 'Inquiry', 'Active', 'Follow_Up_Required']
            ).order_by('-inquiry_date_time').first()
            
            if opportunity:
                treatment = opportunity.treatment_advised or opportunity.treatment_concern
                objection = opportunity.current_objection or opportunity.initial_objection
                
                workflow_result = self.workflow_orchestrator.process_event(
                    phone_number=phone_number,
                    user_message=message,
                    treatment=treatment,
                    objection=objection
                )
            else:
                workflow_result = self.workflow_orchestrator.process_event(
                    phone_number=phone_number,
                    user_message=message
                )
        else:
            # Process without patient context
            workflow_result = self.workflow_orchestrator.process_event(
                phone_number=phone_number,
                user_message=message
            )

        if workflow_result['success']:
            template = workflow_result['template']
            
            if patient:
                opportunity = Opportunity.objects.filter(
                    patient=patient
                ).order_by('-inquiry_date_time').first()
                variables = self._prepare_opportunity_variables(
                    opportunity, template
                ) if opportunity else {}
            else:
                variables = {}
            
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

            # Log the interaction if patient exists
            if patient and opportunity:
                self._log_interaction(
                    opportunity=opportunity,
                    interaction_type='WhatsApp Message',
                    outcome='Response Sent',
                    sequence_name=template['library'],
                    message_variant_id=template['template_id'],
                    call_objective='Response to patient message'
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

    def get_template_from_system_config(self, config_type: str, code: str, 
                                       treatment: str = None, objection: str = None) -> Optional[str]:
        """
        Get template name from System_Config based on parameters.
        """
        query = Q(config_type=config_type, code=code, active_status=True)
        
        if treatment:
            query &= Q(treatment=treatment)
        if objection:
            query &= Q(objection=objection)
        
        config = SystemConfig.objects.filter(query).first()
        return config.meta_template_name if config else None
