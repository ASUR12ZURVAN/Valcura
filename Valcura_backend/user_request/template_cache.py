from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from typing import Optional, Dict, Any, List
from .models import MetaTemplate


class TemplateCacheService:
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
    ALL_TEMPLATES_CACHE_KEY = "all_templates_cache"
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[Dict[str, Any]]:
        cache_key = f"template_{template_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        try:
            template = MetaTemplate.objects.get(template_id=template_id)
            template_data = cls._serialize_template(template)
            cache.set(cache_key, template_data, cls.CACHE_TIMEOUT)
            return template_data
        except MetaTemplate.DoesNotExist:
            return None
    
    @classmethod
    def get_all_templates(cls) -> Dict[str, Dict[str, Any]]:
        cached_data = cache.get(cls.ALL_TEMPLATES_CACHE_KEY)
        
        if cached_data is not None:
            return cached_data
        
        templates = MetaTemplate.objects.all()
        template_dict = {}
        for template in templates:
            template_dict[template.template_id] = cls._serialize_template(template)
        
        cache.set(cls.ALL_TEMPLATES_CACHE_KEY, template_dict, cls.CACHE_TIMEOUT)
        return template_dict

    
    @classmethod
    def get_templates_by_library(cls, library: str) -> List[Dict[str, Any]]:
        import hashlib
        safe_library = hashlib.md5(library.encode()).hexdigest()
        cache_key = f"templates_library_{safe_library}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        templates = MetaTemplate.objects.filter(library=library)
        template_list = [cls._serialize_template(template) for template in templates]
        cache.set(cache_key, template_list, cls.CACHE_TIMEOUT)
        return template_list
    
    @classmethod
    def get_templates_by_trigger(cls, trigger: str) -> List[Dict[str, Any]]:
        import hashlib
        safe_trigger = hashlib.md5(trigger.encode()).hexdigest()
        cache_key = f"templates_trigger_{safe_trigger}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        templates = MetaTemplate.objects.filter(trigger=trigger)
        template_list = [cls._serialize_template(template) for template in templates]
        cache.set(cache_key, template_list, cls.CACHE_TIMEOUT)
        return template_list
    
    @classmethod
    def get_templates_by_treatment(cls, treatment: str) -> List[Dict[str, Any]]:
        import hashlib
        safe_treatment = hashlib.md5(treatment.encode()).hexdigest()
        cache_key = f"templates_treatment_{safe_treatment}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        templates = MetaTemplate.objects.filter(treatment=treatment)
        template_list = [cls._serialize_template(template) for template in templates]
        cache.set(cache_key, template_list, cls.CACHE_TIMEOUT)
        return template_list
    
    @classmethod
    def get_templates_by_objection(cls, objection: str) -> List[Dict[str, Any]]:
        import hashlib
        safe_objection = hashlib.md5(objection.encode()).hexdigest()
        cache_key = f"templates_objection_{safe_objection}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        templates = MetaTemplate.objects.filter(objection=objection)
        template_list = [cls._serialize_template(template) for template in templates]
        cache.set(cache_key, template_list, cls.CACHE_TIMEOUT)
        return template_list
    
    @classmethod
    def find_template_by_situation(cls, library: str, trigger: str, 
                                   treatment: str = None, objection: str = None) -> Optional[Dict[str, Any]]:
        import hashlib
        situation_string = f"{library}_{trigger}_{treatment}_{objection}"
        safe_situation = hashlib.md5(situation_string.encode()).hexdigest()
        cache_key = f"situation_{safe_situation}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        queryset = MetaTemplate.objects.filter(library=library, trigger=trigger)
        
        if treatment:
            queryset = queryset.filter(treatment=treatment)
        if objection:
            queryset = queryset.filter(objection=objection)
        
        try:
            template = queryset.first()
            if template:
                template_data = cls._serialize_template(template)
                cache.set(cache_key, template_data, cls.CACHE_TIMEOUT)
                return template_data
        except MetaTemplate.DoesNotExist:
            pass
        
        return None
    
    @classmethod
    def invalidate_template(cls, template_id: str):
        cache_key = f"template_{template_id}"
        cache.delete(cache_key)
        cache.delete(cls.ALL_TEMPLATES_CACHE_KEY)
    
    @classmethod
    def invalidate_library_cache(cls, library: str):
        cache_key = f"templates_library_{library}"
        cache.delete(cache_key)
        cache.delete(cls.ALL_TEMPLATES_CACHE_KEY)
        return None

    @classmethod
    def get_template_from_system_config(cls, config_type: str, code: str, 
                                       treatment: str = None, objection: str = None) -> Optional[Dict[str, Any]]:
        """
        Get template from System_Config based on parameters.
        Returns cached template if available.
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
    def invalidate_cache(cls):
        """Invalidate all template cache."""
        cache.delete(cls.ALL_TEMPLATES_CACHE_KEY)
    
    @classmethod
    def _serialize_template(cls, template: MetaTemplate) -> Dict[str, Any]:
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
