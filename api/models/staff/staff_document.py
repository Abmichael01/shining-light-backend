from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models.user import User
from .staff import Staff


class StaffDocument(models.Model):
    """Documents a staff member uploads (passport, NIN, certificates, etc.)."""

    DOCUMENT_TYPE_CHOICES = [
        ('passport', 'Passport Photograph'),
        ('nin', 'NIN / National ID'),
        ('certificate', 'Educational Certificate'),
        ('trcn', 'TRCN / Teaching License'),
        ('school_result', 'School Result'),
        ('other', 'Other'),
    ]

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='staff_documents',
    )
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
    )
    document_file = models.FileField(upload_to='staff/documents/%Y/%m/%d/')
    label = models.CharField(
        max_length=120,
        blank=True,
        help_text=_('Optional free-text label, e.g. "B.Ed Education" or "NYSC Certificate".'),
    )

    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_documents_verified',
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        label = self.label or self.get_document_type_display()
        return f'{self.staff.staff_id} – {label}'
