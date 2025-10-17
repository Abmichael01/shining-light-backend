"""
Fee-related models for the School Management System
Handles fee types and student payments
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from api.models.user import User
from api.models.academic import School, Class, Session, SessionTerm
from api.models.student import Student


class FeeType(models.Model):
    """
    Fee Type - Define different types of fees (Admission, Tuition, etc.)
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card/POS'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200, help_text='e.g., Admission Fee, Tuition Fee, Sport Fee')
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='fee_types')
    
    # Applicability
    applicable_classes = models.ManyToManyField(
        Class,
        blank=True,
        related_name='fee_types',
        help_text='Leave empty to apply to all classes in the school'
    )
    
    # Payment Options
    max_installments = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of installments allowed (1 = pay in full only)'
    )
    
    # Classification
    is_mandatory = models.BooleanField(
        default=True,
        help_text='Is this fee required for all students?'
    )
    is_recurring_per_term = models.BooleanField(
        default=False,
        help_text='Does student pay this fee every term?'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Is this fee currently active?'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fee_types_created'
    )
    
    class Meta:
        db_table = 'fee_types'
        ordering = ['school', 'name']
        unique_together = [['school', 'name']]
        indexes = [
            models.Index(fields=['school', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.school.name} (₦{self.amount:,.2f})"
    
    def clean(self):
        """Validate fee type"""
        super().clean()
        
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Amount must be greater than zero.'
            })
        
        if self.max_installments < 1:
            raise ValidationError({
                'max_installments': 'Maximum installments must be at least 1.'
            })
    
    def is_applicable_to_class(self, class_id):
        """Check if this fee applies to a specific class"""
        # If no classes specified, applies to all
        if not self.applicable_classes.exists():
            return True
        # Otherwise, check if class is in the list
        return self.applicable_classes.filter(id=class_id).exists()
    
    def get_student_total_paid(self, student_id, session=None, session_term=None):
        """Get total amount paid by a student for this fee"""
        filters = {
            'student_id': student_id,
            'fee_type': self,
        }
        
        if self.is_recurring_per_term and session_term:
            filters['session_term_id'] = session_term
        elif session:
            filters['session_id'] = session
        
        total = FeePayment.objects.filter(**filters).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return total
    
    def get_student_remaining(self, student_id, session=None, session_term=None):
        """Get remaining amount for a student"""
        total_paid = self.get_student_total_paid(student_id, session, session_term)
        return max(0, self.amount - total_paid)
    
    def get_student_status(self, student_id, session=None, session_term=None):
        """Get payment status for a student"""
        total_paid = self.get_student_total_paid(student_id, session, session_term)
        
        if total_paid >= self.amount:
            return 'paid'
        elif total_paid > 0:
            return 'partial'
        else:
            return 'unpaid'


class FeePayment(models.Model):
    """
    Fee Payment - Individual payment records
    Students can make multiple payments (installments) for a single fee
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card/POS'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ]
    
    # Core Information
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    fee_type = models.ForeignKey(FeeType, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Installment Tracking
    installment_number = models.PositiveIntegerField(
        default=1,
        help_text='Which installment is this (1, 2, 3, etc.)'
    )
    
    # Session/Term Tracking (for recurring fees)
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fee_payments',
        help_text='Applicable for recurring fees'
    )
    session_term = models.ForeignKey(
        SessionTerm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fee_payments',
        help_text='Applicable for per-term recurring fees'
    )
    
    # Payment Details
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    reference_number = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=50, blank=True, unique=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fee_payments_processed'
    )
    
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
        return f"{self.student.get_full_name()} - {self.fee_type.name} - ₦{self.amount:,.2f} (Installment {self.installment_number})"
    
    def save(self, *args, **kwargs):
        """Auto-generate receipt number if not provided"""
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)
    
    def _generate_receipt_number(self):
        """Generate unique receipt number: RCP-YYYY-XXXXXX"""
        year = timezone.now().year
        
        # Get count of payments this year
        year_start = timezone.datetime(year, 1, 1, tzinfo=timezone.get_current_timezone())
        count = FeePayment.objects.filter(
            created_at__gte=year_start
        ).count() + 1
        
        # Format: RCP-2025-000001
        return f"RCP-{year}-{count:06d}"
    
    def clean(self):
        """Validate payment"""
        super().clean()
        
        # Validate amount
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Payment amount must be greater than zero.'
            })
        
        # Check if fee is active
        if not self.fee_type.is_active:
            raise ValidationError({
                'fee_type': 'Cannot make payment for inactive fee type.'
            })
        
        # Validate against total already paid
        filters = {
            'student': self.student,
            'fee_type': self.fee_type,
        }
        
        if self.fee_type.is_recurring_per_term and self.session_term:
            filters['session_term'] = self.session_term
        elif self.session:
            filters['session'] = self.session
        
        # Exclude current payment if editing
        existing_payments = FeePayment.objects.filter(**filters)
        if self.pk:
            existing_payments = existing_payments.exclude(pk=self.pk)
        
        total_paid = existing_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Check if already fully paid
        if total_paid >= self.fee_type.amount:
            raise ValidationError({
                'amount': f'This fee is already fully paid (₦{total_paid:,.2f}).'
            })
        
        # Check if payment exceeds remaining
        remaining = self.fee_type.amount - total_paid
        if self.amount > remaining:
            raise ValidationError({
                'amount': f'Payment amount (₦{self.amount:,.2f}) exceeds remaining balance (₦{remaining:,.2f}).'
            })
        
        # Check installment limit
        installments_made = existing_payments.count()
        if installments_made >= self.fee_type.max_installments:
            raise ValidationError({
                'installment_number': f'Maximum {self.fee_type.max_installments} installments allowed. Already made {installments_made} payments.'
            })
        
        # Auto-set installment number if not provided
        if not self.installment_number or self.installment_number == 1:
            self.installment_number = installments_made + 1
        
        # Validate student is in applicable class
        if self.fee_type.applicable_classes.exists():
            if self.student.class_model and not self.fee_type.is_applicable_to_class(self.student.class_model.id):
                raise ValidationError({
                    'fee_type': f'This fee does not apply to {self.student.class_model.name}.'
                })


