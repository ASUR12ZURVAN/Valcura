from django.test import TestCase
from django.urls import reverse


class ChatRAGEndpointTests(TestCase):
    def test_chat_endpoint_returns_answer_for_common_question(self):
        response = self.client.post(
            reverse('chat-rag'),
            data={'question': 'What are the doctor timings?'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('answer', data)
        self.assertTrue(len(data['answer']) > 0)
