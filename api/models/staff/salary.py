from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from api.models.user import User
from .staff import Staff

class SalaryGrade(models.Model):
    """Salary grade definitions - Grade 1 to Grade 18"""
    grade_number = models.PositiveIntegerField(unique=True, choices=[(i, f'Grade {i}') for i in range(1, 19)])
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='salary_grades_created')
    
    class Meta:
        db_table = 'salary_grades'
        ordering = ['grade_number']
    
    def __str__(self):
        return f"Grade {self.grade_number} (₦{self.monthly_amount:,.2f})"
    
    def clean(self):
        super().clean()
        if self.monthly_amount <= 0:
            raise ValidationError({'monthly_amount': 'Salary amount must be greater than zero.'})


class StaffSalary(models.Model):
    """Current salary assignment for staff"""
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='current_salary')
    salary_grade = models.ForeignKey(SalaryGrade, on_delete=models.PROTECT, related_name='assigned_staff')
    effective_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='staff_salaries_assigned')
    
    class Meta:
        db_table = 'staff_salaries'
        verbose_name_plural = 'Staff salaries'
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - Grade {self.salary_grade.grade_number}"
    
    def clean(self):
        super().clean()
        staff_school = getattr(self.staff, 'school', None)
        grade_school = getattr(self.salary_grade, 'school', None)
        if grade_school and staff_school and grade_school != staff_school:
            raise ValidationError({'salary_grade': 'Salary grade must belong to the same school as the staff member.'})


class SalaryPayment(models.Model):
    """Monthly salary payment records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='salary_payments')
    salary_grade = models.ForeignKey(SalaryGrade, on_delete=models.PROTECT, related_name='payments')
    
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='salary_payments_processed')
    
    class Meta:
        db_table = 'salary_payments'
        ordering = ['-year', '-month', 'staff']
        unique_together = [['staff', 'month', 'year']]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['year', 'month']),
        ]
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.month}/{self.year} (₦{self.net_amount:,.2f})"
    
    def save(self, *args, **kwargs):
        self.net_amount = self.amount - self.deductions
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        if self.month < 1 or self.month > 12:
            raise ValidationError({'month': 'Month must be between 1 and 12.'})
        current_year = timezone.now().year
        if self.year < 2000 or self.year > current_year + 1:
            raise ValidationError({'year': f'Year must be between 2000 and {current_year + 1}.'})
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        if self.deductions < 0:
            raise ValidationError({'deductions': 'Deductions cannot be negative.'})
