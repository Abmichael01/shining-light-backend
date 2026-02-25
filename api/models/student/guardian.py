from django.db import models
from django.utils.translation import gettext_lazy as _
from .student import Student

class Guardian(models.Model):
    """Parent or Guardian information"""
    
    GUARDIAN_TYPE_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='guardians',
        verbose_name=_('student')
    )
    
    guardian_type = models.CharField(
        _('guardian type'),
        max_length=20,
        choices=GUARDIAN_TYPE_CHOICES
    )
    relationship_to_student = models.CharField(
        _('relationship to student'),
        max_length=100,
        blank=True,
        help_text=_('For "Guardian" type, specify relationship')
    )
    
    surname = models.CharField(_('surname'), max_length=100)
    first_name = models.CharField(_('first name'), max_length=100)
    state_of_origin = models.CharField(_('state of origin'), max_length=100)
    
    phone_number = models.CharField(_('phone number'), max_length=20)
    email = models.EmailField(_('email'), blank=True)
    
    occupation = models.CharField(_('occupation'), max_length=150)
    place_of_employment = models.CharField(_('place of employment'), max_length=255)
    
    is_primary_contact = models.BooleanField(
        _('primary contact'),
        default=False,
        help_text=_('Is this the main contact person?')
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Guardian')
        verbose_name_plural = _('Guardians')
        ordering = ['-is_primary_contact', 'guardian_type']
        unique_together = [['student', 'guardian_type']]
    
    def __str__(self):
        return f"{self.get_guardian_type_display()}: {self.surname} {self.first_name}"
