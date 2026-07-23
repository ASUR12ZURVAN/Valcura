import os
from typing import Optional

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
