import os
from typing import Optional

# pyrefly: ignore [missing-import]
from .knowledge import retrieve_context


class GroqChatService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY")

    def get_answer(self, question: str) -> str:
        context = retrieve_context(question)

        if not self.api_key:
            return (
                f"I found the following local guidance:\n\n{context}\n\n"
                "To enable live Groq-based RAG responses, set GROQ_API_KEY in your environment."
            )

        try:
            import requests

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a medical support assistant for a hospital. "
                                "Reply briefly, clearly, and safely using only the provided context."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Context:\n{context}\n\nQuestion:\n{question}",
                        },
                    ],
                    "temperature": 0.2,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"].strip()
        except Exception:
            return (
                f"I found the following local guidance:\n\n{context}\n\n"
                "The live Groq request failed, so this response is using the local retrieval fallback."
            )


class WhatsAppService:
    def __init__(self) -> None:
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")

    def send_message(self, to_number: str, message: str) -> bool:
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
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message},
            }

            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to send WhatsApp message: {e}")
            return False
