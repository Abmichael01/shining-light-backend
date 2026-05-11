from django.db import models
from django.utils.translation import gettext_lazy as _
from api.models.user import User

class CommunicationTemplate(models.Model):
    """
    Templates for SMS and Email communications.
    """
    TYPE_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200, blank=True, help_text="Required for Email templates")
    content = models.TextField(help_text="Use {{ variable }} for dynamic content")
    
    # Metadata for UI helpers
    description = models.CharField(max_length=255, blank=True, help_text="Short description of what this template is for")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='templates_created')
    
    class Meta:
        db_table = 'communication_templates'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class GuardianMessage(models.Model):
    """
    Record of messages/emails sent to guardians.
    """
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sent_guardian_messages'
    )
    student = models.ForeignKey(
        'Student', 
        on_delete=models.CASCADE, 
        related_name='guardian_messages'
    )
    # If sent specifically to one guardian
    recipient_guardian = models.ForeignKey(
        'Guardian', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='received_messages'
    )
    
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guardian_messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"Message to {self.student.admission_number} via {self.channel} at {self.created_at}"


class AIMessageDraft(models.Model):
    """
    AI-generated SMS/email drafts that must be reviewed by an admin before
    delivery.
    """
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    TARGET_GROUP_CHOICES = [
        ('all_students', 'All Students'),
        ('specific_class', 'Specific Class'),
        ('all_staff', 'All Staff'),
        ('teaching_staff', 'Teaching Staff'),
        ('non_teaching_staff', 'Non-Teaching Staff'),
        ('custom', 'Custom Recipients'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    target_group = models.CharField(max_length=30, choices=TARGET_GROUP_CHOICES)
    class_model = models.ForeignKey(
        'Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_message_drafts',
    )
    student_ids = models.JSONField(default=list, blank=True)
    custom_recipients = models.JSONField(default=list, blank=True)

    prompt = models.TextField()
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    ai_model = models.CharField(max_length=80, blank=True)
    send_summary = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_message_drafts_created',
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_message_drafts_approved',
    )
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_message_drafts_sent',
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_message_drafts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['channel', 'target_group']),
        ]

    def __str__(self):
        label = self.subject or self.prompt[:40]
        return f"{self.get_channel_display()} draft: {label}"
