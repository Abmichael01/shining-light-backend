from .base import FeeTypeViewSet, FeePaymentViewSet, PDFRenderer
from .actions import FeeActionsMixin
from .paystack import PaystackMixin

# Combine Mixins into FeePaymentViewSet
FeePaymentViewSet.__bases__ = (FeeActionsMixin, PaystackMixin) + FeePaymentViewSet.__bases__

__all__ = ['FeeTypeViewSet', 'FeePaymentViewSet', 'PDFRenderer']
