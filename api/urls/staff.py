"""
URL routes for staff-related API endpoints
"""
from rest_framework.routers import DefaultRouter
from api.views.staff import (
    StaffViewSet,
    StaffEducationViewSet,
    SalaryGradeViewSet,
    StaffSalaryViewSet,
    SalaryPaymentViewSet,
    LoanApplicationViewSet,
    LoanPaymentViewSet,
    LoanTenureViewSet
)

router = DefaultRouter()

# Staff management
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'staff-education', StaffEducationViewSet, basename='staff-education')

# Salary management
router.register(r'salary-grades', SalaryGradeViewSet, basename='salary-grade')
router.register(r'staff-salaries', StaffSalaryViewSet, basename='staff-salary')
router.register(r'salary-payments', SalaryPaymentViewSet, basename='salary-payment')

# Loan management
router.register(r'loan-applications', LoanApplicationViewSet, basename='loan-application')
router.register(r'loan-payments', LoanPaymentViewSet, basename='loan-payment')
router.register(r'loan-tenures', LoanTenureViewSet, basename='loan-tenure')

urlpatterns = router.urls



