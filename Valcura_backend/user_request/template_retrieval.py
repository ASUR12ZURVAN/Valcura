from typing import Optional, Dict, Any, List
from .template_cache import TemplateCacheService
from .workflow_service import WorkflowService


class TemplateRetrievalService:
    """
    High-level service for retrieving templates based on various situations and triggers.
    Provides a clean API for finding the right template for any given context.
    """
    
    @staticmethod
    def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by its ID.
        """
        return TemplateCacheService.get_template(template_id)
    
    @staticmethod
    def get_templates_for_missed_call() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for a missed call situation.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 1',
            trigger='Missed Call'
        )
    
    @staticmethod
    def get_templates_for_appointment_confirmation() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for appointment confirmation.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 3',
            trigger='Appointment Booked'
        )
    
    @staticmethod
    def get_templates_for_24hr_reminder() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for 24-hour appointment reminder.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 3',
            trigger='24 Hours Before Appointment'
        )
    
    @staticmethod
    def get_templates_for_6hr_reminder() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for 6-hour appointment reminder.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 3',
            trigger='6 Hours Before Appointment'
        )
    
    @staticmethod
    def get_templates_for_call_completed() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for when a call is completed without appointment.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 2',
            trigger='Call Completed – No Appointment'
        )
    
    @staticmethod
    def get_templates_for_visit_summary_consent() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for visit summary consent request.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 4',
            trigger='Consultation Completed'
        )
    
    @staticmethod
    def get_templates_for_visit_summary_delivery() -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for delivering the visit summary.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 4',
            trigger='Patient Replied "Yes"'
        )
    
    @staticmethod
    def get_templates_for_cost_objection(treatment: str = 'Root Canal Treatment') -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for cost objection handling.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 5',
            trigger='Primary Objection = Cost',
            treatment=treatment
        )
    
    @staticmethod
    def get_templates_for_trust_objection(treatment: str = 'Root Canal Treatment') -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for trust objection handling.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 5',
            trigger='Primary Objection = Trust',
            treatment=treatment
        )
    
    @staticmethod
    def get_templates_for_fear_objection(treatment: str = 'Root Canal Treatment') -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for fear objection handling.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 5',
            trigger='Primary Objection = Fear',
            treatment=treatment
        )
    
    @staticmethod
    def get_templates_for_urgency_objection(treatment: str = 'Root Canal Treatment') -> Optional[Dict[str, Any]]:
        """
        Get the appropriate template for urgency objection handling.
        """
        return TemplateCacheService.find_template_by_situation(
            library='Library 5',
            trigger='Primary Objection = No Urgency',
            treatment=treatment
        )
    
    @staticmethod
    def get_followup_templates(library: str, day_offset: int) -> Optional[Dict[str, Any]]:
        """
        Get follow-up templates based on library and day offset.
        """
        templates = TemplateCacheService.get_templates_by_library(library)
        
        for template in templates:
            day_value = WorkflowService._parse_day_field(template['day'])
            if day_value == day_offset:
                return template
        
        return None
    
    @staticmethod
    def get_next_followup_template(phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get the next follow-up template for a phone number based on workflow state.
        """
        return WorkflowService.get_next_template_in_sequence(phone_number)
    
    @staticmethod
    def get_all_library_templates(library: str) -> List[Dict[str, Any]]:
        """
        Get all templates for a specific library.
        """
        return TemplateCacheService.get_templates_by_library(library)
    
    @staticmethod
    def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
        """
        Get all templates for a specific category (Utility/Marketing).
        """
        from .models import MetaTemplate
        templates = MetaTemplate.objects.filter(category=category)
        return [TemplateCacheService._serialize_template(template) for template in templates]
    
    @staticmethod
    def get_templates_by_treatment(treatment: str) -> List[Dict[str, Any]]:
        """
        Get all templates for a specific treatment type.
        """
        return TemplateCacheService.get_templates_by_treatment(treatment)
    
    @staticmethod
    def search_templates(query: str) -> List[Dict[str, Any]]:
        """
        Search templates by name, objective, or trigger.
        """
        from .models import MetaTemplate
        from django.db.models import Q
        
        templates = MetaTemplate.objects.filter(
            Q(meta_template_name__icontains=query) |
            Q(objective__icontains=query) |
            Q(trigger__icontains=query) |
            Q(message_name__icontains=query)
        )
        
        return [TemplateCacheService._serialize_template(template) for template in templates]
    
    @staticmethod
    def get_workflow_sequence(library: str) -> List[Dict[str, Any]]:
        """
        Get the complete workflow sequence for a library in order.
        """
        templates = TemplateCacheService.get_templates_by_library(library)
        
        # Sort by day field to get the correct sequence
        def sort_key(template):
            day_value = WorkflowService._parse_day_field(template['day'])
            return day_value
        
        return sorted(templates, key=sort_key)
    
    @staticmethod
    def get_template_variables(template_id: str) -> List[str]:
        """
        Get the list of variables needed for a template.
        """
        template = TemplateCacheService.get_template(template_id)
        if not template:
            return []
        
        return WorkflowService._extract_variables(template['meta_approved_body'])
    
    @staticmethod
    def get_template_workflow_info(template_id: str) -> Dict[str, Any]:
        """
        Get workflow-related information for a template.
        """
        template = TemplateCacheService.get_template(template_id)
        if not template:
            return {}
        
        return {
            'template_id': template['template_id'],
            'library': template['library'],
            'trigger': template['trigger'],
            'day': template['day'],
            'exit_condition': template['workflow_exit_condition'],
            'objective': template['objective'],
            'internal_notes': template['internal_notes'],
        }
    
    @staticmethod
    def validate_template_variables(template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if provided variables match template requirements.
        """
        required_vars = TemplateRetrievalService.get_template_variables(template_id)
        
        missing_vars = []
        for var_num in required_vars:
            if var_num not in variables:
                missing_vars.append(var_num)
        
        return {
            'is_valid': len(missing_vars) == 0,
            'missing_variables': missing_vars,
            'required_variables': required_vars,
        }
