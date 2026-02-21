from django.urls import path
from api.views.messaging import SendSMSView, BulkMessagingView, GuardianMessagingView

urlpatterns = [
    path('sms/send/', SendSMSView.as_view(), name='send-sms'),
    path('bulk/', BulkMessagingView.as_view(), name='bulk-messaging'),
    path('guardian/', GuardianMessagingView.as_view(), name='guardian-messaging'),
]
