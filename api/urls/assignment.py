from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.assignment import AssignmentViewSet, AssignmentSubmissionViewSet

router = DefaultRouter()
router.register(r'submissions', AssignmentSubmissionViewSet, basename='assignment-submission')
router.register(r'', AssignmentViewSet, basename='assignment')

urlpatterns = [
    path('assignments/', include(router.urls)),
]
