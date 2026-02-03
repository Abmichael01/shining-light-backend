from django.db import models
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
