"""
URL configuration for Valcura_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from user_request.views import chat_rag, whatsapp_webhook, missed_call_webhook, message_list, dashboard
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat-rag/', chat_rag, name='chat-rag'),
    path('api/whatsapp/webhook/', whatsapp_webhook, name='whatsapp-webhook'),
    path('api/missed-call/webhook/', missed_call_webhook, name='missed-call-webhook'),
    
    # JWT Auth Endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Analytics / Dashboard API
    path('api/messages/', message_list, name='message-list'),
    
    # Frontend Template
    path('dashboard/', dashboard, name='dashboard'),
]
