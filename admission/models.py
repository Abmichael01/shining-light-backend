# admission/models/Application.py
from django.db import models
from accounts.models import Biodata
from core.models import Class as ClassName
from django.contrib.auth import get_user_model

User = get_user_model()

class Application(models.Model):
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('reviewing', 'Under Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(
        Biodata.user.field.remote_field.model,
        on_delete=models.CASCADE,
        editable=False,
        related_name='applications'
    )
    
    biodata = models.ForeignKey(
        Biodata,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    
    class_name = models.ForeignKey(
        ClassName,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted'
    )
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"{self.biodata.first_name} {self.biodata.last_name} → {self.class_name.school.name} {self.class_name.name}"
    

DOCUMENT_TYPES = (
    ('birth_certificate', 'Birth Certificate'),
    ('academic_result', 'Academic Result'),
    ('passport_photo', 'Passport Photo'),
    ('recommendation_letter', 'Recommendation Letter'),
    ('other', 'Other')
)

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    
    type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='admission_documents/')
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.get_type_display()}"