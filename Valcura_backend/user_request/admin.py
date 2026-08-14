from django.contrib import admin
from .models import UserRequest, MessageLog

@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user_message', 'is_missed_call', 'created_at')
    search_fields = ('phone_number', 'user_message')
    list_filter = ('is_missed_call', 'created_at')

@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ('ph_number', 'Language', 'Service_Type')
