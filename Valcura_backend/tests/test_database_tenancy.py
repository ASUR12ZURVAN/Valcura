import uuid
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from user_request.models import (
    ClinicAuditEvent,
    ClinicIntegration,
    ClinicInvitation,
    ClinicMembership,
    ClinicProfile,
    DataImportJob,
    DataImportRowError,
    HospitalUser,
    MessageLog,
    WebhookEvent,
    WorkflowState,
)


class DatabaseTenancyTests(TestCase):
    def setUp(self):
        self.clinic_a = ClinicProfile.objects.create(
            clinic_id="CLNCLINICA",
            clinic_name="Clinic Alpha",
            city="Pune",
            locality="Kothrud",
            clinic_type="Dental",
            chair_count=3,
            primary_specialty="Orthodontics",
            monthly_revenue_baseline_inr=150000,
            reception_team_size=2,
            onboarding_date=date.today(),
            crm_status="None",
            valcura_plan="Standard",
        )

        self.clinic_b = ClinicProfile.objects.create(
            clinic_id="CLNCLINICB",
            clinic_name="Clinic Beta",
            city="Mumbai",
            locality="Bandra",
            clinic_type="Dental",
            chair_count=5,
            primary_specialty="Endodontics",
            monthly_revenue_baseline_inr=300000,
            reception_team_size=3,
            onboarding_date=date.today(),
            crm_status="None",
            valcura_plan="Premium",
        )

        self.user_a = HospitalUser.objects.create_user(
            username="dr_alpha",
            email="alpha@example.com",
            password="Password123!",
            clinic=self.clinic_a,
            role="doctor",
        )

        self.user_b = HospitalUser.objects.create_user(
            username="admin_beta",
            email="beta@example.com",
            password="Password123!",
            clinic=self.clinic_b,
            role="admin",
            is_hospital_admin=True,
        )

    # -------------------------------------------------------------
    # 1. ClinicProfile Identity & Lifecycle
    # -------------------------------------------------------------
    def test_clinic_has_auto_generated_unique_uuid_tenant_id(self):
        self.assertIsNotNone(self.clinic_a.tenant_id)
        self.assertIsNotNone(self.clinic_b.tenant_id)
        self.assertNotEqual(self.clinic_a.tenant_id, self.clinic_b.tenant_id)
        self.assertIsInstance(self.clinic_a.tenant_id, uuid.UUID)

    def test_clinic_name_change_does_not_alter_tenant_id(self):
        original_tenant_id = self.clinic_a.tenant_id
        self.clinic_a.clinic_name = "Renamed Alpha Clinic"
        self.clinic_a.save()
        self.clinic_a.refresh_from_db()
        self.assertEqual(self.clinic_a.tenant_id, original_tenant_id)

    def test_clinic_lifecycle_onboarding_status_defaults_to_pending(self):
        clinic = ClinicProfile.objects.create(
            clinic_id="CLNTESTNEW",
            clinic_name="New Test Clinic",
            city="Delhi",
            locality="Connaught",
            clinic_type="Dental",
            chair_count=2,
            primary_specialty="General",
            monthly_revenue_baseline_inr=50000,
            reception_team_size=1,
            onboarding_date=date.today(),
            crm_status="None",
            valcura_plan="Starter",
        )
        self.assertEqual(clinic.onboarding_status, "pending")

    # -------------------------------------------------------------
    # 2. ClinicMembership Constraints
    # -------------------------------------------------------------
    def test_membership_creation_and_unique_constraint(self):
        membership = ClinicMembership.objects.create(
            clinic=self.clinic_a,
            user=self.user_a,
            role="clinician",
            status="active",
        )
        self.assertEqual(membership.clinic, self.clinic_a)
        self.assertEqual(membership.user, self.user_a)

        # Duplicate membership for the exact same clinic and user must fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicMembership.objects.create(
                    clinic=self.clinic_a,
                    user=self.user_a,
                    role="admin",
                )

    def test_multi_clinic_user_membership(self):
        """A user can hold memberships in multiple distinct clinics."""
        mem_a = ClinicMembership.objects.create(
            clinic=self.clinic_a,
            user=self.user_a,
            role="clinician",
            status="active",
        )
        mem_b = ClinicMembership.objects.create(
            clinic=self.clinic_b,
            user=self.user_a,
            role="manager",
            status="active",
        )
        self.assertNotEqual(mem_a.clinic, mem_b.clinic)
        self.assertEqual(self.user_a.memberships.count(), 2)

    # -------------------------------------------------------------
    # 3. ClinicInvitation
    # -------------------------------------------------------------
    def test_clinic_invitation_lifecycle(self):
        token_hash = "hash_" + uuid.uuid4().hex
        invitation = ClinicInvitation.objects.create(
            clinic=self.clinic_a,
            email="newdoctor@example.com",
            role="clinician",
            token_hash=token_hash,
            invited_by=self.user_b,
            expires_at=timezone.now() + timedelta(days=7),
            status="pending",
        )
        self.assertEqual(invitation.status, "pending")
        self.assertEqual(invitation.clinic, self.clinic_a)

        # Duplicate token_hash must fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicInvitation.objects.create(
                    clinic=self.clinic_b,
                    email="other@example.com",
                    role="receptionist",
                    token_hash=token_hash,
                    expires_at=timezone.now() + timedelta(days=7),
                )

    # -------------------------------------------------------------
    # 4. ClinicIntegration & Secret Masking Boundary
    # -------------------------------------------------------------
    def test_clinic_integration_unique_account_mapping(self):
        ClinicIntegration.objects.create(
            clinic=self.clinic_a,
            provider="whatsapp_cloud",
            external_account_id="WABA_PHONE_12345",
            secret_reference="secrets/clinic_a/whatsapp_token",
            config={"display_phone_number": "+91 99999 11111"},
            status="active",
        )

        # Another clinic cannot bind to the exact same external_account_id
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicIntegration.objects.create(
                    clinic=self.clinic_b,
                    provider="whatsapp_cloud",
                    external_account_id="WABA_PHONE_12345",
                    secret_reference="secrets/clinic_b/whatsapp_token",
                )

    def test_clinic_integration_one_provider_per_clinic(self):
        ClinicIntegration.objects.create(
            clinic=self.clinic_a,
            provider="google_sheets",
            external_account_id="SPREADSHEET_ID_ALPHA",
            secret_reference="secrets/clinic_a/google_sa",
        )

        # Same clinic cannot add duplicate provider config
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicIntegration.objects.create(
                    clinic=self.clinic_a,
                    provider="google_sheets",
                    external_account_id="SPREADSHEET_ID_ALPHA_2",
                )

    # -------------------------------------------------------------
    # 5. MessageLog Tenant Ownership
    # -------------------------------------------------------------
    def test_messagelog_supports_explicit_clinic_ownership_and_unscoped_legacy(self):
        # Explicit clinic ownership
        msg_scoped = MessageLog.objects.create(
            clinic=self.clinic_a,
            phone_number="+919876543210",
            user_message="Hello Clinic A",
            ai_response="Welcome to Clinic A",
        )
        self.assertEqual(msg_scoped.clinic, self.clinic_a)

        # Unscoped legacy message (null clinic) remains permissible during migration
        msg_legacy = MessageLog.objects.create(
            clinic=None,
            phone_number="+919876543210",
            user_message="Legacy message",
            ai_response="Legacy response",
        )
        self.assertIsNone(msg_legacy.clinic)

    # -------------------------------------------------------------
    # 6. WorkflowState Tenant-Scoped Uniqueness
    # -------------------------------------------------------------
    def test_workflow_state_allows_same_phone_across_different_clinics(self):
        """Cross-tenant fix: Two different clinics CAN have a workflow state for the same phone number."""
        wf_a = WorkflowState.objects.create(
            clinic=self.clinic_a,
            phone_number="+919999988888",
            current_library="L1",
            current_step=1,
        )
        wf_b = WorkflowState.objects.create(
            clinic=self.clinic_b,
            phone_number="+919999988888",
            current_library="L2",
            current_step=2,
        )
        self.assertEqual(wf_a.phone_number, wf_b.phone_number)
        self.assertNotEqual(wf_a.clinic, wf_b.clinic)

    def test_workflow_state_enforces_uniqueness_within_same_clinic(self):
        """Within the same clinic, duplicate phone number in WorkflowState must fail."""
        WorkflowState.objects.create(
            clinic=self.clinic_a,
            phone_number="+919999977777",
            current_library="L1",
            current_step=1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkflowState.objects.create(
                    clinic=self.clinic_a,
                    phone_number="+919999977777",
                    current_library="L1",
                    current_step=2,
                )

    # -------------------------------------------------------------
    # 7. WebhookEvent Idempotency
    # -------------------------------------------------------------
    def test_webhook_event_idempotency_constraint(self):
        WebhookEvent.objects.create(
            clinic=self.clinic_a,
            provider="whatsapp_cloud",
            provider_event_id="wamid.HBgLMTIzNDU2",
            payload={"sample": "payload"},
            status="received",
        )

        # Duplicate delivery with the same provider and event_id must fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WebhookEvent.objects.create(
                    clinic=self.clinic_a,
                    provider="whatsapp_cloud",
                    provider_event_id="wamid.HBgLMTIzNDU2",
                    payload={"sample": "duplicate_payload"},
                )

    # -------------------------------------------------------------
    # 8. DataImportJob and Row Errors
    # -------------------------------------------------------------
    def test_data_import_job_and_row_error_cascade(self):
        job = DataImportJob.objects.create(
            clinic=self.clinic_a,
            uploaded_by=self.user_a,
            file_name="patients_batch_01.csv",
            total_rows=10,
            status="importing",
        )
        row_err = DataImportRowError.objects.create(
            job=job,
            row_number=3,
            field_name="phone_number",
            error_message="Invalid phone format",
            raw_row_data={"name": "Jane Doe", "phone": "invalid"},
        )
        self.assertEqual(job.row_errors.count(), 1)
        self.assertEqual(job.row_errors.first().row_number, 3)

        # Deleting the job cascades to row errors
        job.delete()
        self.assertFalse(DataImportRowError.objects.filter(id=row_err.id).exists())

    # -------------------------------------------------------------
    # 9. ClinicAuditEvent
    # -------------------------------------------------------------
    def test_audit_event_records_properly(self):
        event = ClinicAuditEvent.objects.create(
            clinic=self.clinic_a,
            actor=self.user_a,
            action="update_working_hours",
            target_type="ClinicProfile",
            target_id=str(self.clinic_a.clinic_id),
            payload={"new_hours": "09:00-18:00"},
        )
        self.assertEqual(event.clinic, self.clinic_a)
        self.assertEqual(event.action, "update_working_hours")
        self.assertEqual(event.payload["new_hours"], "09:00-18:00")
