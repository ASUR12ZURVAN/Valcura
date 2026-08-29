from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .services import TemplateService


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


class MetaTemplateTests(TestCase):
    def test_all_approved_templates_are_loaded_from_csv(self):
        templates = TemplateService._load_templates()

        self.assertEqual(len(templates), 121)
        self.assertEqual(
            templates['MKT-L3-01']['name'],
            'mkt_l3_appointment_confirmation_v1',
        )
        self.assertEqual(templates['MKT-L3-01']['workflow']['trigger'], 'Appointment Booked')
        self.assertEqual(templates['MKT-L3-01']['workflow']['day'], 'Immediately')

    def test_named_variables_are_normalized_and_mapping_order_is_preserved(self):
        variables = TemplateService.normalize_variables(
            'MKT-L3-01',
            {
                'clinic_name': 'Valcura Dental',
                'doctor_name': 'Taylor',
                'reception_number': '+15550001111',
                'patient_name': 'Alex',
                'appointment_date': '2026-09-01',
                'appointment_time': '10:30',
                'google_maps_link': 'https://maps.example/valcura',
            },
        )

        self.assertEqual(
            TemplateService.meta_variables('MKT-L3-01', variables),
            ['Alex', 'Taylor', '2026-09-01', '10:30', 'Valcura Dental',
             'https://maps.example/valcura', '+15550001111', 'Valcura Dental'],
        )

    @patch('user_request.views.WhatsAppService.send_message', return_value=True)
    @patch('user_request.views.GoogleSheetsService.append_row', return_value=(True, 'ok'))
    def test_webhook_sends_csv_meta_name_and_ordered_variables(self, _append_row, send_message):
        response = self.client.post(
            reverse('macrodroid-webhook'),
            data={
                'phone_number': '+15550001111',
                'template_id': 'MKT-L3-01',
                'variables': {
                    '1': 'Valcura Dental', '2': 'Taylor', '3': '+15550001111',
                    '4': 'Alex', '10': '2026-09-01', '11': '10:30',
                    '16': 'https://maps.example/valcura',
                },
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(send_message.call_args.kwargs['template_name'], 'mkt_l3_appointment_confirmation_v1')
        self.assertEqual(send_message.call_args.kwargs['template_variables'], [
            'Alex', 'Taylor', '2026-09-01', '10:30', 'Valcura Dental',
            'https://maps.example/valcura', '+15550001111', 'Valcura Dental',
        ])
