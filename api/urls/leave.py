from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.leave import LeaveRequestViewSet

router = DefaultRouter()
# /api/leaves/
router.register(r'leaves', LeaveRequestViewSet, basename='leave-request')

urlpatterns = [
    path('', include(router.urls)),
]
