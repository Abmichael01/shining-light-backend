from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from api.models.user import User
from api.models.academic import Session, SessionTerm
from api.models.student import Student
from .structure import FeeType, PaymentPurpose

class FeePayment(models.Model):
    """Fee Payment - Individual payment records"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'), ('bank_transfer', 'Bank Transfer'), ('card', 'Card/POS'),
        ('cheque', 'Cheque'), ('online', 'Online Payment'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    installment_number = models.PositiveIntegerField(default=1)
    payment_purpose = models.ForeignKey(PaymentPurpose, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_payments')
    session_term = models.ForeignKey(SessionTerm, on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_payments')
    
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    reference_number = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=50, blank=True, unique=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='fee_payments_processed')
    
    class Meta:
        db_table = 'fee_payments'
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'fee_type']),
            models.Index(fields=['session', 'session_term']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['receipt_number']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.fee_type.name} - ₦{self.amount:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)
    
    def _generate_receipt_number(self):
        year = timezone.now().year
        year_start = timezone.datetime(year, 1, 1, tzinfo=timezone.get_current_timezone())
        for attempt in range(100):
            count = FeePayment.objects.filter(created_at__gte=year_start).count() + 1 + attempt
            receipt_number = f"RCP-{year}-{count:06d}"
            if not FeePayment.objects.filter(receipt_number=receipt_number).exists():
                return receipt_number
        import time
        timestamp = int(time.time() * 1000) % 1000000
        return f"RCP-{year}-{timestamp:06d}"
    
    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Payment amount must be greater than zero.'})
        if not self.fee_type.is_active:
            raise ValidationError({'fee_type': 'Cannot make payment for inactive fee type.'})
        
        filters = {'student': self.student, 'fee_type': self.fee_type}
        if self.fee_type.is_recurring_per_term and self.session_term:
            filters['session_term'] = self.session_term
        elif self.session:
            filters['session'] = self.session
        
        existing_payments = FeePayment.objects.filter(**filters)
        if self.pk:
            existing_payments = existing_payments.exclude(pk=self.pk)
        
        total_paid = existing_payments.aggregate(total=Sum('amount'))['total'] or 0
        applicable_amount = self.fee_type.get_applicable_amount(self.student)
        if total_paid >= applicable_amount:
            raise ValidationError({'amount': f'This fee is already fully paid (₦{total_paid:,.2f}).'})
        
        remaining = applicable_amount - total_paid
        if self.amount > remaining:
            raise ValidationError({'amount': f'Payment amount (₦{self.amount:,.2f}) exceeds remaining balance (₦{remaining:,.2f}).'})
        
        installments_made = existing_payments.count()
        if installments_made >= self.fee_type.max_installments:
            raise ValidationError({'installment_number': f'Maximum {self.fee_type.max_installments} installments allowed.'})
        
        if not self.installment_number or self.installment_number == 1:
            self.installment_number = installments_made + 1
            
        if self.fee_type.applicable_classes.exists():
            if self.student.class_model and not self.fee_type.is_applicable_to_class(self.student.class_model.id):
                raise ValidationError({'fee_type': f'This fee does not apply to {self.student.class_model.name}.'})
