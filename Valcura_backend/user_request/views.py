import json
import os

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MessageLog
from .services import GroqChatService, WhatsAppService


@csrf_exempt
def chat_rag(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON body'}, status=400)

    question = payload.get('question', '').strip()
    if not question:
        return JsonResponse({'detail': 'Question is required'}, status=400)

    response = GroqChatService().get_answer(question)
    return JsonResponse({'answer': response})


@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'GET':
        # Webhook verification for Meta API
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                return HttpResponse(challenge, status=200)
            else:
                return HttpResponse('Forbidden', status=403)
        return HttpResponse('Bad Request', status=400)
        
    elif request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
            
            # Process incoming webhook events
            if payload.get('object') == 'whatsapp_business_account':
                for entry in payload.get('entry', []):
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        if 'messages' in value:
                            for message in value['messages']:
                                from_number = message.get('from')
                                if message.get('type') == 'text':
                                    text_body = message['text']['body']
                                    
                                    # Use the AI agent to get a response
                                    agent_response = GroqChatService().get_answer(text_body)
                                    
                                    # Send the response back via WhatsApp
                                    WhatsAppService().send_message(from_number, agent_response)
                                    
                                    # Store in database
                                    MessageLog.objects.create(
                                        phone_number=from_number,
                                        user_message=text_body,
                                        ai_response=agent_response,
                                        is_missed_call=False
                                    )
                                    
            return HttpResponse('EVENT_RECEIVED', status=200)
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'Invalid JSON body'}, status=400)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return HttpResponse('Error', status=500)
            
    return JsonResponse({'detail': 'Method not allowed'}, status=405)


@csrf_exempt
def missed_call_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    # Check if the request is from Twilio (form-urlencoded) or JSON
    event = None
    number = None

    if request.content_type == 'application/x-www-form-urlencoded':
        # Twilio payload
        call_status = request.POST.get('CallStatus')
        from_number = request.POST.get('From')
        
        # Twilio sends various statuses, usually we want to trigger on 'ringing' or 'completed' 
        # (For a missed call setup, you might configure Twilio to just hit the webhook and hang up)
        if from_number:
            event = 'missed_call'
            number = from_number
    else:
        # JSON payload (Exotel, custom, etc)
        try:
            payload = json.loads(request.body.decode('utf-8'))
            event = payload.get('event')
            number = payload.get('number')
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'Invalid JSON body'}, status=400)

    if event == 'missed_call' and number:
        # We can ask the AI to generate a contextual greeting or use a static one
        prompt = "A user just called our business number and we missed it. Write a brief, polite SMS/WhatsApp message saying we missed their call and asking how we can help them. Keep it very short."
        agent_response = GroqChatService().get_answer(prompt)
        
        # WhatsApp API typically requires the number without the leading +
        # Twilio numbers usually start with +
        formatted_number = number[1:] if number.startswith('+') else number
        
        WhatsAppService().send_message(formatted_number, agent_response)
        
        # Store in database
        MessageLog.objects.create(
            phone_number=number,
            user_message="[Missed Call]",
            ai_response=agent_response,
            is_missed_call=True
        )
        
        # If Twilio is calling this, we can return TwiML to hang up or just a 200 OK
        if request.content_type == 'application/x-www-form-urlencoded':
            return HttpResponse('<Response><Reject /></Response>', content_type='text/xml')
            
        return JsonResponse({'status': 'success', 'message': 'WhatsApp message sent'})
        
    return JsonResponse({'detail': 'Invalid payload or missing fields'}, status=400)


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
            'created_at': msg.created_at.isoformat()
        })
        
    total_messages = messages.count()
    missed_calls = messages.filter(is_missed_call=True).count()
    
    return Response({
        'analytics': {
            'total_messages': total_messages,
            'missed_calls': missed_calls,
            'whatsapp_messages': total_messages - missed_calls
        },
        'messages': data
    })


def dashboard(request):
    return render(request, 'dashboard.html')
