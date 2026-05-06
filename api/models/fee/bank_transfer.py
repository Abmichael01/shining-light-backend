from django.db import models
from api.models.user import User
from api.models.student import Student
from django.utils.translation import gettext_lazy as _

class AdmissionBankTransfer(models.Model):
    """
    Stores bank transfer proof of payment for admission applications
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='bank_transfers')
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    reference = models.CharField(_('reference'), max_length=100, blank=True)
    screenshot = models.ImageField(_('screenshot'), upload_to='payment_screenshots/%Y/%m/%d/')
    
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(_('rejection reason'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_admission_transfers',
        verbose_name=_('verified by')
    )
    verified_at = models.DateTimeField(_('verified at'), null=True, blank=True)
    
    class Meta:
        db_table = 'admission_bank_transfers'
        ordering = ['-created_at']
        verbose_name = _('Admission Bank Transfer')
        verbose_name_plural = _('Admission Bank Transfers')
        
    def __str__(self):
        return f"{self.student.get_full_name()} - ₦{self.amount} ({self.status})"
