from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from api.models.user import User
from api.models.academic import School, Class

class Staff(models.Model):
    """Staff model - stores staff profile and employment information"""
    
    ZONE_CHOICES = [('ransowa', 'Ransowa'), ('omoowo', 'Omoowo')]
    TITLE_CHOICES = [('miss', 'Miss'), ('mrs', 'Mrs'), ('mr', 'Mr'), ('dr', 'Dr')]
    MARITAL_STATUS_CHOICES = [('single', 'Single'), ('married', 'Married')]
    RELIGION_CHOICES = [('muslim', 'Muslim'), ('christian', 'Christian')]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('retired', 'Retired'),
    ]
    STAFF_TYPE_CHOICES = [('teaching', 'Teaching Staff'), ('non_teaching', 'Non-Teaching Staff')]
    
    staff_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    
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
    
    entry_date = models.DateField(default=timezone.now)
    staff_type = models.CharField(max_length=20, choices=STAFF_TYPE_CHOICES, default='teaching')
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='staff_members', null=True, blank=True)
    zone = models.CharField(max_length=20, choices=ZONE_CHOICES)
    assigned_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_staff_members')
    
    number_of_children_in_school = models.PositiveIntegerField(default=0)
    children = models.ManyToManyField('Student', blank=True, related_name='staff_parents')
    
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    passport_photo = models.FileField(upload_to='staff/passports/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='staff_created')
    
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
        return self.staff_id
    
    def get_full_name(self):
        names = [self.surname, self.first_name]
        if self.other_names:
            names.append(self.other_names)
        full_name = ' '.join(names)
        return f"{self.get_title_display()} {full_name}"
    
    def _generate_staff_id(self):
        year = timezone.now().year
        max_attempts = 1000
        for attempt in range(max_attempts):
            count = Staff.objects.count() + 1 + attempt
            staff_id = f"STF{year}{count:03d}"
            if not Staff.objects.filter(staff_id=staff_id).exists():
                return staff_id
        import time
        timestamp = int(time.time() * 1000) % 1000000
        return f"STF{year}{timestamp:06d}"
    
    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = self._generate_staff_id()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        if user:
            user.delete()
    
    def clean(self):
        super().clean()
        if self.date_of_birth:
            age = (timezone.now().date() - self.date_of_birth).days / 365.25
            if age < 18:
                raise ValidationError({'date_of_birth': 'Staff member must be at least 18 years old.'})
            if age > 70:
                raise ValidationError({'date_of_birth': 'Please verify the date of birth.'})


class StaffEducation(models.Model):
    """Staff education background - supports multiple entries"""
    
    EDUCATION_LEVEL_CHOICES = [
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('tertiary', 'Tertiary Institution'),
    ]
    DEGREE_CHOICES = [
        ('ond', 'OND'), ('hnd', 'HND'), ('nce', 'NCE'), ('bsc', 'B.Sc'),
        ('bed', 'B.Ed'), ('msc', 'M.Sc'), ('med', 'M.Ed'), ('phd', 'Ph.D'), ('other', 'Other'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='education_records')
    level = models.CharField(max_length=20, choices=EDUCATION_LEVEL_CHOICES)
    institution_name = models.CharField(max_length=200)
    year_of_graduation = models.PositiveIntegerField()
    degree = models.CharField(max_length=20, choices=DEGREE_CHOICES, blank=True)
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
        super().clean()
        current_year = timezone.now().year
        if self.year_of_graduation > current_year:
            raise ValidationError({'year_of_graduation': 'Year of graduation cannot be in the future.'})
        if self.year_of_graduation < 1950:
            raise ValidationError({'year_of_graduation': 'Please verify the year of graduation.'})
        if self.level == 'tertiary' and not self.degree:
            raise ValidationError({'degree': 'Degree is required for tertiary education.'})


class StaffBeneficiary(models.Model):
    """Saved beneficiaries for staff withdrawals"""
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='beneficiaries')
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=20)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=200)
    
    paystack_recipient_code = models.CharField(max_length=50, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'staff_beneficiaries'
        unique_together = ['staff', 'account_number', 'bank_code']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.account_name} - {self.bank_name}"
