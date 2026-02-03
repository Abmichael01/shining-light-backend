from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.communication import CommunicationTemplateViewSet

router = DefaultRouter()
router.register(r'templates', CommunicationTemplateViewSet, basename='communication-templates')

urlpatterns = [
    path('', include(router.urls)),
]
