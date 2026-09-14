import os
import re
from typing import Any, Optional

# pyrefly: ignore [missing-import]
from .knowledge import retrieve_context
from .google_sheets_service import GoogleSheetsService
from .template_cache import TemplateCacheService

class TemplateService:
    """
    Updated TemplateService that uses the cached database model instead of the hardcoded catalog.
    Provides backward compatibility with existing code while leveraging the new caching system.
    """
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[dict[str, Any]]:
        """Get template from cache with fallback to database."""
        return TemplateCacheService.get_template(template_id)

    @classmethod
    def required_variables(cls, template_id: str) -> set[str]:
        """Get required variable placeholders from template."""
        template = cls.get_template(template_id)
        if not template:
            return set()
        return set(re.findall(r"\{\{(\d+)\}\}", template["meta_approved_body"]))

    @classmethod
    def meta_variables(cls, template_id: str, variables: dict[str, Any]) -> list[str]:
        """Get variables in Meta API order based on meta_mapping."""
        template = cls.get_template(template_id)
        if not template:
            return []
        return [str(variables.get(key, "")) for key in template["meta_mapping"]]

    @classmethod
    def normalize_variables(cls, template_id: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Normalize variable keys based on variable_mapping."""
        template = cls.get_template(template_id)
        if not template:
            return variables

        normalized = {str(key): value for key, value in variables.items()}
        for number, label in re.findall(
            r"\{\{(\d+)\}\}\s*=\s*(.*?)(?=\{\{\d+\}\}|$)",
            template["variable_mapping"],
        ):
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
            if key in variables and number not in normalized:
                normalized[number] = variables[key]
        return normalized

    @classmethod
    def meta_components(cls, template_id: str, media_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Build Meta API components for the template."""
        template = cls.get_template(template_id)
        if not template:
            return []

        components = []
        header_type = template["header_type"]
        if media_id and header_type in {"image", "video", "document"}:
            components.append({
                "type": "header",
                "parameters": [{"type": header_type, header_type: {"id": str(media_id)}},],
            })

        if template["cta_type"] == "quick reply" and template["cta_value"]:
            components.append({
                "type": "button",
                "sub_type": "quick_reply",
                "index": "0",
                "parameters": [{"type": "payload", "payload": template["cta_value"]}],
            })
        return components

    def get_message(self, template_id: str, variables: dict) -> str:
        """Render message by replacing placeholders with variable values."""
        template = self.get_template(template_id)
        if not template:
            return ""
        
        # Replace placeholders like {{1}}, {{2}} with values from variables dict
        def replace_var(match):
            var_key = match.group(1)
            return str(variables.get(var_key, f"{{{{{var_key}}}}}"))
            
        return re.sub(r'\{\{(\d+)\}\}', replace_var, template["meta_approved_body"])
    
    @classmethod
    def get_workflow_info(cls, template_id: str) -> dict[str, Any]:
        """Get workflow-related information for a template."""
        template = cls.get_template(template_id)
        if not template:
            return {}
        
        return {
            "library": template["library"],
            "trigger": template["trigger"],
            "day": template["day"],
            "category": template["category"],
            "treatment": template["treatment"],
            "objection": template["objection"],
            "exit_condition": template["workflow_exit_condition"],
        }


class WhatsAppService:
    def __init__(self) -> None:
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")
        self.last_error = ""

    def send_message(self, to_number: str, message: str, template_name: str = None, template_variables: list = None, template_components: list = None) -> bool:
        if not self.access_token or not self.phone_number_id:
            self.last_error = "WhatsApp credentials are not configured."
            print(self.last_error)
            return False

        try:
            import requests

            url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            
            if template_name:
                template_data = {
                    "name": template_name,
                    "language": {"code": "en_US"}
                }
                
                components = []
                if template_variables:
                    parameters = [{"type": "text", "text": str(var)} for var in template_variables]
                    components.append({"type": "body", "parameters": parameters})
                if template_components:
                    components.extend(template_components)
                if components:
                    template_data["components"] = components

                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_number,
                    "type": "template",
                    "template": template_data
                }
            else:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_number,
                    "type": "text",
                    "text": {"body": message},
                }

            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 'error'
            detail = ""
            if e.response is not None:
                try:
                    error_data = e.response.json().get("error", {})
                    detail = error_data.get("message") or error_data.get("type") or ""
                    error_code = error_data.get("code")
                    if error_code:
                        detail = f"{detail} (code {error_code})"
                except (ValueError, AttributeError):
                    pass
            self.last_error = f"WhatsApp API returned HTTP {status_code}."
            if detail:
                self.last_error += f" {detail}"
            print(f"Failed to send WhatsApp message. HTTP Error: {e}")
            if e.response is not None:
                print("WhatsApp API Error Response:", e.response.text)
            return False
        except Exception as e:
            self.last_error = f"WhatsApp request failed: {e}"
            print(f"Failed to send WhatsApp message: {e}")
            return False
