import json
import os

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MessageLog
from .services import TemplateService, WhatsAppService, GoogleSheetsService

@csrf_exempt
def macrodroid_webhook(request):
    """
    Webhook handling MacroDroid triggers.
    Supports both outbound triggers (sending template messages) and inbound user responses from MacroDroid.
    Updates Google Sheets on both outbound triggers and inbound responses.
    """
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    try:
        print("MacroDroid Raw request body:", request.body)
        body_text = request.body.decode('utf-8')
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            from urllib.parse import parse_qs
            parsed = parse_qs(body_text)
            if parsed:
                payload = {k: v[0] for k, v in parsed.items()}
            else:
                payload = {"raw_body": body_text}
                
        print("MacroDroid Parsed payload:", payload)
    except Exception as e:
        print("Error reading body:", e)
        return JsonResponse({'detail': 'Invalid body format'}, status=400)

    phone_number = payload.get('phone_number') or payload.get('call_number') or payload.get('from')
    user_response = payload.get('user_response') or payload.get('response_text') or payload.get('message')
    event_type = payload.get('event', 'trigger') # 'trigger' or 'response'

    if not phone_number:
        print("Error: Missing phone_number or call_number in payload.")
        return JsonResponse({'detail': 'phone_number or call_number is required'}, status=400)

    sheets_service = GoogleSheetsService()

    # IF payload represents a direct USER RESPONSE captured via MacroDroid (e.g. SMS reply / Call outcome)
    if user_response or event_type == 'response':
        status_label = payload.get('status', 'Received (MacroDroid)')
        ai_response_text = payload.get('ai_response', 'User response logged from MacroDroid')

        # 1. Log in SQLite Database
        synced_success, sync_msg = sheets_service.append_row(
            phone_number=phone_number,
            source="MacroDroid",
            user_message=user_response or "User Response",
            ai_response=ai_response_text,
            status=status_label
        )

        log_entry = MessageLog.objects.create(
            phone_number=phone_number,
            user_message=user_response,
            ai_response=ai_response_text,
            is_missed_call=False,
            source="MacroDroid",
            status=status_label,
            sheet_synced=synced_success
        )

        return JsonResponse({
            'status': 'success',
            'type': 'user_response',
            'sheet_synced': synced_success,
            'sync_detail': sync_msg,
            'message_id': log_entry.id
        })

    # ELSE: Payload represents an OUTBOUND MISSED CALL TRIGGER
    template_id = payload.get('template_id', 'UTL-L1-01')
    variables = payload.get('variables', {})

    if not variables and isinstance(payload, dict):
        sim_operator = payload.get('sim_operator_name', 'Valcura')
        call_name = payload.get('call_name', 'Valued Patient')
        
        variables = {
            "1": sim_operator,
            "2": "Smith",
            "3": phone_number,
            "4": call_name,
        }

    template_service = TemplateService()
    message = template_service.get_message(template_id, variables)

    if not message:
        return JsonResponse({'detail': f'Invalid template_id: {template_id}'}, status=400)

    import re
    formatted_number = re.sub(r'\D', '', phone_number)

    meta_template_name = payload.get('meta_template_name', 'clinical_reply')
    # clinical_reply template expects 1 variable: the patient's name
    patient_name = variables.get("4", "Valued Patient")
    
    whatsapp_service = WhatsAppService()
    send_success = whatsapp_service.send_message(
        formatted_number, 
        message, 
        template_name=meta_template_name,
        template_variables=[patient_name]
    )

    # Sync to Google Sheets
    synced_success, sync_msg = sheets_service.append_row(
        phone_number=phone_number,
        source="MacroDroid Trigger",
        user_message=f"[Missed Call / Trigger: {template_id}]",
        ai_response=message,
        status="Sent" if send_success else "Send Failed"
    )

    # Store in database
    log_entry = MessageLog.objects.create(
        phone_number=phone_number,
        user_message=f"[MacroDroid Trigger: {template_id}]",
        ai_response=message,
        is_missed_call=True if "Missed Call" in message or "UTL-L1" in template_id else False,
        source="MacroDroid",
        status="Sent" if send_success else "Send Failed",
        sheet_synced=synced_success
    )

    if send_success:
        return JsonResponse({
            'status': 'success',
            'message': 'WhatsApp message sent',
            'sheet_synced': synced_success,
            'sync_detail': sync_msg
        })
    else:
        return JsonResponse({
            'status': 'error',
            'detail': 'Failed to send WhatsApp message',
            'sheet_synced': synced_success,
            'sync_detail': sync_msg
        }, status=500)


@csrf_exempt
def whatsapp_webhook(request):
    """
    Webhook endpoint for receiving incoming WhatsApp responses (Meta WhatsApp Cloud API / Twilio).
    - GET: Meta Webhook verification handshake.
    - POST: Incoming patient message/reply processing & Google Sheets auto-sync.
    """
    # 1. Verification Handshake (GET Request from Meta)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        expected_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'valcura_secure_webhook_token_2026')

        if mode == 'subscribe' and token == expected_token:
            print("WhatsApp Webhook verified successfully.")
            return HttpResponse(challenge, status=200)
        else:
            print(f"WhatsApp Webhook verification failed. Token received: {token}")
            return HttpResponse('Verification failed', status=403)

    # 2. Incoming Webhook Event (POST Request)
    if request.method == 'POST':
        try:
            body_text = request.body.decode('utf-8')
            payload = json.loads(body_text) if body_text else {}
            print("WhatsApp Webhook Payload:", json.dumps(payload, indent=2))
        except Exception as e:
            print("Error parsing WhatsApp webhook JSON:", e)
            return JsonResponse({'detail': 'Invalid JSON'}, status=400)

        # Parse standard Meta Cloud API payload structure
        phone_number = None
        user_message = None
        message_id = None

        try:
            entry = payload.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])

            if messages:
                msg_item = messages[0]
                phone_number = msg_item.get('from')
                message_id = msg_item.get('id')

                # Handle text message
                if msg_item.get('type') == 'text':
                    user_message = msg_item.get('text', {}).get('body')
                # Handle interactive button reply
                elif msg_item.get('type') == 'interactive':
                    interactive = msg_item.get('interactive', {})
                    if interactive.get('type') == 'button_reply':
                        user_message = interactive.get('button_reply', {}).get('title')
                    elif interactive.get('type') == 'list_reply':
                        user_message = interactive.get('list_reply', {}).get('title')
                # Fallback for other message types
                else:
                    user_message = f"[{msg_item.get('type')} message received]"

        except Exception as parse_err:
            print("Parsing Meta structure failed, trying flat payload fallback:", parse_err)

        # Fallback for flat JSON / Twilio format
        if not phone_number:
            phone_number = payload.get('From') or payload.get('phone_number') or payload.get('from')
            user_message = payload.get('Body') or payload.get('user_message') or payload.get('message')

        if not phone_number or not user_message:
            # Might be a status update event (sent, delivered, read)
            return JsonResponse({'status': 'ignored', 'detail': 'No user message found in event'}, status=200)

        formatted_number = phone_number.replace('whatsapp:', '').strip()

        ai_ack_response = f"Thank you for your response! We have received your message: '{user_message}'"

        # 3. Sync to Google Sheets
        sheets_service = GoogleSheetsService()
        synced_success, sync_msg = sheets_service.append_row(
            phone_number=formatted_number,
            source="WhatsApp API Response",
            user_message=user_message,
            ai_response=ai_ack_response,
            status="Received"
        )

        # 4. Save in Database
        log_entry = MessageLog.objects.create(
            phone_number=formatted_number,
            user_message=user_message,
            ai_response=ai_ack_response,
            is_missed_call=False,
            source="WhatsApp API",
            status="Received",
            sheet_synced=synced_success
        )

        return JsonResponse({
            'status': 'success',
            'message_id': log_entry.id,
            'sheet_synced': synced_success,
            'sync_detail': sync_msg
        }, status=200)

    return JsonResponse({'detail': 'Method not allowed'}, status=405)


@csrf_exempt
def sync_sheets_view(request):
    """
    API endpoint to manually sync message logs or trigger a test row to Google Sheets.
    """
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed. Use POST.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    phone_number = data.get('phone_number', '+1234567890')
    source = data.get('source', 'Manual Test')
    user_message = data.get('user_message', 'Test message for Google Sheets sync')
    ai_response = data.get('ai_response', 'Test system response')
    status = data.get('status', 'Test Success')

    sheets_service = GoogleSheetsService()
    success, detail = sheets_service.append_row(
        phone_number=phone_number,
        source=source,
        user_message=user_message,
        ai_response=ai_response,
        status=status
    )

    return JsonResponse({
        'status': 'success' if success else 'error',
        'sheet_synced': success,
        'detail': detail,
        'config': {
            'spreadsheet_id': bool(sheets_service.spreadsheet_id),
            'has_service_account': bool(os.path.exists(sheets_service.service_account_file) or sheets_service.service_account_json),
            'has_webhook_url': bool(sheets_service.webhook_url)
        }
    }, status=200 if success else 400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_list(request):
    messages = MessageLog.objects.all().order_by('-created_at')
    
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'phone_number': msg.phone_number,
            'user_message': msg.user_message,
            'ai_response': msg.ai_response,
            'is_missed_call': msg.is_missed_call,
            'source': getattr(msg, 'source', 'WhatsApp'),
            'status': getattr(msg, 'status', 'Received'),
            'sheet_synced': getattr(msg, 'sheet_synced', False),
            'created_at': msg.created_at.isoformat()
        })
        
    total_messages = messages.count()
    missed_calls = messages.filter(is_missed_call=True).count()
    synced_count = messages.filter(sheet_synced=True).count()
    
    return Response({
        'analytics': {
            'total_messages': total_messages,
            'missed_calls': missed_calls,
            'whatsapp_messages': total_messages - missed_calls,
            'google_sheets_synced': synced_count
        },
        'messages': data
    })


def dashboard(request):
    return render(request, 'dashboard.html')
