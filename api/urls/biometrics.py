from django.urls import path
from ..views.biometrics import (
    StudentListView, 
    EnrollFingerprintView,
    VerifyFingerprintView,
    BiometricStationListCreateView,
    BiometricStationDetailView
)

urlpatterns = [
    path('students/', StudentListView.as_view(), name='biometric-students'),
    path('enroll/', EnrollFingerprintView.as_view(), name='biometric-enroll'),
    path('verify/', VerifyFingerprintView.as_view(), name='biometric-verify'),
    
    # Management Endpoints
    path('stations/', BiometricStationListCreateView.as_view(), name='Station-list-create'),
    path('stations/<int:pk>/', BiometricStationDetailView.as_view(), name='station-detail'),
]
