from django.db import models
from django.core.cache import cache


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
        # Invalidate cache when template is updated
        cache_key = f"template_{self.template_id}"
        cache.delete(cache_key)
        cache.delete("all_templates_cache")


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
