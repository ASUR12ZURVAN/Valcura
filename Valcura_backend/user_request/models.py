from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


class HospitalUser(AbstractUser):
    """Custom user model for hospital/clinic staff"""
    clinic = models.ForeignKey('ClinicProfile', on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Admin'),
        ('receptionist', 'Receptionist'),
        ('doctor', 'Doctor'),
        ('manager', 'Manager'),
    ], default='receptionist')
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
    phone_number = models.CharField(max_length=50)
    user_message = models.TextField(null=True, blank=True)
    ai_response = models.TextField()
    is_missed_call = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default="WhatsApp")
    status = models.CharField(max_length=50, default="Received")
    sheet_synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

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
            models.Index(fields=['library']),
            models.Index(fields=['category']),
            models.Index(fields=['trigger']),
            models.Index(fields=['treatment']),
            models.Index(fields=['objection']),
        ]

    def __str__(self):
        return f"{self.template_id} - {self.meta_template_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# Excel Database Models based on Valcura Master Revenue Intelligence Database

class ClinicProfile(models.Model):
    clinic_id = models.CharField(max_length=50, unique=True, primary_key=True)
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


class TeamMaster(models.Model):
    staff_id = models.CharField(max_length=50, unique=True, primary_key=True)
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.CASCADE, related_name='staff')
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
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.CASCADE, related_name='patients')
    external_crm_id = models.CharField(max_length=100, blank=True)
    patient_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, db_index=True)
    phone_hash_analytics = models.CharField(max_length=100, blank=True)
    new_existing_patient = models.CharField(max_length=20)
    preferred_language = models.CharField(max_length=50, default='English')
    communication_allowed = models.BooleanField(default=True)
    data_source = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_name} - {self.phone_number}"


class Opportunity(models.Model):
    opportunity_id = models.CharField(max_length=50, unique=True, primary_key=True)
    patient = models.ForeignKey(PatientContact, on_delete=models.CASCADE, related_name='opportunities')
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.CASCADE, related_name='opportunities')
    external_crm_opportunity_id = models.CharField(max_length=100, blank=True)
    inquiry_date_time = models.DateTimeField()
    inquiry_type = models.CharField(max_length=50)
    lead_source = models.CharField(max_length=50)
    treatment_concern = models.CharField(max_length=200)
    appointment_date_time = models.DateTimeField(null=True, blank=True)
    consultation_date_time = models.DateTimeField(null=True, blank=True)
    doctor = models.ForeignKey(TeamMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    treatment_advised = models.CharField(max_length=200, blank=True)
    why_treatment_advised = models.TextField(blank=True)
    ats_value_inr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ats_category = models.CharField(max_length=50, blank=True)
    urgency_level = models.CharField(max_length=50, blank=True)
    initial_objection = models.CharField(max_length=200, blank=True)
    current_objection = models.CharField(max_length=200, blank=True)
    opportunity_status = models.CharField(max_length=50, db_index=True)
    last_interaction_date_time = models.DateTimeField(null=True, blank=True)
    next_followup_date_time = models.DateTimeField(null=True, blank=True)
    treatment_start_date = models.DateField(null=True, blank=True)
    treatment_completion_date = models.DateField(null=True, blank=True)
    realized_revenue_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lost_reason = models.TextField(blank=True)
    nps_score = models.IntegerField(null=True, blank=True)
    conversion_probability_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weighted_pipeline_value_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_at_risk_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conversion_days = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.opportunity_id} - {self.patient.patient_name} ({self.opportunity_status})"

    class Meta:
        indexes = [
            models.Index(fields=['opportunity_status', 'next_followup_date_time']),
            models.Index(fields=['clinic', 'opportunity_status']),
        ]


class InteractionLog(models.Model):
    interaction_id = models.CharField(max_length=50, unique=True, primary_key=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='interactions')
    patient = models.ForeignKey(PatientContact, on_delete=models.CASCADE, related_name='interactions')
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.CASCADE, related_name='interactions')
    staff = models.ForeignKey(TeamMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='interactions')
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
            models.Index(fields=['opportunity', 'event_date_time']),
            models.Index(fields=['patient', 'event_date_time']),
        ]


class TreatmentConfig(models.Model):
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.CASCADE, related_name='treatment_configs')
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
    language = models.CharField(max_length=50, default='English')
    sequence_name = models.CharField(max_length=100)
    day_in_sequence = models.IntegerField()
    meta_template_name = models.CharField(max_length=200)
    active_status = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default='v1')
    
    class Meta:
        unique_together = [['code', 'version']]

    def __str__(self):
        return f"{self.code} - {self.display_value} ({self.sequence_name})"


class MonthlyMetrics(models.Model):
    month = models.DateField()
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.CASCADE, related_name='monthly_metrics')
    confirmed_revenue_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inquiry_count = models.IntegerField(default=0)
    consultation_count = models.IntegerField(default=0)
    treatment_started_count = models.IntegerField(default=0)
    inquiry_to_consult_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    consult_to_treatment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    missed_call_recovery_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    followup_compliance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pipeline_value_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_at_risk_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recovered_revenue_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_nps = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    data_quality_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    forecast_30d_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    forecast_60d_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    forecast_90d_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = [['month', 'clinic']]

    def __str__(self):
        return f"{self.clinic.clinic_name} - {self.month.strftime('%Y-%m')}"


class WorkflowState(models.Model):
    phone_number = models.CharField(max_length=50, unique=True)
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
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['current_library']),
        ]

    def __str__(self):
        return f"{self.phone_number} - Library: {self.current_library}, Step: {self.current_step}"
