from django.db import models


class UserRequest(models.Model):
    ph_number = models.IntegerField()
    Language = models.CharField(max_length=200)
    Service_Type = models.CharField(max_length=200)

class MessageLog(models.Model):
    phone_number = models.CharField(max_length=50)
    user_message = models.TextField(null=True, blank=True)
    ai_response = models.TextField()
    is_missed_call = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
