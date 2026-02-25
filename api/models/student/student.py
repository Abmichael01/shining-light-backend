from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date

class Student(models.Model):
    """
    Main Student model - handles both applicants and enrolled students
    Status-based approach: applicant → under_review → accepted → enrolled
    """
    
    APPLICATION_STATUS_CHOICES = [
        ('applicant', 'Applicant'),
        ('under_review', 'Under Review'),
        ('accepted', 'Accepted'),
        ('enrolled', 'Enrolled'),
        ('suspended', 'Suspended'),
        ('graduated', 'Graduated'),
        ('withdrawn', 'Withdrawn'),
        ('rejected', 'Rejected'),
    ]
    
    SOURCE_CHOICES = [
        ('online_application', 'Online Application'),
        ('admin_registration', 'Admin Registration'),
    ]
    
    id = models.CharField(
        _('student ID'),
        max_length=20,
        primary_key=True,
        help_text=_('Human-readable ID like STU-001ABC')
    )
    
    application_number = models.CharField(
        _('application number'),
        max_length=20,
        unique=True,
        help_text=_('Auto-generated on application')
    )
    admission_number = models.CharField(
        _('admission number'),
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        default=None,
        help_text=_('Auto-generated on acceptance (Format: YYYYMMDD + Serial)')
    )
    
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name=_('user account')
    )
    
    school = models.ForeignKey(
        'School',
        on_delete=models.PROTECT,
        related_name='students',
        verbose_name=_('school')
    )
    class_model = models.ForeignKey(
        'Class',
        on_delete=models.PROTECT,
        related_name='students',
        verbose_name=_('class')
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='students',
        verbose_name=_('department'),
        help_text=_('Only for Senior Secondary (SS1, SS2, SS3)')
    )
    former_school_attended = models.CharField(
        _('former school attended'),
        max_length=255,
        blank=True
    )
    club = models.ForeignKey(
        'Club',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name=_('club'),
        help_text=_('Student club or society membership')
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=APPLICATION_STATUS_CHOICES,
        default='applicant'
    )
    source = models.CharField(
        _('source'),
        max_length=30,
        choices=SOURCE_CHOICES,
        help_text=_('How this student record was created')
    )
    
    application_date = models.DateField(_('application date'), auto_now_add=True)
    review_date = models.DateField(_('review date'), null=True, blank=True)
    acceptance_date = models.DateField(_('acceptance date'), null=True, blank=True)
    enrollment_date = models.DateField(_('enrollment date'), null=True, blank=True)
    graduation_date = models.DateField(_('graduation date'), null=True, blank=True)
    
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_created',
        verbose_name=_('created by')
    )
    reviewed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students_reviewed',
        verbose_name=_('reviewed by')
    )
    
    application_checklist = models.JSONField(
        _('application checklist'),
        blank=True,
        default=dict,
        help_text=_('Tracks completion of application steps: biodata, guardians, documents, payment')
    )
    seat_number = models.CharField(
        _('seat number'),
        max_length=20,
        blank=True,
        help_text=_('Assigned when application is submitted')
    )
    application_submitted_at = models.DateTimeField(
        _('application submitted at'),
        null=True,
        blank=True,
        help_text=_('When the online application was submitted')
    )
    
    rejection_reason = models.TextField(_('rejection reason'), blank=True)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['admission_number']),
            models.Index(fields=['status']),
            models.Index(fields=['school', 'class_model']),
        ]
    
    def __str__(self):
        if self.admission_number:
            return self.admission_number
        return self.application_number
    
    def get_full_name(self):
        try:
            biodata = self.biodata
            return f"{biodata.surname} {biodata.first_name}"
        except:
            return "N/A"
    
    @property
    def current_session(self):
        from api.models.academic import Session
        return Session.objects.filter(is_current=True).first()

    @property
    def current_term(self):
        from api.models.academic import SessionTerm
        return SessionTerm.objects.filter(is_current=True).first()

    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self._generate_application_number()
        
        if self.status in ['accepted', 'enrolled']:
            if not self.admission_number or self.admission_number.strip() == '':
                self.admission_number = self._generate_admission_number()
        
        if not self.id:
            from api.utils.id_generator import generate_student_id
            self.id = generate_student_id()
        
        super().save(*args, **kwargs)
    
    def _generate_application_number(self):
        current_year = date.today().year
        prefix = f"APP-{current_year}"
        last_student = Student.objects.filter(
            application_number__startswith=prefix
        ).order_by('application_number').last()
        
        if last_student:
            last_number = int(last_student.application_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:04d}"
    
    def _generate_admission_number(self):
        if not hasattr(self, 'biodata') or not self.biodata or not self.biodata.date_of_birth:
            raise ValidationError(_('Student biodata with date of birth is required to generate admission number'))
        
        dob_prefix = self.biodata.date_of_birth.strftime('%Y%m%d')
        last_student = Student.objects.filter(
            admission_number__startswith=dob_prefix
        ).exclude(admission_number='').order_by('admission_number').last()
        
        if last_student:
            try:
                last_serial = int(last_student.admission_number[-2:])
                new_serial = last_serial + 1
            except (ValueError, IndexError):
                new_serial = 1
        else:
            new_serial = 1
        
        if new_serial > 99:
            raise ValidationError(_('Maximum number of students with the same date of birth (99) has been reached'))
        
        return f"{dob_prefix}{new_serial:02d}"
    
    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        if user:
            user.delete()
    
    def clean(self):
        super().clean()
        if self.class_model:
            class_name = self.class_model.name.upper()
            if any(x in class_name for x in ['SS1', 'SS2', 'SS3', 'SSS1', 'SSS2', 'SSS3']):
                if not self.department:
                    raise ValidationError(_('Department is required for Senior Secondary classes'))
            else:
                if self.department:
                    raise ValidationError(_('Department should only be set for Senior Secondary classes'))
