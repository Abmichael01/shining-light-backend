from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from api.models.user import User
from .staff import Staff

class LoanTenure(models.Model):
    """Pre-defined loan tenures/plans created by Admin"""
    name = models.CharField(max_length=100, help_text="e.g. 6 Months Plan")
    duration_months = models.PositiveIntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Interest rate (percentage)")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loan_tenures'
        ordering = ['duration_months']
    
    def __str__(self):
        return f"{self.name} ({self.interest_rate}%)"


class LoanApplication(models.Model):
    """Staff loan applications"""
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'), ('completed', 'Completed'), ('defaulted', 'Defaulted'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='loan_applications')
    tenure = models.ForeignKey(LoanTenure, on_delete=models.PROTECT, related_name='applications', null=True, blank=True)
    application_number = models.CharField(max_length=20, unique=True, blank=True)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    repayment_period_months = models.PositiveIntegerField()
    monthly_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    application_date = models.DateField(auto_now_add=True)
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='loans_reviewed')
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loan_applications'
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.staff.get_full_name()} (₦{self.loan_amount:,.2f})"
    
    def _generate_application_number(self):
        year = timezone.now().year
        year_start = timezone.datetime(year, 1, 1)
        count = LoanApplication.objects.filter(created_at__gte=year_start).count() + 1
        return f"LOAN-{year}-{count:04d}"
    
    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self._generate_application_number()
        interest_amount = (self.loan_amount * self.interest_rate) / 100
        self.total_amount = self.loan_amount + interest_amount
        if self.repayment_period_months > 0:
            self.monthly_deduction = self.total_amount / self.repayment_period_months
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        if self.loan_amount <= 0:
            raise ValidationError({'loan_amount': 'Loan amount must be greater than zero.'})
        if self.interest_rate < 0:
            raise ValidationError({'interest_rate': 'Interest rate cannot be negative.'})
        if self.repayment_period_months <= 0:
            raise ValidationError({'repayment_period_months': 'Repayment period must be at least 1 month.'})
    
    def get_amount_paid(self):
        return self.loan_payments.aggregate(total_paid=models.Sum('amount'))['total_paid'] or 0
    
    def get_amount_remaining(self):
        return self.total_amount - self.get_amount_paid()


class LoanPayment(models.Model):
    """Loan repayment tracking"""
    loan_application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='loan_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.PositiveIntegerField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='loan_payments_processed')
    
    class Meta:
        db_table = 'loan_payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['year', 'month']),
        ]
    
    def __str__(self):
        return f"{self.loan_application.application_number} - {self.month}/{self.year} (₦{self.amount:,.2f})"
    
    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Payment amount must be greater than zero.'})
        remaining = self.loan_application.get_amount_remaining()
        if self.pk is None:
            if self.amount > remaining:
                raise ValidationError({'amount': f'Payment amount (₦{self.amount:,.2f}) exceeds remaining balance (₦{remaining:,.2f}).'})
