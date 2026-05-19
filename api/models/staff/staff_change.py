from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models.user import User
from .staff import Staff, StaffEducation
from .staff_document import StaffDocument


class StaffChangeRequest(models.Model):
    """Audit log of staff-initiated changes that admin must review.

    A row is created every time a staff member changes anything about their
    profile or documents. The change is applied immediately (so staff aren't
    blocked) but admins see what changed and can approve or roll it back.
    """

    CHANGE_TYPE_CHOICES = [
        ('profile_field', 'Profile Field'),
        ('document_upload', 'Document Uploaded'),
        ('document_replace', 'Document Replaced'),
        ('document_delete', 'Document Deleted'),
        ('education_create', 'Education Record Added'),
        ('education_update', 'Education Record Updated'),
        ('education_delete', 'Education Record Deleted'),
    ]
    STATUS_CHOICES = [
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='change_requests',
    )
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPE_CHOICES)
    field_name = models.CharField(
        max_length=80,
        blank=True,
        help_text=_('Profile field name, or document type for document changes.'),
    )
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    document = models.ForeignKey(
        StaffDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_requests',
    )
    education = models.ForeignKey(
        StaffEducation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_requests',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending_review',
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_changes_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'staff_change_requests'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['staff', '-submitted_at']),
        ]

    def __str__(self):
        return f'{self.staff.staff_id} – {self.get_change_type_display()} ({self.status})'
