from django.db import models
from api.models.student import Student

class ApplicationSlip(models.Model):
    """Stores generated application slips for applicants"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='application_slip', verbose_name='student')
    application_number = models.CharField(max_length=20)
    screening_date = models.DateField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='application_slips/%Y/%m/%d/', blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'application_slips'
        ordering = ['-generated_at']
        verbose_name = 'Application Slip'
        verbose_name_plural = 'Application Slips'
    
    def __str__(self):
        return f"Application Slip - {self.application_number}"


class Anything:
    """Legacy/Testing helper class"""
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    
    def __str__(self):
        return str(self.kwargs)
        
    def doSomething(self):
        print("hey how far now,  imiss u so much")
        print(self.kwargs)
