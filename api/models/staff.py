"""
Staff-related models for the School Management System
Handles staff profiles, education, salary, and loans
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from api.models.user import User
from api.models.academic import School, Class, Department
import random
import string


class Staff(models.Model):
    """
    Staff model - stores staff profile and employment information
    """
    ZONE_CHOICES = [
        ('ransowa', 'Ransowa'),
        ('omoowo', 'Omoowo'),
    ]
    
    TITLE_CHOICES = [
        ('miss', 'Miss'),
        ('mrs', 'Mrs'),
        ('mr', 'Mr'),
        ('dr', 'Dr'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
    ]
    
    RELIGION_CHOICES = [
        ('muslim', 'Muslim'),
        ('christian', 'Christian'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('retired', 'Retired'),
    ]
    
    STAFF_TYPE_CHOICES = [
        ('teaching', 'Teaching Staff'),
        ('non_teaching', 'Non-Teaching Staff'),
    ]
    
    # Registration & User
    staff_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    
    # Personal Information
    title = models.CharField(max_length=10, choices=TITLE_CHOICES)
    surname = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=100, default='Nigerian')
    state_of_origin = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    permanent_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    religion = models.CharField(max_length=20, choices=RELIGION_CHOICES)
    
    # Employment Details
    entry_date = models.DateField(default=timezone.now)
    staff_type = models.CharField(max_length=20, choices=STAFF_TYPE_CHOICES, default='teaching')
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='staff_members',
        null=True, # Allow null for existing records
        blank=True
    )
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES)
    assigned_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_staff_members',
        help_text='Class the staff member is assigned to (for teaching staff)'
    )
    
    # Family
    number_of_children_in_school = models.PositiveIntegerField(default=0)
    
    # Account Details
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    
    # Documents
    passport_photo = models.FileField(upload_to='staff/passports/', null=True, blank=True)
    
    # Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='staff_created'
    )
    
    class Meta:
        db_table = 'staff'
        ordering = ['-created_at']
        verbose_name_plural = 'Staff'
        indexes = [
            models.Index(fields=['staff_id']),
            models.Index(fields=['status']),
            models.Index(fields=['zone']),
        ]
    
    def __str__(self):
        """Return staff ID as the string representation"""
        return self.staff_id
    
    def get_full_name(self):
        """Return staff member's full name with title"""
        names = [self.surname, self.first_name]
        if self.other_names:
            names.append(self.other_names)
        full_name = ' '.join(names)
        return f"{self.get_title_display()} {full_name}"
    
    def _generate_staff_id(self):
        """Generate unique staff ID: STFYYYYNNN (e.g., STF2025001)"""
        year = timezone.now().year
        
        # Get count of all staff (across all schools) for global incrementing
        # Use a loop to handle race conditions where multiple staff are created simultaneously
        max_attempts = 1000
        for attempt in range(max_attempts):
            count = Staff.objects.count() + 1 + attempt
            staff_id = f"STF{year}{count:03d}"
            
            # Check if this ID already exists
            if not Staff.objects.filter(staff_id=staff_id).exists():
                return staff_id
        
        # Fallback: if we can't find a unique ID after many attempts, use timestamp
        import time
        timestamp = int(time.time() * 1000) % 1000000
        return f"STF{year}{timestamp:06d}"
    
    def save(self, *args, **kwargs):
        """Override save to generate staff ID"""
        if not self.staff_id:
            self.staff_id = self._generate_staff_id()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to also delete associated user account"""
        user = self.user
        # Delete staff first (this will cascade to education, salary, loans, etc.)
        super().delete(*args, **kwargs)
        # Then delete the user account
        if user:
            user.delete()
    
    def clean(self):
        """Validate staff data"""
        super().clean()
        
        # Validate date of birth
        if self.date_of_birth:
            age = (timezone.now().date() - self.date_of_birth).days / 365.25
            if age < 18:
                raise ValidationError({
                    'date_of_birth': 'Staff member must be at least 18 years old.'
                })
            if age > 70:
                raise ValidationError({
                    'date_of_birth': 'Please verify the date of birth.'
                })


class StaffEducation(models.Model):
    """
    Staff education background - supports multiple entries
    """
    EDUCATION_LEVEL_CHOICES = [
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('tertiary', 'Tertiary Institution'),
    ]
    
    DEGREE_CHOICES = [
        ('ond', 'OND'),
        ('hnd', 'HND'),
        ('nce', 'NCE'),
        ('bsc', 'B.Sc'),
        ('bed', 'B.Ed'),
        ('msc', 'M.Sc'),
        ('med', 'M.Ed'),
        ('phd', 'Ph.D'),
        ('other', 'Other'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='education_records')
    level = models.CharField(max_length=20, choices=EDUCATION_LEVEL_CHOICES)
    institution_name = models.CharField(max_length=200)
    year_of_graduation = models.PositiveIntegerField()
    degree = models.CharField(
        max_length=20,
        choices=DEGREE_CHOICES,
        blank=True,
        help_text='Applicable for tertiary education only'
    )
    certificate = models.FileField(upload_to='staff/certificates/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'staff_education'
        ordering = ['staff', 'year_of_graduation']
        unique_together = [['staff', 'level', 'institution_name']]
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.get_level_display()} ({self.year_of_graduation})"
    
    def clean(self):
        """Validate education record"""
        super().clean()
        
        # Validate year of graduation
        current_year = timezone.now().year
        if self.year_of_graduation > current_year:
            raise ValidationError({
                'year_of_graduation': 'Year of graduation cannot be in the future.'
            })
        if self.year_of_graduation < 1950:
            raise ValidationError({
                'year_of_graduation': 'Please verify the year of graduation.'
            })
        
        # Degree is required for tertiary education
        if self.level == 'tertiary' and not self.degree:
            raise ValidationError({
                'degree': 'Degree is required for tertiary education.'
            })


class SalaryGrade(models.Model):
    """
    Salary grade definitions - Grade 1 to Grade 18 (Global across all schools)
    """
    grade_number = models.PositiveIntegerField(unique=True, choices=[(i, f'Grade {i}') for i in range(1, 19)])
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, help_text='Optional description of the grade')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salary_grades_created'
    )
    
    class Meta:
        db_table = 'salary_grades'
        ordering = ['grade_number']
    
    def __str__(self):
        return f"Grade {self.grade_number} (₦{self.monthly_amount:,.2f})"
    
    def clean(self):
        """Validate salary grade"""
        super().clean()
        
        if self.monthly_amount <= 0:
            raise ValidationError({
                'monthly_amount': 'Salary amount must be greater than zero.'
            })


class StaffSalary(models.Model):
    """
    Current salary assignment for staff
    """
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='current_salary')
    salary_grade = models.ForeignKey(SalaryGrade, on_delete=models.PROTECT, related_name='assigned_staff')
    effective_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='staff_salaries_assigned'
    )
    
    class Meta:
        db_table = 'staff_salaries'
        verbose_name_plural = 'Staff salaries'
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - Grade {self.salary_grade.grade_number}"
    
    def clean(self):
        """Validate staff salary assignment"""
        super().clean()
        
        # Ensure salary grade belongs to the same school
        grade_school = getattr(self.salary_grade, 'school', None)
        staff_school = getattr(self.staff, 'school', None)
        if grade_school and staff_school and grade_school != staff_school:
            raise ValidationError({
                'salary_grade': 'Salary grade must belong to the same school as the staff member.'
            })


class SalaryPayment(models.Model):
    """
    Monthly salary payment records
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='salary_payments')
    salary_grade = models.ForeignKey(SalaryGrade, on_delete=models.PROTECT, related_name='payments')
    
    # Payment Details
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salary_payments_processed'
    )
    
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
        """Calculate net amount before saving"""
        self.net_amount = self.amount - self.deductions
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate salary payment"""
        super().clean()
        
        # Validate month and year
        if self.month < 1 or self.month > 12:
            raise ValidationError({
                'month': 'Month must be between 1 and 12.'
            })
        
        current_year = timezone.now().year
        if self.year < 2000 or self.year > current_year + 1:
            raise ValidationError({
                'year': f'Year must be between 2000 and {current_year + 1}.'
            })
        
        # Validate amounts
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Amount must be greater than zero.'
            })
        
        if self.deductions < 0:
            raise ValidationError({
                'deductions': 'Deductions cannot be negative.'
            })


class LoanApplication(models.Model):
    """
    Staff loan applications
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='loan_applications')
    
    # Loan Details
    application_number = models.CharField(max_length=20, unique=True, blank=True)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Interest rate as percentage')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    repayment_period_months = models.PositiveIntegerField(help_text='Repayment period in months')
    monthly_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField(help_text='Reason for loan application')
    
    # Status & Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    application_date = models.DateField(auto_now_add=True)
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    
    # Review
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loans_reviewed'
    )
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'loan_applications'
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.staff.get_full_name()} (₦{self.loan_amount:,.2f})"
    
    def _generate_application_number(self):
        """Generate unique loan application number: LOAN-YYYY-XXXX"""
        year = timezone.now().year
        
        # Get count of loan applications this year
        year_start = timezone.datetime(year, 1, 1)
        count = LoanApplication.objects.filter(
            created_at__gte=year_start
        ).count() + 1
        
        # Format: LOAN-2025-0001
        return f"LOAN-{year}-{count:04d}"
    
    def save(self, *args, **kwargs):
        """Calculate total amount and monthly deduction before saving"""
        if not self.application_number:
            self.application_number = self._generate_application_number()
        
        # Calculate total amount with interest
        interest_amount = (self.loan_amount * self.interest_rate) / 100
        self.total_amount = self.loan_amount + interest_amount
        
        # Calculate monthly deduction
        if self.repayment_period_months > 0:
            self.monthly_deduction = self.total_amount / self.repayment_period_months
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate loan application"""
        super().clean()
        
        if self.loan_amount <= 0:
            raise ValidationError({
                'loan_amount': 'Loan amount must be greater than zero.'
            })
        
        if self.interest_rate < 0:
            raise ValidationError({
                'interest_rate': 'Interest rate cannot be negative.'
            })
        
        if self.repayment_period_months <= 0:
            raise ValidationError({
                'repayment_period_months': 'Repayment period must be at least 1 month.'
            })
    
    def get_amount_paid(self):
        """Calculate total amount paid so far"""
        return self.loan_payments.aggregate(
            total_paid=models.Sum('amount')
        )['total_paid'] or 0
    
    def get_amount_remaining(self):
        """Calculate remaining loan balance"""
        return self.total_amount - self.get_amount_paid()


class LoanPayment(models.Model):
    """
    Loan repayment tracking
    """
    loan_application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='loan_payments'
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 13)])
    year = models.PositiveIntegerField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='loan_payments_processed'
    )
    
    class Meta:
        db_table = 'loan_payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['year', 'month']),
        ]
    
    def __str__(self):
        return f"{self.loan_application.application_number} - {self.month}/{self.year} (₦{self.amount:,.2f})"
    
    def clean(self):
        """Validate loan payment"""
        super().clean()
        
        if self.amount <= 0:
            raise ValidationError({
                'amount': 'Payment amount must be greater than zero.'
            })
        
        # Check if payment exceeds remaining balance
        remaining = self.loan_application.get_amount_remaining()
        if self.pk is None:  # New payment
            if self.amount > remaining:
                raise ValidationError({
                    'amount': f'Payment amount (₦{self.amount:,.2f}) exceeds remaining balance (₦{remaining:,.2f}).'
                })


