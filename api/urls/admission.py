"""
Admission URL Configuration
Routes for admission portal endpoints
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.admission import (
    AdmissionSettingsViewSet,
    PaymentPurposeViewSet,
    admission_metadata,
    send_otp,
    verify_and_register,
    register_applicant,
    change_applicant_password,
    applicant_dashboard,
    applicant_biodata,
    applicant_guardians,
    applicant_guardian_detail,
    applicant_documents,
    applicant_document_detail,
    payment_status,
    initialize_payment,
    verify_payment,
    paystack_webhook,
    submit_application,
    application_slip,
    notify_applicants,
    count_filtered_applicants,
    submit_bank_transfer,
    list_bank_transfers,
    verify_bank_transfer,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'settings', AdmissionSettingsViewSet, basename='admission-settings')
router.register(r'payment-purposes', PaymentPurposeViewSet, basename='payment-purposes')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Public endpoints
    path('metadata/', admission_metadata, name='admission-metadata'),
    path('send-otp/', send_otp, name='admission-send-otp'),
    path('verify-otp/', verify_and_register, name='admission-verify-otp'),
    path('register/', register_applicant, name='admission-register'),  # Legacy
    
    # Authenticated applicant endpoints
    path('change-password/', change_applicant_password, name='admission-change-password'),
    path('dashboard/', applicant_dashboard, name='admission-dashboard'),
    
    # Biodata
    path('biodata/', applicant_biodata, name='admission-biodata'),
    
    # Guardians
    path('guardians/', applicant_guardians, name='admission-guardians'),
    path('guardians/<int:pk>/', applicant_guardian_detail, name='admission-guardian-detail'),
    
    # Documents
    path('documents/', applicant_documents, name='admission-documents'),
    path('documents/<int:pk>/', applicant_document_detail, name='admission-document-detail'),
    
    # Payment
    path('payment/status/', payment_status, name='admission-payment-status'),
    path('payment/initialize/', initialize_payment, name='admission-payment-initialize'),
    path('payment/verify/', verify_payment, name='admission-payment-verify'),
    path('payment/webhook/', paystack_webhook, name='paystack-webhook'),
    path('payment/bank-transfer/', submit_bank_transfer, name='admission-submit-bank-transfer'),
    
    # Admin Verification
    path('admin/bank-transfers/', list_bank_transfers, name='admission-admin-list-bank-transfers'),
    path('admin/bank-transfers/<int:pk>/verify/', verify_bank_transfer, name='admission-admin-verify-bank-transfer'),
    
    # Submission
    path('submit/', submit_application, name='admission-submit'),
    path('slip/', application_slip, name='admission-slip'),
    
    # Notifications
    path('notify-applicants/', notify_applicants, name='admission-notify-applicants'),
    path('count-filtered-applicants/', count_filtered_applicants, name='admission-count-filtered-applicants'),
]
