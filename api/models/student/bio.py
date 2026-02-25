from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date
from .student import Student

class BioData(models.Model):
    """Student's biographical and personal information"""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
    ]
    
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='biodata',
        verbose_name=_('student')
    )
    
    surname = models.CharField(_('surname'), max_length=100)
    first_name = models.CharField(_('first name'), max_length=100)
    other_names = models.CharField(_('other names'), max_length=100, blank=True)
    gender = models.CharField(_('gender'), max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(_('date of birth'))
    passport_photo = models.ImageField(
        _('passport photo'),
        upload_to='students/passports/',
        blank=True,
        null=True,
        help_text=_('Student passport photograph')
    )
    
    nationality = models.CharField(_('nationality'), max_length=100, default='Nigerian')
    state_of_origin = models.CharField(_('state of origin'), max_length=100)
    permanent_address = models.TextField(_('permanent address'))
    
    lin = models.CharField(
        _('learner identification number'),
        max_length=50,
        blank=True,
        help_text=_('Learner Identification Number (LIN)')
    )
    
    has_medical_condition = models.BooleanField(
        _('has medical condition'),
        default=False
    )
    medical_condition_details = models.TextField(
        _('medical condition details'),
        blank=True,
        help_text=_('Describe any medical conditions')
    )
    blood_group = models.CharField(
        _('blood group'),
        max_length=5,
        choices=BLOOD_GROUP_CHOICES,
        blank=True
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Bio Data')
        verbose_name_plural = _('Bio Data')
    
    def __str__(self):
        return f"{self.surname} {self.first_name} {self.other_names}".strip()
    
    def get_age(self):
        """Calculate student's age"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def clean(self):
        """Validate bio data"""
        super().clean()
        if self.date_of_birth:
            age = self.get_age()
            if age < 3 or age > 30:
                raise ValidationError(_('Student age must be between 3 and 30 years'))
