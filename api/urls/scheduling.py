from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.scheduling import PeriodViewSet, TimetableViewSet, AttendanceViewSet

router = DefaultRouter()
router.register(r'periods', PeriodViewSet)
router.register(r'timetables', TimetableViewSet)
router.register(r'attendance', AttendanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
