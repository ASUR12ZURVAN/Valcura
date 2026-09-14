import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Valcura_backend.settings')
django.setup()

from django.test import RequestFactory
from user_request.views import macrodroid_webhook, whatsapp_webhook, sync_sheets_view
from user_request.models import MessageLog
from user_request.services import GoogleSheetsService

def run_tests():
    print("--- Starting Backend Google Sheets & Webhook Tests ---")
    factory = RequestFactory()

    # Test 1: Direct GoogleSheetsService Call
    print("\n1. Testing GoogleSheetsService.append_row()...")
    service = GoogleSheetsService()
    success, msg = service.append_row(
        phone_number="+1234567890",
        source="Unit Test",
        user_message="Hello Google Sheets",
        ai_response="Automated Test Response",
        status="Testing"
    )
    print(f"Result: Success={success}, Message='{msg}'")

    # Test 2: MacroDroid Inbound Response Webhook
    print("\n2. Testing MacroDroid User Response Webhook...")
    payload_macrodroid_resp = {
        "phone_number": "+919876543210",
        "user_response": "Yes, I need to schedule an appointment for tomorrow.",
        "event": "response"
    }
    request = factory.post(
        '/api/macrodroid/webhook/',
        data=json.dumps(payload_macrodroid_resp),
        content_type='application/json'
    )
    response = macrodroid_webhook(request)
    print(f"Status Code: {response.status_code}, Body: {response.content.decode('utf-8')}")

    # Test 3: WhatsApp Inbound Reply Webhook (Meta Format)
    print("\n3. Testing WhatsApp Incoming Message Webhook (Meta Format)...")
    payload_whatsapp_meta = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "+1555000", "phone_number_id": "1000"},
                            "messages": [
                                {
                                    "from": "919123456789",
                                    "id": "wamid.HBgL...",
                                    "timestamp": "1700000000",
                                    "text": {"body": "I would like to confirm my consultation for 4 PM."},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    request = factory.post(
        '/api/whatsapp/webhook/',
        data=json.dumps(payload_whatsapp_meta),
        content_type='application/json'
    )
    response = whatsapp_webhook(request)
    print(f"Status Code: {response.status_code}, Body: {response.content.decode('utf-8')}")

    # Test 4: WhatsApp Verification GET Handshake
    print("\n4. Testing WhatsApp Webhook GET Verification Handshake...")
    request = factory.get('/api/whatsapp/webhook/?hub.mode=subscribe&hub.verify_token=valcura_secure_webhook_token_2026&hub.challenge=CHALLENGE_CODE_123')
    response = whatsapp_webhook(request)
    print(f"Status Code: {response.status_code}, Handshake Response: {response.content.decode('utf-8')}")

    # Test 5: Check Database Records
    print("\n5. Checking Database MessageLog entries...")
    logs = MessageLog.objects.all().order_by('-created_at')[:5]
    for log in logs:
        print(f"- ID: {log.id} | Source: {log.source} | Phone: {log.phone_number} | Status: {log.status} | Sheet Synced: {log.sheet_synced} | Msg: {log.user_message[:30] if log.user_message else ''}")

    print("\n--- All Backend Integration Tests Finished Successfully ---")

if __name__ == "__main__":
    run_tests()
