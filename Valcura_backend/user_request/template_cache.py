from typing import Optional, Dict, Any, List
from .models import MetaTemplate, SystemConfig


class TemplateCacheService:
    """
    Simplified template service without caching.
    Direct database queries for template retrieval.
    """
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID from database."""
        try:
            template = MetaTemplate.objects.get(template_id=template_id)
            return cls._serialize_template(template)
        except MetaTemplate.DoesNotExist:
            return None
    
    @classmethod
    def get_all_templates(cls) -> Dict[str, Dict[str, Any]]:
        """Get all templates from database."""
        templates = MetaTemplate.objects.all()
        template_dict = {}
        for template in templates:
            template_dict[template.template_id] = cls._serialize_template(template)
        return template_dict

    @classmethod
    def get_templates_by_library(cls, library: str) -> List[Dict[str, Any]]:
        """Get templates by library from database."""
        templates = MetaTemplate.objects.filter(library=library)
        return [cls._serialize_template(template) for template in templates]
    
    @classmethod
    def get_templates_by_trigger(cls, trigger: str) -> List[Dict[str, Any]]:
        """Get templates by trigger from database."""
        templates = MetaTemplate.objects.filter(trigger=trigger)
        return [cls._serialize_template(template) for template in templates]
    
    @classmethod
    def get_templates_by_treatment(cls, treatment: str) -> List[Dict[str, Any]]:
        """Get templates by treatment from database."""
        templates = MetaTemplate.objects.filter(treatment=treatment)
        return [cls._serialize_template(template) for template in templates]
    
    @classmethod
    def get_templates_by_objection(cls, objection: str) -> List[Dict[str, Any]]:
        """Get templates by objection from database."""
        templates = MetaTemplate.objects.filter(objection=objection)
        return [cls._serialize_template(template) for template in templates]
    
    @classmethod
    def find_template_by_situation(cls, library: str, trigger: str, 
                                   treatment: str = None, objection: str = None) -> Optional[Dict[str, Any]]:
        """Find template by situation from database."""
        queryset = MetaTemplate.objects.filter(library=library, trigger=trigger)
        
        if treatment:
            queryset = queryset.filter(treatment=treatment)
        if objection:
            queryset = queryset.filter(objection=objection)
        
        try:
            template = queryset.first()
            if template:
                return cls._serialize_template(template)
        except MetaTemplate.DoesNotExist:
            pass
        
        return None
    
    @classmethod
    def get_template_from_system_config(cls, config_type: str, code: str, 
                                       treatment: str = None, objection: str = None) -> Optional[Dict[str, Any]]:
        """
        Get template from System_Config based on parameters.
        """
        from django.db.models import Q
        
        query = Q(config_type=config_type, code=code, active_status=True)
        
        if treatment:
            query &= Q(treatment=treatment)
        if objection:
            query &= Q(objection=objection)
        
        config = SystemConfig.objects.filter(query).first()
        
        if config:
            return cls.get_template(config.meta_template_name)
        
        return None
    
    @classmethod
    def _serialize_template(cls, template: MetaTemplate) -> Dict[str, Any]:
        """Serialize template object to dictionary."""
        return {
            "template_id": template.template_id,
            "meta_template_name": template.meta_template_name,
            "library": template.library,
            "message_name": template.message_name,
            "category": template.category,
            "treatment": template.treatment,
            "objection": template.objection,
            "trigger": template.trigger,
            "day": template.day,
            "header_type": template.header_type,
            "header_text": template.header_text,
            "meta_approved_body": template.meta_approved_body,
            "cta_type": template.cta_type,
            "cta_value": template.cta_value,
            "media_type": template.media_type,
            "media_asset_id": template.media_asset_id,
            "variable_mapping": template.variable_mapping,
            "objective": template.objective,
            "ai_personalization_inputs": template.ai_personalization_inputs,
            "ai_writing_rules": template.ai_writing_rules,
            "workflow_exit_condition": template.workflow_exit_condition,
            "internal_notes": template.internal_notes,
            "meta_templates": template.meta_templates,
            "meta_mapping": template.meta_mapping,
        }
