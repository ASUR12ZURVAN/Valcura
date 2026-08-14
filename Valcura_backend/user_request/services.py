import os
from typing import Optional

# pyrefly: ignore [missing-import]
from .knowledge import retrieve_context
from .google_sheets_service import GoogleSheetsService


import re

class TemplateService:
    TEMPLATES = {
        "UTL-L1-01": (
            "Thank you for reaching out to {{1}}.\n\n"
            "We are sorry that we couldn't connect with you when you called us a little while ago.\n\n"
            "If you are still looking for help with your dental concern, simply reply to this message or call us on {{3}}, whichever is more convenient for you.\n\n"
            "We are here whenever you need us, and we will be happy to assist you.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "MKT-L1-02": (
            "Thank you once again for reaching out to {{1}}.\n\n"
            "Choosing a dental clinic is an important decision, and we believe every patient deserves honest advice and treatment that is genuinely needed.\n\n"
            "That's why every advise at {{1}} is made with your long term oral health in mind, supported by experienced doctors, modern technology and the trust of many happy patients.\n\n"
            "There's no pressure. Our role is simply to help you make the right decision for your oral health.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "MKT-L1-03": (
            "Since you had reached out to us recently, we just wanted to check if your dental concern still needs attention.\n\n"
            "If you have any questions or would simply like to understand your options better, we would be glad to help.You can call us on {{3}} whenever it's convenient for you.\n\n"
            "Take your time, our role is simply to help you make an informed decision for your oral health.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "MKT-L1-04": (
            "We thought we would check in one last time regarding your enquiry with {{1}}.\n\n"
            "If your dental concern is still bothering you, we would be happy to help you understand the right treatment options whenever you're ready. You can simply reply to this message or call us on {{3}}.\n\n"
            "Whether you choose us or not, we hope you don't ignore your oral health. Wishing you good oral health.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "UTL-L2-01": (
            "Every treatment begins with understanding your concern.\n\n"
            "Hi {{4}},\n\n"
            "Thank you for speaking with our team today about {{6}}.\n\n"
            "We hope your initial questions were answered. If anything else comes to mind, reply to this message, we will be happy to help.\n\n"
            "We are here whenever you need us.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "MKT-L2-02": (
            "The right advice is just as important as the right treatment.\n\n"
            "Hi {{4}},\n\n"
            "We understand your concern about {{6}}.\n\n"
            "At {{1}}, every recommendation for {{5}} is made only when it's genuinely needed, using modern technology and a patient-first approach.\n\n"
            "Call us on {{3}} if you would like to discuss your concern further.\n\n"
            "The right decision begins with the right understanding.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "MKT-L2-03": (
            "The more you understand your treatment, the more confident you'll feel.\n\n"
            "Hi {{4}},\n\n"
            "Based on what you shared about {{6}}, {{5}} may be one of the suitable treatment options.\n\n"
            "We've attached a simple overview explaining what it is, how it helps and why timely care matters.\n\n"
            "Call us on {{3}} if you'd like to know more.\n\n"
            "Take your time, we arre here to answer your questions.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
        "MKT-L2-04": (
            "A consultation isn't about starting treatment, it's about getting clarity.\n\n"
            "Hi {{4}},\n\n"
            "If {{6}} is still bothering you, we'd be happy to answer your questions and help you understand whether {{5}} is the right option.\n\n"
            "Reply to this message or call us on {{3}} whenever you're ready.\n\n"
            "Our goal is to help you decide with confidence.\n\n"
            "Team {{1}}\n"
            "Dr. {{2}}"
        ),
    }

    def get_message(self, template_id: str, variables: dict) -> str:
        template = self.TEMPLATES.get(template_id)
        if not template:
            return ""
        
        # Replace placeholders like {{1}}, {{2}} with values from variables dict
        def replace_var(match):
            var_key = match.group(1)
            return str(variables.get(var_key, f"{{{{{var_key}}}}}"))
            
        return re.sub(r'\{\{(\d+)\}\}', replace_var, template)


class WhatsAppService:
    def __init__(self) -> None:
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")

    def send_message(self, to_number: str, message: str, template_name: str = None, template_variables: list = None) -> bool:
        if not self.access_token or not self.phone_number_id:
            print("WhatsApp credentials not set. Cannot send message.")
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
                
                if template_variables:
                    parameters = [{"type": "text", "text": str(var)} for var in template_variables]
                    template_data["components"] = [
                        {
                            "type": "body",
                            "parameters": parameters
                        }
                    ]

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
            print(f"Failed to send WhatsApp message. HTTP Error: {e}")
            if e.response is not None:
                print("WhatsApp API Error Response:", e.response.text)
            return False
        except Exception as e:
            print(f"Failed to send WhatsApp message: {e}")
            return False
