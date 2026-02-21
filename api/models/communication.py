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
