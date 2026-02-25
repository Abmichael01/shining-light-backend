from django.db import models
from django.utils.translation import gettext_lazy as _
from .student import Student

class Document(models.Model):
    """Student documents storage"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('nin', 'National Identification Number (NIN)'),
        ('birth_certificate', 'Birth Certificate'),
        ('primary_certificate', 'Primary School Certificate'),
        ('bece_certificate', 'BECE Certificate'),
        ('passport', 'Passport Photograph'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('student')
    )
    
    document_type = models.CharField(
        _('document type'),
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_file = models.FileField(
        _('document file'),
        upload_to='student_documents/%Y/%m/%d/'
    )
    document_number = models.CharField(
        _('document number'),
        max_length=100,
        blank=True,
        help_text=_('e.g., NIN number, certificate number')
    )
    
    # Verification
    verified = models.BooleanField(_('verified'), default=False)
    verified_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_verified',
        verbose_name=_('verified by')
    )
    verified_at = models.DateTimeField(_('verified at'), null=True, blank=True)
    
    notes = models.TextField(_('notes'), blank=True)
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.student}"


class Biometric(models.Model):
    """Student biometric data (fingerprints)"""
    
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='biometric',
        verbose_name=_('student')
    )
    
    # Fingerprint images
    left_thumb = models.ImageField(
        _('left thumb'),
        upload_to='biometrics/%Y/%m/%d/',
        null=True,
        blank=True
    )
    left_index = models.ImageField(
        _('left index'),
        upload_to='biometrics/%Y/%m/%d/',
        null=True,
        blank=True
    )
    right_thumb = models.ImageField(
        _('right thumb'),
        upload_to='biometrics/%Y/%m/%d/',
        null=True,
        blank=True
    )
    right_index = models.ImageField(
        _('right index'),
        upload_to='biometrics/%Y/%m/%d/',
        null=True,
        blank=True
    )
    
    # Raw template data (Base64)
    left_thumb_template = models.TextField(
        _('left thumb template'),
        null=True,
        blank=True
    )
    left_index_template = models.TextField(
        _('left index template'),
        null=True,
        blank=True
    )
    right_thumb_template = models.TextField(
        _('right thumb template'),
        null=True,
        blank=True
    )
    right_index_template = models.TextField(
        _('right index template'),
        null=True,
        blank=True
    )
    
    captured_at = models.DateTimeField(_('captured at'), auto_now_add=True)
    captured_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='biometrics_captured',
        verbose_name=_('captured by')
    )
    
    notes = models.TextField(_('notes'), blank=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Biometric')
        verbose_name_plural = _('Biometrics')
    
    def __str__(self):
        return f"Biometric - {self.student}"
