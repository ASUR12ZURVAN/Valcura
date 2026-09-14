from datetime import date

from django.test import TestCase
from django.urls import reverse

from user_request.models import ClinicProfile, HospitalUser, MessageLog, PatientContact


class HospitalAuthTests(TestCase):
    def registration_data(self, username='admin'):
        return {
            'clinic_name': 'Valcura Dental',
            'city': 'Pune',
            'locality': 'Kothrud',
            'clinic_type': 'Dental',
            'chair_count': 4,
            'primary_specialty': 'Dentistry',
            'monthly_revenue_baseline_inr': '100000',
            'reception_team_size': 2,
            'onboarding_date': date.today().isoformat(),
            'crm_status': 'Not integrated',
            'crm_name': '',
            'crm_integration_mode': '',
            'valcura_plan': 'Basic',
            'admin_username': username,
            'admin_email': f'{username}@example.com',
            'admin_password': 'StrongPassword123!',
            'admin_password_confirm': 'StrongPassword123!',
        }

    def test_registration_logs_in_and_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('hospital_register'), self.registration_data()
        )

        self.assertRedirects(response, reverse('hospital_dashboard'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'admin')
        self.assertEqual(ClinicProfile.objects.count(), 1)

    def test_login_redirects_to_dashboard_and_dashboard_is_hospital_scoped(self):
        clinic = ClinicProfile.objects.create(
            clinic_id='CLNVALCURA', clinic_name='Valcura Dental', city='Pune',
            locality='Kothrud', clinic_type='Dental', chair_count=4,
            primary_specialty='Dentistry', monthly_revenue_baseline_inr=100000,
            reception_team_size=2, onboarding_date=date.today(),
            crm_status='Not integrated', valcura_plan='Basic'
        )
        user = HospitalUser.objects.create_user(
            username='admin', password='StrongPassword123!', clinic=clinic
        )
        patient = PatientContact.objects.create(
            patient_id='PAT-1', clinic=clinic, patient_name='Patient One',
            phone_number='+15550000001', new_existing_patient='New',
            data_source='Test'
        )
        MessageLog.objects.create(
            phone_number=patient.phone_number, user_message='Hello',
            ai_response='Welcome'
        )

        response = self.client.post(reverse('login'), {
            'username': user.username,
            'password': 'StrongPassword123!',
        })

        self.assertRedirects(response, reverse('hospital_dashboard'))
        dashboard = self.client.get(reverse('hospital_dashboard'))
        self.assertContains(dashboard, 'Hello')
        self.assertContains(dashboard, 'Welcome')

    def test_auth_routes_work_without_trailing_slashes(self):
        self.assertEqual(self.client.get('/register').status_code, 200)
        self.assertEqual(self.client.get('/login').status_code, 200)

    def test_empty_clinic_dashboard_shows_demo_messages_and_filters(self):
        self.client.post(reverse('hospital_register'), self.registration_data())

        dashboard = self.client.get(reverse('hospital_dashboard'))

        self.assertContains(dashboard, 'Aarav Mehta')
        self.assertContains(dashboard, 'Diya Shah')
        self.assertContains(dashboard, 'patient-filter')
        self.assertContains(dashboard, 'issue-filter')
        self.assertContains(dashboard, 'Appointment')
        self.assertContains(dashboard, 'Pricing')
        self.assertNotContains(dashboard, "'phone_number':")