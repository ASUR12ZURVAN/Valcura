import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class HospitalUser(AbstractUser):
    """Custom user model for hospital/clinic staff"""

    clinic = models.ForeignKey(
        "ClinicProfile",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("receptionist", "Receptionist"),
            ("doctor", "Doctor"),
            ("manager", "Manager"),
        ],
        default="receptionist",
    )
    phone_number = models.CharField(max_length=20, blank=True)
    is_hospital_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} - {self.clinic.clinic_name if self.clinic else 'No Clinic'} ({self.role})"

    class Meta:
        verbose_name = "Hospital User"
        verbose_name_plural = "Hospital Users"


class UserRequest(models.Model):
    ph_number = models.IntegerField()
    Language = models.CharField(max_length=200)
    Service_Type = models.CharField(max_length=200)


class MessageLog(models.Model):
    clinic = models.ForeignKey(
        "ClinicProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="messages",
    )
    phone_number = models.CharField(max_length=50)
    user_message = models.TextField(null=True, blank=True)
    ai_response = models.TextField()
    is_missed_call = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default="WhatsApp")
    status = models.CharField(max_length=50, default="Received")
    sheet_synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["clinic", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.source}] {self.phone_number} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class MetaTemplate(models.Model):
    template_id = models.CharField(max_length=100, unique=True, primary_key=True)
    meta_template_name = models.CharField(max_length=200)
    library = models.CharField(max_length=50)
    message_name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    treatment = models.CharField(max_length=100, blank=True)
    objection = models.CharField(max_length=100, blank=True)
    trigger = models.CharField(max_length=200)
    day = models.CharField(max_length=50)
    header_type = models.CharField(max_length=50, blank=True)
    header_text = models.TextField(blank=True)
    meta_approved_body = models.TextField()
    cta_type = models.CharField(max_length=50, blank=True)
    cta_value = models.CharField(max_length=200, blank=True)
    media_type = models.CharField(max_length=50, blank=True)
    media_asset_id = models.CharField(max_length=200, blank=True)
    variable_mapping = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    ai_personalization_inputs = models.TextField(blank=True)
    ai_writing_rules = models.TextField(blank=True)
    workflow_exit_condition = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    meta_templates = models.TextField(blank=True)
    meta_mapping = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["library"]),
            models.Index(fields=["category"]),
            models.Index(fields=["trigger"]),
            models.Index(fields=["treatment"]),
            models.Index(fields=["objection"]),
        ]

    def __str__(self):
        return f"{self.template_id} - {self.meta_template_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# Excel Database Models based on Valcura Master Revenue Intelligence Database


class ClinicProfile(models.Model):
    ONBOARDING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("profile_complete", "Profile Complete"),
        ("integration_pending", "Integration Pending"),
        ("data_import_pending", "Data Import Pending"),
        ("test_pending", "Test Pending"),
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("offboarding", "Offboarding"),
        ("closed", "Closed"),
    ]

    clinic_id = models.CharField(max_length=50, unique=True, primary_key=True)
    tenant_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    onboarding_status = models.CharField(
        max_length=32,
        choices=ONBOARDING_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    clinic_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    locality = models.CharField(max_length=100)
    clinic_type = models.CharField(max_length=50)
    chair_count = models.IntegerField()
    primary_specialty = models.CharField(max_length=100)
    monthly_revenue_baseline_inr = models.DecimalField(max_digits=12, decimal_places=2)
    reception_team_size = models.IntegerField()
    onboarding_date = models.DateField()
    crm_status = models.CharField(max_length=50)
    crm_name = models.CharField(max_length=100, blank=True)
    crm_integration_mode = models.CharField(max_length=50, blank=True)
    valcura_plan = models.CharField(max_length=50)
    active_status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.clinic_name} ({self.clinic_id})"


class ClinicMembership(models.Model):
    ROLE_CHOICES = [
        ("owner", "Clinic Owner"),
        ("admin", "Clinic Admin"),
        ("manager", "Manager"),
        ("receptionist", "Receptionist"),
        ("clinician", "Clinician"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("invited", "Invited"),
        ("suspended", "Suspended"),
        ("inactive", "Inactive"),
    ]

    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.PROTECT, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships"
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="receptionist")
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="active", db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "user"], name="uniq_clinic_user_membership"
            ),
        ]
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.clinic.clinic_name} ({self.role})"


class ClinicInvitation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=32, choices=ClinicMembership.ROLE_CHOICES, default="receptionist"
    )
    token_hash = models.CharField(max_length=128, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invite for {self.email} to {self.clinic.clinic_name} ({self.status})"


class ClinicIntegration(models.Model):
    PROVIDER_CHOICES = [
        ("whatsapp_cloud", "Meta WhatsApp Cloud API"),
        ("whatsapp_twilio", "Twilio WhatsApp"),
        ("google_sheets", "Google Sheets"),
        ("macrodroid", "MacroDroid"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("error", "Error"),
        ("revoked", "Revoked"),
    ]

    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="integrations"
    )
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    external_account_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="e.g. Meta Phone Number ID, WABA ID, or Spreadsheet ID",
    )
    secret_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reference/alias to secret in secret store, NOT raw token",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Non-sensitive configuration (e.g. sheet names, webhook settings)",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    last_health_check = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_account_id"],
                name="uniq_provider_external_account",
            ),
            models.UniqueConstraint(
                fields=["clinic", "provider"], name="uniq_clinic_provider"
            ),
        ]

    def __str__(self):
        return (
            f"{self.clinic.clinic_name} - {self.provider} ({self.external_account_id})"
        )


class ClinicAuditEvent(models.Model):
    clinic = models.ForeignKey(
        ClinicProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"[{self.action}] on {self.target_type}:{self.target_id} by {self.actor}"


class TeamMaster(models.Model):
    staff_id = models.CharField(max_length=50, unique=True, primary_key=True)
    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="staff"
    )
    staff_name = models.CharField(max_length=200)
    role = models.CharField(max_length=50)
    whatsapp_number = models.CharField(max_length=20)
    active_status = models.BooleanField(default=True)
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff_name} - {self.role} ({self.staff_id})"


class PatientContact(models.Model):
    patient_id = models.CharField(max_length=50, unique=True, primary_key=True)
    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="patients"
    )
    external_crm_id = models.CharField(max_length=100, blank=True)
    patient_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, db_index=True)
    phone_hash_analytics = models.CharField(max_length=100, blank=True)
    new_existing_patient = models.CharField(max_length=20)
    preferred_language = models.CharField(max_length=50, default="English")
    communication_allowed = models.BooleanField(default=True)
    data_source = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_name} - {self.phone_number}"


class Opportunity(models.Model):
    opportunity_id = models.CharField(max_length=50, unique=True, primary_key=True)
    patient = models.ForeignKey(
        PatientContact, on_delete=models.CASCADE, related_name="opportunities"
    )
    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="opportunities"
    )
    external_crm_opportunity_id = models.CharField(max_length=100, blank=True)
    inquiry_date_time = models.DateTimeField()
    inquiry_type = models.CharField(max_length=50)
    lead_source = models.CharField(max_length=50)
    treatment_concern = models.CharField(max_length=200)
    appointment_date_time = models.DateTimeField(null=True, blank=True)
    consultation_date_time = models.DateTimeField(null=True, blank=True)
    doctor = models.ForeignKey(
        TeamMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )
    treatment_advised = models.CharField(max_length=200, blank=True)
    why_treatment_advised = models.TextField(blank=True)
    ats_value_inr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    ats_category = models.CharField(max_length=50, blank=True)
    urgency_level = models.CharField(max_length=50, blank=True)
    initial_objection = models.CharField(max_length=200, blank=True)
    current_objection = models.CharField(max_length=200, blank=True)
    opportunity_status = models.CharField(max_length=50, db_index=True)
    last_interaction_date_time = models.DateTimeField(null=True, blank=True)
    next_followup_date_time = models.DateTimeField(null=True, blank=True)
    treatment_start_date = models.DateField(null=True, blank=True)
    treatment_completion_date = models.DateField(null=True, blank=True)
    realized_revenue_inr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    lost_reason = models.TextField(blank=True)
    nps_score = models.IntegerField(null=True, blank=True)
    conversion_probability_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    weighted_pipeline_value_inr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    revenue_at_risk_inr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    conversion_days = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.opportunity_id} - {self.patient.patient_name} ({self.opportunity_status})"

    class Meta:
        indexes = [
            models.Index(fields=["opportunity_status", "next_followup_date_time"]),
            models.Index(fields=["clinic", "opportunity_status"]),
        ]


class InteractionLog(models.Model):
    interaction_id = models.CharField(max_length=50, unique=True, primary_key=True)
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="interactions"
    )
    patient = models.ForeignKey(
        PatientContact, on_delete=models.CASCADE, related_name="interactions"
    )
    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="interactions"
    )
    staff = models.ForeignKey(
        TeamMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interactions",
    )
    event_date_time = models.DateTimeField()
    channel = models.CharField(max_length=50)
    direction = models.CharField(max_length=20)
    interaction_type = models.CharField(max_length=50)
    sequence_name = models.CharField(max_length=100, blank=True)
    day_in_sequence = models.IntegerField(null=True, blank=True)
    message_variant_id = models.CharField(max_length=50, blank=True)
    call_objective = models.TextField(blank=True)
    outcome = models.CharField(max_length=100, blank=True)
    response_status = models.CharField(max_length=50, blank=True)
    previous_objection = models.CharField(max_length=200, blank=True)
    observed_objection = models.CharField(max_length=200, blank=True)
    next_followup_date_time = models.DateTimeField(null=True, blank=True)
    compliance_flag = models.BooleanField(null=True, blank=True)
    delivery_status = models.CharField(max_length=50, blank=True)
    ai_summary = models.TextField(blank=True)
    conversion_fingerprint_flag = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interaction_id} - {self.patient.patient_name} ({self.interaction_type})"

    class Meta:
        indexes = [
            models.Index(fields=["opportunity", "event_date_time"]),
            models.Index(fields=["patient", "event_date_time"]),
        ]


class TreatmentConfig(models.Model):
    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="treatment_configs"
    )
    treatment = models.CharField(max_length=200)
    default_ats_value_inr = models.DecimalField(max_digits=12, decimal_places=2)
    ats_category = models.CharField(max_length=50)
    expected_sittings = models.IntegerField()
    followup_track = models.CharField(max_length=50)
    default_urgency = models.CharField(max_length=50)
    active_status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.treatment} - {self.clinic.clinic_name}"


class SystemConfig(models.Model):
    config_type = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    display_value = models.CharField(max_length=200)
    treatment = models.CharField(max_length=200, blank=True)
    objection = models.CharField(max_length=200, blank=True)
    ats_category = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=50, default="English")
    sequence_name = models.CharField(max_length=100)
    day_in_sequence = models.IntegerField()
    meta_template_name = models.CharField(max_length=200)
    active_status = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default="v1")

    class Meta:
        unique_together = [["code", "version"]]

    def __str__(self):
        return f"{self.code} - {self.display_value} ({self.sequence_name})"


class MonthlyMetrics(models.Model):
    month = models.DateField()
    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="monthly_metrics"
    )
    confirmed_revenue_inr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    inquiry_count = models.IntegerField(default=0)
    consultation_count = models.IntegerField(default=0)
    treatment_started_count = models.IntegerField(default=0)
    inquiry_to_consult_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    consult_to_treatment_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    missed_call_recovery_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    followup_compliance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    pipeline_value_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_at_risk_inr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    recovered_revenue_inr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    avg_nps = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    data_quality_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    forecast_30d_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    forecast_60d_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    forecast_90d_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = [["month", "clinic"]]

    def __str__(self):
        return f"{self.clinic.clinic_name} - {self.month.strftime('%Y-%m')}"


class WorkflowState(models.Model):
    clinic = models.ForeignKey(
        ClinicProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="workflow_states",
    )
    phone_number = models.CharField(max_length=50, db_index=True)
    current_library = models.CharField(max_length=50, blank=True)
    current_step = models.IntegerField(default=0)
    last_template_id = models.CharField(max_length=50, blank=True)
    treatment = models.CharField(max_length=100, blank=True)
    objection = models.CharField(max_length=100, blank=True)
    appointment_booked = models.BooleanField(default=False)
    last_message_date = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "phone_number"],
                name="uniq_workflow_state_clinic_phone",
            ),
        ]
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["current_library"]),
            models.Index(fields=["clinic", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.phone_number} - Library: {self.current_library}, Step: {self.current_step}"


class WebhookEvent(models.Model):
    STATUS_CHOICES = [
        ("received", "Received"),
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("ignored", "Ignored"),
    ]

    clinic = models.ForeignKey(
        ClinicProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    provider = models.CharField(max_length=32)
    provider_event_id = models.CharField(max_length=128, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="received", db_index=True
    )
    processing_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_event_id"],
                name="uniq_webhook_provider_event",
            ),
        ]
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["received_at"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_event_id} ({self.status})"


class DataImportJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("validating", "Validating"),
        ("importing", "Importing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    clinic = models.ForeignKey(
        ClinicProfile, on_delete=models.CASCADE, related_name="import_jobs"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    file_name = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    error_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["clinic", "status"]),
        ]

    def __str__(self):
        return f"Import {self.file_name} for {self.clinic.clinic_name} ({self.status})"


class DataImportRowError(models.Model):
    job = models.ForeignKey(
        DataImportJob, on_delete=models.CASCADE, related_name="row_errors"
    )
    row_number = models.IntegerField()
    field_name = models.CharField(max_length=64, blank=True)
    error_message = models.TextField()
    raw_row_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["job", "row_number"]),
        ]

    def __str__(self):
        return f"Error row {self.row_number} in job {self.job_id}: {self.error_message}"
