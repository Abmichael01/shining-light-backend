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
    LoanTenureViewSet,
    StaffWalletTransactionViewSet
)

router = DefaultRouter()

# Staff management
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'staff-education', StaffEducationViewSet, basename='staff-education')

# Salary management
router.register(r'salary-grades', SalaryGradeViewSet, basename='salary-grade')
router.register(r'staff-salaries', StaffSalaryViewSet, basename='staff-salary')
router.register(r'salary-payments', SalaryPaymentViewSet, basename='salary-payment')

# Wallet & Transactions
router.register(r'wallet-transactions', StaffWalletTransactionViewSet, basename='staff-wallet-transaction')

# Loan management
router.register(r'loan-applications', LoanApplicationViewSet, basename='loan-application')
router.register(r'loan-payments', LoanPaymentViewSet, basename='loan-payment')
router.register(r'loan-tenures', LoanTenureViewSet, basename='loan-tenure')

# Withdrawal management
from api.views.staff import WithdrawalRequestViewSet, StaffBeneficiaryViewSet
router.register(r'withdrawal-requests', WithdrawalRequestViewSet, basename='withdrawal-request')
router.register(r'beneficiaries', StaffBeneficiaryViewSet, basename='staff-beneficiary')

urlpatterns = router.urls



