import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import GroqChatService


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
