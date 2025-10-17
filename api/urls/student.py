from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    StudentViewSet,
    BioDataViewSet,
    GuardianViewSet,
    DocumentViewSet,
    BiometricViewSet,
    StudentSubjectViewSet
)

router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'biodata', BioDataViewSet, basename='biodata')
router.register(r'guardians', GuardianViewSet, basename='guardian')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'biometrics', BiometricViewSet, basename='biometric')
router.register(r'student-subjects', StudentSubjectViewSet, basename='studentsubject')

urlpatterns = router.urls


