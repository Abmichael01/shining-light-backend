from rest_framework.routers import DefaultRouter
from api.views import (
    SchoolViewSet, 
    SessionViewSet, 
    SessionTermViewSet,
    ClassViewSet,
    DepartmentViewSet,
    SubjectGroupViewSet,
    SubjectViewSet
)

router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'session-terms', SessionTermViewSet, basename='session-term')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'subject-groups', SubjectGroupViewSet, basename='subject-group')
router.register(r'subjects', SubjectViewSet, basename='subject')

urlpatterns = router.urls

