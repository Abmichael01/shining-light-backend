from django.db import models
from django.utils.translation import gettext_lazy as _
import random
import string
from django.utils import timezone

class ResultPin(models.Model):
    """PIN for result checking. Each PIN is one-time use."""
    
    pin = models.CharField(_('PIN'), max_length=15, unique=True)
    serial_number = models.CharField(_('serial number'), max_length=15, unique=True)
    
    # Link to payment
    payment = models.OneToOneField(
        'api.FeePayment', 
        on_delete=models.CASCADE, 
        related_name='result_pin',
        verbose_name=_('payment')
    )
    
    # Assigned when used (or at purchase if we want to restrict)
    student = models.ForeignKey(
        'api.Student', 
        on_delete=models.CASCADE, 
        related_name='result_pins',
        verbose_name=_('student')
    )
    
    session = models.ForeignKey(
        'api.Session', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('session')
    )
    session_term = models.ForeignKey(
        'api.SessionTerm', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_('session term')
    )
    
    is_used = models.BooleanField(_('used'), default=False)
    used_at = models.DateTimeField(_('used at'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Result PIN')
        verbose_name_plural = _('Result PINs')
        ordering = ['-created_at']

    def __str__(self):
        return f"PIN: {self.pin} (S/N: {self.serial_number})"

    @staticmethod
    def generate_pin(length=12):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    @staticmethod
    def generate_serial(length=10):
        return ''.join(random.choices(string.digits, k=length))

    def save(self, *args, **kwargs):
        if not self.pin:
            self.pin = self.generate_pin()
            while ResultPin.objects.filter(pin=self.pin).exists():
                self.pin = self.generate_pin()
        
        if not self.serial_number:
            self.serial_number = self.generate_serial()
            while ResultPin.objects.filter(serial_number=self.serial_number).exists():
                self.serial_number = self.generate_serial()
                
        super().save(*args, **kwargs)

    def use(self, student, session, session_term):
        """Mark PIN as used for a specific term result."""
        if self.is_used:
            return False, "This PIN has already been used."
        
        if self.student != student:
             return False, "This PIN belongs to another student."

        self.is_used = True
        self.used_at = timezone.now()
        self.session = session
        self.session_term = session_term
        self.save()
        return True, "PIN validated successfully."
