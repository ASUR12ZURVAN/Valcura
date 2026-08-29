from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from django.utils import timezone
from .models import WorkflowState, MetaTemplate
from .template_cache import TemplateCacheService


class WorkflowService:
    """
    Implements the Cause -> Reason -> Response workflow for patient communication.
    
    Cause: The trigger event (e.g., missed call, appointment booked, no response)
    Reason: The objective/context (e.g., treatment type, objection type, library context)
    Response: The appropriate template message based on the cause and reason
    """
    
    @staticmethod
    def analyze_cause(user_message: str, is_missed_call: bool = False, 
                     appointment_booked: bool = False) -> Dict[str, Any]:
        """
        Analyze the cause based on user interaction or system event.
        Returns structured cause information.
        """
        cause = {
            'trigger': '',
            'category': '',
            'is_missed_call': is_missed_call,
            'appointment_booked': appointment_booked,
            'timestamp': timezone.now(),
        }
        
        if is_missed_call:
            cause['trigger'] = 'Missed Call'
            cause['category'] = 'Utility'
        elif appointment_booked:
            cause['trigger'] = 'Appointment Booked'
            cause['category'] = 'Utility'
        elif user_message:
            # Analyze user message for intent
            user_message_lower = user_message.lower()
            
            if any(word in user_message_lower for word in ['cost', 'price', 'expensive', 'afford']):
                cause['trigger'] = 'Primary Objection = Cost'
                cause['category'] = 'Marketing'
            elif any(word in user_message_lower for word in ['trust', 'sure', 'necessary', 'really need']):
                cause['trigger'] = 'Primary Objection = Trust'
                cause['category'] = 'Marketing'
            elif any(word in user_message_lower for word in ['pain', 'hurt', 'scared', 'afraid', 'nervous']):
                cause['trigger'] = 'Primary Objection = Fear'
                cause['category'] = 'Marketing'
            elif any(word in user_message_lower for word in ['wait', 'later', 'not urgent', 'no hurry']):
                cause['trigger'] = 'Primary Objection = No Urgency'
                cause['category'] = 'Marketing'
            elif any(word in user_message_lower for word in ['yes', 'sure', 'okay', 'confirm']):
                cause['trigger'] = 'Patient Replied "Yes"'
                cause['category'] = 'Utility'
            else:
                cause['trigger'] = 'No Response'
                cause['category'] = 'Marketing'
        
        return cause
    
    @staticmethod
    def determine_reason(phone_number: str, cause: Dict[str, Any], 
                        treatment: str = None, objection: str = None, user_message: str = None) -> Dict[str, Any]:
        """
        Determine the reason/context based on workflow state and cause.
        Returns structured reason information.
        """
        workflow_state = WorkflowState.objects.filter(phone_number=phone_number).first()
        user_message_lower = user_message.lower() if user_message else ''
        
        reason = {
            'library': '',
            'treatment': treatment or '',
            'objection': objection or '',
            'day_offset': 0,
            'objective': '',
            'current_step': 0,
        }
        
        if workflow_state:
            reason['library'] = workflow_state.current_library
            reason['treatment'] = workflow_state.treatment or treatment or ''
            reason['objection'] = workflow_state.objection or objection or ''
            reason['current_step'] = workflow_state.current_step
            
            # Calculate day offset based on last message date
            if workflow_state.last_message_date:
                days_since = (timezone.now() - workflow_state.last_message_date).days
                reason['day_offset'] = days_since
        else:
            # Initialize workflow state for new patient
            if cause['trigger'] == 'Missed Call':
                reason['library'] = 'Library 1'
                reason['objective'] = 'Recover the missed inquiry while making the patient feel acknowledged and valued'
            elif cause['trigger'] == 'Call Completed – No Appointment':
                reason['library'] = 'Library 2'
                reason['objective'] = 'Build confidence in the clinic and doctor'
            elif cause['trigger'] == 'Appointment Booked':
                reason['library'] = 'Library 3'
                reason['objective'] = 'Confirm appointment and provide complete visit details'
            elif cause['trigger'] == 'Consultation Completed':
                reason['library'] = 'Library 4'
                reason['objective'] = 'Obtain patient consent before sending the personalized Visit Summary'
            elif 'Objection' in cause['trigger'] or any(word in user_message_lower for word in ['cost', 'price', 'expensive', 'afford', 'trust', 'sure', 'necessary', 'pain', 'hurt', 'scared', 'afraid', 'wait', 'later', 'not urgent']):
                reason['library'] = 'Library 5'
                reason['objection'] = cause['trigger'].replace('Primary Objection = ', '') if 'Objection' in cause['trigger'] else ''
                reason['treatment'] = treatment or 'Root Canal Treatment'
                reason['objective'] = f'Address objection for {reason["treatment"]}'
        
        return reason
    
    @staticmethod
    def get_response(phone_number: str, cause: Dict[str, Any], 
                     reason: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get the appropriate response template based on cause and reason.
        """
        # Build query parameters
        query_params = {
            'library': reason['library'],
            'trigger': cause['trigger'],
        }
        
        if reason['treatment']:
            query_params['treatment'] = reason['treatment']
        if reason['objection']:
            query_params['objection'] = reason['objection']
        
        # Use cache service to find template
        template = TemplateCacheService.find_template_by_situation(
            library=query_params['library'],
            trigger=query_params['trigger'],
            treatment=query_params.get('treatment'),
            objection=query_params.get('objection')
        )
        
        if template:
            return {
                'template': template,
                'cause': cause,
                'reason': reason,
                'variables_needed': WorkflowService._extract_variables(template['meta_approved_body']),
            }
        
        # Fallback: try to find template by library and trigger only
        template = TemplateCacheService.find_template_by_situation(
            library=query_params['library'],
            trigger=query_params['trigger']
        )
        
        if template:
            return {
                'template': template,
                'cause': cause,
                'reason': reason,
                'variables_needed': WorkflowService._extract_variables(template['meta_approved_body']),
            }
        
        return None
    
    @staticmethod
    def update_workflow_state(phone_number: str, template_id: str, 
                              cause: Dict[str, Any], reason: Dict[str, Any],
                              metadata: Dict[str, Any] = None) -> WorkflowState:
        """
        Update workflow state after sending a message.
        """
        workflow_state, created = WorkflowState.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'current_library': reason['library'],
                'current_step': 1,
                'last_template_id': template_id,
                'treatment': reason['treatment'],
                'objection': reason['objection'],
                'appointment_booked': cause['appointment_booked'],
                'metadata': metadata or {},
            }
        )
        
        if not created:
            workflow_state.current_library = reason['library']
            workflow_state.current_step += 1
            workflow_state.last_template_id = template_id
            workflow_state.treatment = reason['treatment']
            workflow_state.objection = reason['objection']
            workflow_state.appointment_booked = cause['appointment_booked']
            workflow_state.last_message_date = timezone.now()
            if metadata:
                workflow_state.metadata.update(metadata)
            workflow_state.save()
        
        return workflow_state
    
    @staticmethod
    def should_exit_workflow(phone_number: str, template: Dict[str, Any]) -> bool:
        """
        Check if workflow should exit based on template conditions.
        """
        workflow_state = WorkflowState.objects.filter(phone_number=phone_number).first()
        
        if not workflow_state:
            return False
        
        # Check exit conditions from template
        exit_condition = template.get('workflow_exit_condition', '').lower()
        
        if 'end workflow' in exit_condition or 'final follow-up' in exit_condition:
            return True
        
        if workflow_state.appointment_booked and 'appointment is booked' in exit_condition:
            return True
        
        if workflow_state.appointment_booked and 'appointment is cancelled' in exit_condition:
            return True
        
        return False
    
    @staticmethod
    def get_next_template_in_sequence(phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get the next template in the workflow sequence based on time elapsed.
        """
        workflow_state = WorkflowState.objects.filter(phone_number=phone_number).first()
        
        if not workflow_state:
            return None
        
        # Get all templates in current library
        library_templates = TemplateCacheService.get_templates_by_library(workflow_state.current_library)
        
        # Find current template index
        current_index = -1
        for i, template in enumerate(library_templates):
            if template['template_id'] == workflow_state.last_template_id:
                current_index = i
                break
        
        if current_index == -1 or current_index + 1 >= len(library_templates):
            return None
        
        next_template = library_templates[current_index + 1]
        
        # Check if enough time has passed based on template's day field
        days_required = WorkflowService._parse_day_field(next_template['day'])
        days_elapsed = (timezone.now() - workflow_state.last_message_date).days
        
        if days_elapsed >= days_required:
            return next_template
        
        return None
    
    @staticmethod
    def reset_workflow(phone_number: str) -> bool:
        """
        Reset workflow state for a phone number.
        """
        try:
            workflow_state = WorkflowState.objects.get(phone_number=phone_number)
            workflow_state.delete()
            return True
        except WorkflowState.DoesNotExist:
            return False
    
    @staticmethod
    def _extract_variables(body: str) -> List[str]:
        """
        Extract variable placeholders from template body.
        """
        import re
        return re.findall(r'\{\{(\d+)\}\}', body)
    
    @staticmethod
    def _parse_day_field(day_field: str) -> int:
        """
        Parse the day field to extract the number of days.
        """
        day_field = day_field.lower()
        
        if 'immediately' in day_field or '0' in day_field:
            return 0
        elif '-1 day' in day_field or '24 hours' in day_field:
            return -1
        elif 'same day' in day_field or '6 hours' in day_field:
            return 0
        elif 'day 1' in day_field:
            return 1
        elif 'day 2' in day_field:
            return 2
        elif 'day 3' in day_field:
            return 3
        elif 'day 6' in day_field or 'day 8' in day_field:
            return 6
        else:
            return 1


class WorkflowOrchestrator:
    """
    High-level orchestrator for the complete cause->reason->response workflow.
    """
    
    def __init__(self):
        self.workflow_service = WorkflowService()
    
    def process_event(self, phone_number: str, user_message: str = None,
                     is_missed_call: bool = False, appointment_booked: bool = False,
                     treatment: str = None, objection: str = None,
                     metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a complete event through the cause->reason->response workflow.
        """
        # Step 1: Analyze the cause
        cause = self.workflow_service.analyze_cause(
            user_message=user_message,
            is_missed_call=is_missed_call,
            appointment_booked=appointment_booked
        )
        
        # Step 2: Determine the reason
        reason = self.workflow_service.determine_reason(
            phone_number=phone_number,
            cause=cause,
            treatment=treatment,
            objection=objection,
            user_message=user_message
        )
        
        # Step 3: Get the response
        response = self.workflow_service.get_response(
            phone_number=phone_number,
            cause=cause,
            reason=reason
        )
        
        if not response:
            return {
                'success': False,
                'message': 'No matching template found for the given cause and reason',
                'cause': cause,
                'reason': reason,
            }
        
        # Step 4: Update workflow state
        self.workflow_service.update_workflow_state(
            phone_number=phone_number,
            template_id=response['template']['template_id'],
            cause=cause,
            reason=reason,
            metadata=metadata
        )
        
        return {
            'success': True,
            'template': response['template'],
            'cause': cause,
            'reason': reason,
            'variables_needed': response['variables_needed'],
            'should_exit_workflow': self.workflow_service.should_exit_workflow(
                phone_number, response['template']
            ),
        }
    
    def get_scheduled_messages(self) -> List[Dict[str, Any]]:
        """
        Get all messages that should be sent based on time-based triggers.
        """
        scheduled_messages = []
        
        # Get all active workflow states
        active_states = WorkflowState.objects.all()
        
        for state in active_states:
            next_template = self.workflow_service.get_next_template_in_sequence(
                state.phone_number
            )
            
            if next_template:
                scheduled_messages.append({
                    'phone_number': state.phone_number,
                    'template': next_template,
                    'workflow_state': state,
                })
        
        return scheduled_messages
