from django.db import models
from api.models.user import User

class LeaveRequest(models.Model):
    """
    Leave Application for Staff and Students
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Generic user link (handles both Student and Staff via their User account)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    
    # Leave Details
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    
    # Admin Response
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_note = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leaves_responded'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.start_date} ({self.status})"
