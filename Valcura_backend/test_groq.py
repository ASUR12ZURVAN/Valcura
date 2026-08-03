import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    print("GROQ_API_KEY is not set.")
    exit(1)

prompt = "A user just called our business number and we missed it. Write a brief, polite SMS/WhatsApp message saying we missed their call and asking how we can help them. Keep it very short."

print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")
print(f"Prompt: {prompt}\n")

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are a medical support assistant for a hospital. Reply briefly, clearly, and safely.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    },
    timeout=20,
)

if response.status_code == 200:
    payload = response.json()
    print("Groq API Response:")
    print("-" * 20)
    print(payload["choices"][0]["message"]["content"].strip())
    print("-" * 20)
else:
    print("Failed to get response from Groq API")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
