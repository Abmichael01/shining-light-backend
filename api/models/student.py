from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction
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
    
    # Unique identifiers
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
        blank=True,
        help_text=_('Auto-generated on acceptance')
    )
    
    # User account (optional until accepted)
    # CASCADE: When student is deleted, user account is also deleted
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name=_('user account')
    )
    
    # Academic information
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
    
    # Status tracking
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
    
    # Important dates
    application_date = models.DateField(_('application date'), auto_now_add=True)
    review_date = models.DateField(_('review date'), null=True, blank=True)
    acceptance_date = models.DateField(_('acceptance date'), null=True, blank=True)
    enrollment_date = models.DateField(_('enrollment date'), null=True, blank=True)
    graduation_date = models.DateField(_('graduation date'), null=True, blank=True)
    
    # Admin actions
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
    rejection_reason = models.TextField(_('rejection reason'), blank=True)
    
    # Timestamps
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
        """Return admission/application number as the string representation"""
        if self.admission_number:
            return self.admission_number
        return self.application_number
    
    def get_full_name(self):
        """Get student's full name from biodata"""
        try:
            biodata = self.biodata
            return f"{biodata.surname} {biodata.first_name}"
        except:
            return "N/A"
    
    def save(self, *args, **kwargs):
        """Auto-generate application number and admission number"""
        if not self.application_number:
            self.application_number = self._generate_application_number()
        
        # Generate admission number when status changes to accepted or enrolled
        if not self.admission_number and self.status in ['accepted', 'enrolled']:
            self.admission_number = self._generate_admission_number()
        
        super().save(*args, **kwargs)
    
    def _generate_application_number(self):
        """Generate unique application number: APP-YYYY-NNNN"""
        current_year = date.today().year
        prefix = f"APP-{current_year}"
        
        # Get the last application number for this year
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
        """Generate unique admission number: SLGSYYYY001 (e.g., SLGS2025001)"""
        current_year = date.today().year
        prefix = f"SLGS{current_year}"
        
        # Get the last admission number for this year
        last_student = Student.objects.filter(
            admission_number__startswith=prefix
        ).exclude(admission_number='').order_by('admission_number').last()
        
        if last_student:
            # Extract the numeric part (last 3 digits)
            last_number = int(last_student.admission_number[-3:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:03d}"
    
    def delete(self, *args, **kwargs):
        """Override delete to also delete associated user account"""
        user = self.user
        # Delete student first (this will cascade to biodata, guardians, documents, etc.)
        super().delete(*args, **kwargs)
        # Then delete the user account if it exists
        if user:
            user.delete()
    
    def clean(self):
        """Validate student data"""
        super().clean()
        
        # Department required for SS1, SS2, SS3
        if self.class_model:
            class_name = self.class_model.name.upper()
            if any(x in class_name for x in ['SS1', 'SS2', 'SS3', 'SSS1', 'SSS2', 'SSS3']):
                if not self.department:
                    raise ValidationError(_('Department is required for Senior Secondary classes'))
            else:
                if self.department:
                    raise ValidationError(_('Department should only be set for Senior Secondary classes'))


class BioData(models.Model):
    """Student's biographical and personal information"""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
    ]
    
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='biodata',
        verbose_name=_('student')
    )
    
    # Personal information
    surname = models.CharField(_('surname'), max_length=100)
    first_name = models.CharField(_('first name'), max_length=100)
    other_names = models.CharField(_('other names'), max_length=100, blank=True)
    gender = models.CharField(_('gender'), max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(_('date of birth'))
    passport_photo = models.ImageField(
        _('passport photo'),
        upload_to='students/passports/',
        blank=True,
        null=True,
        help_text=_('Student passport photograph')
    )
    
    # Location information
    nationality = models.CharField(_('nationality'), max_length=100, default='Nigerian')
    state_of_origin = models.CharField(_('state of origin'), max_length=100)
    permanent_address = models.TextField(_('permanent address'))
    
    # Identification
    lin = models.CharField(
        _('learner identification number'),
        max_length=50,
        blank=True,
        help_text=_('Learner Identification Number (LIN)')
    )
    
    # Medical information
    has_medical_condition = models.BooleanField(
        _('has medical condition'),
        default=False
    )
    medical_condition_details = models.TextField(
        _('medical condition details'),
        blank=True,
        help_text=_('Describe any medical conditions')
    )
    blood_group = models.CharField(
        _('blood group'),
        max_length=5,
        choices=BLOOD_GROUP_CHOICES,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Bio Data')
        verbose_name_plural = _('Bio Data')
    
    def __str__(self):
        return f"{self.surname} {self.first_name} {self.other_names}".strip()
    
    def get_age(self):
        """Calculate student's age"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def clean(self):
        """Validate bio data"""
        super().clean()
        
        # Age validation (must be between 3 and 30)
        if self.date_of_birth:
            age = self.get_age()
            if age < 3 or age > 30:
                raise ValidationError(_('Student age must be between 3 and 30 years'))


class Guardian(models.Model):
    """Parent or Guardian information"""
    
    GUARDIAN_TYPE_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='guardians',
        verbose_name=_('student')
    )
    
    # Guardian type and relationship
    guardian_type = models.CharField(
        _('guardian type'),
        max_length=20,
        choices=GUARDIAN_TYPE_CHOICES
    )
    relationship_to_student = models.CharField(
        _('relationship to student'),
        max_length=100,
        blank=True,
        help_text=_('For "Guardian" type, specify relationship')
    )
    
    # Personal information
    surname = models.CharField(_('surname'), max_length=100)
    first_name = models.CharField(_('first name'), max_length=100)
    state_of_origin = models.CharField(_('state of origin'), max_length=100)
    
    # Contact information
    phone_number = models.CharField(_('phone number'), max_length=20)
    email = models.EmailField(_('email'), blank=True)
    
    # Employment information
    occupation = models.CharField(_('occupation'), max_length=150)
    place_of_employment = models.CharField(_('place of employment'), max_length=255)
    
    # Primary contact
    is_primary_contact = models.BooleanField(
        _('primary contact'),
        default=False,
        help_text=_('Is this the main contact person?')
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Guardian')
        verbose_name_plural = _('Guardians')
        ordering = ['-is_primary_contact', 'guardian_type']
        unique_together = [['student', 'guardian_type']]
    
    def __str__(self):
        return f"{self.get_guardian_type_display()}: {self.surname} {self.first_name}"


class Document(models.Model):
    """Student documents storage"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('nin', 'National Identification Number (NIN)'),
        ('birth_certificate', 'Birth Certificate'),
        ('primary_certificate', 'Primary School Certificate'),
        ('bece_certificate', 'BECE Certificate'),
        ('passport', 'Passport Photograph'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('student')
    )
    
    document_type = models.CharField(
        _('document type'),
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_file = models.FileField(
        _('document file'),
        upload_to='student_documents/%Y/%m/%d/'
    )
    document_number = models.CharField(
        _('document number'),
        max_length=100,
        blank=True,
        help_text=_('e.g., NIN number, certificate number')
    )
    
    # Verification
    verified = models.BooleanField(_('verified'), default=False)
    verified_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_verified',
        verbose_name=_('verified by')
    )
    verified_at = models.DateTimeField(_('verified at'), null=True, blank=True)
    
    # Additional information
    notes = models.TextField(_('notes'), blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.student}"


class Biometric(models.Model):
    """Student biometric data (fingerprints)"""
    
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='biometric',
        verbose_name=_('student')
    )
    
    # Fingerprint images
    left_thumb = models.ImageField(
        _('left thumb'),
        upload_to='biometrics/%Y/%m/%d/',
        null=True,
        blank=True
    )
    right_thumb = models.ImageField(
        _('right thumb'),
        upload_to='biometrics/%Y/%m/%d/',
        null=True,
        blank=True
    )
    
    # Capture information
    captured_at = models.DateTimeField(_('captured at'), auto_now_add=True)
    captured_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='biometrics_captured',
        verbose_name=_('captured by')
    )
    
    # Additional information
    notes = models.TextField(_('notes'), blank=True)
    
    # Timestamps
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Biometric')
        verbose_name_plural = _('Biometrics')
    
    def __str__(self):
        return f"Biometric - {self.student}"


class StudentSubject(models.Model):
    """Student subject registration for each session"""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='subject_registrations',
        verbose_name=_('student')
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.PROTECT,
        related_name='student_registrations',
        verbose_name=_('subject')
    )
    session = models.ForeignKey(
        'Session',
        on_delete=models.PROTECT,
        related_name='student_subject_registrations',
        verbose_name=_('session')
    )
    session_term = models.ForeignKey(
        'SessionTerm',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='student_subject_registrations',
        verbose_name=_('session term')
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    registered_at = models.DateTimeField(_('registered at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Subject')
        verbose_name_plural = _('Student Subjects')
        ordering = ['student', 'subject']
        unique_together = [['student', 'subject', 'session']]
    
    def __str__(self):
        return f"{self.student} - {self.subject} ({self.session})"
    
    def clean(self):
        """Validate subject registration"""
        super().clean()
        
        # Ensure subject belongs to student's class
        if self.subject.class_model != self.student.class_model:
            raise ValidationError(
                _('Subject must belong to the student\'s class')
            )
        
        # Ensure subject belongs to student's school
        if self.subject.school != self.student.school:
            raise ValidationError(
                _('Subject must belong to the student\'s school')
            )

