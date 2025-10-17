"""
URL routes for fee-related API endpoints
"""
from rest_framework.routers import DefaultRouter
from api.views.fee import FeeTypeViewSet, FeePaymentViewSet

router = DefaultRouter()

router.register(r'fee-types', FeeTypeViewSet, basename='fee-type')
router.register(r'fee-payments', FeePaymentViewSet, basename='fee-payment')

urlpatterns = router.urls


