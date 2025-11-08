from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import date
from django.utils import timezone


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
    
    # Override default id field with readable format
    id = models.CharField(
        _('student ID'),
        max_length=20,
        primary_key=True,
        help_text=_('Human-readable ID like STU-001ABC')
    )
    
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
        help_text=_('Auto-generated on acceptance (Format: YYYYMMDD + Serial)')
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
    club = models.ForeignKey(
        'Club',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name=_('club'),
        help_text=_('Student club or society membership')
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
        # Only auto-generate if admission_number is None or empty string
        if self.status in ['accepted', 'enrolled']:
            if not self.admission_number or self.admission_number.strip() == '':
                print(f'📝 Auto-generating admission number for student (status: {self.status})')
                self.admission_number = self._generate_admission_number()
                print(f'✅ Generated admission number: {self.admission_number}')
            else:
                print(f'✅ Using provided admission number: {self.admission_number}')
        
        # Generate readable id if not set
        if not self.id:
            from ..utils.id_generator import generate_student_id
            self.id = generate_student_id()
        
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
        """
        Generate unique admission number based on date of birth + serial number
        Format: YYYYMMDD + Serial Number (2 digits)
        Example: Date of birth 2012-06-15 → 20120615 + 02 → 2012061502
        """
        # Check if biodata exists and has date of birth
        if not hasattr(self, 'biodata') or not self.biodata or not self.biodata.date_of_birth:
            raise ValidationError(_('Student biodata with date of birth is required to generate admission number'))
        
        # Format: YYYYMMDD from date of birth
        dob_prefix = self.biodata.date_of_birth.strftime('%Y%m%d')
        
        # Get the last admission number with the same date of birth prefix
        last_student = Student.objects.filter(
            admission_number__startswith=dob_prefix
        ).exclude(admission_number='').order_by('admission_number').last()
        
        if last_student:
            # Extract the serial number (last 2 digits)
            try:
                last_serial = int(last_student.admission_number[-2:])
                new_serial = last_serial + 1
            except (ValueError, IndexError):
                new_serial = 1
        else:
            new_serial = 1
        
        # Ensure serial number doesn't exceed 99
        if new_serial > 99:
            raise ValidationError(
                _('Maximum number of students with the same date of birth (99) has been reached')
            )
        
        return f"{dob_prefix}{new_serial:02d}"
    
    def delete(self, *args, **kwargs):
        """Override delete to also delete associated user account"""
        user = self.user
        
        # Delete student first (Django CASCADE will handle all related records automatically)
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
    """Student subject registration and results for each session"""
    
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
    
    # Registration Status
    is_active = models.BooleanField(_('active'), default=True)
    cleared = models.BooleanField(_('cleared'), default=False)
    cleared_at = models.DateTimeField(_('cleared at'), null=True, blank=True)
    cleared_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_subjects_cleared',
        verbose_name=_('cleared by')
    )

    # Open Day clearance (staff-facing)
    openday_cleared = models.BooleanField(_('open day cleared'), default=False)
    openday_cleared_at = models.DateTimeField(_('open day cleared at'), null=True, blank=True)
    openday_cleared_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='open_day_cleared_subjects',
        verbose_name=_('open day cleared by')
    )
    openday_clearance_notes = models.TextField(_('open day clearance notes'), blank=True)
    openday_clearance_checklist = models.JSONField(
        _('open day clearance checklist'),
        blank=True,
        default=dict
    )
    
    # Result/Assessment Scores
    ca_score = models.DecimalField(
        _('CA score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('Continuous Assessment score (max 40)')
    )
    exam_score = models.DecimalField(
        _('exam score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('Examination score (max 60)')
    )
    total_score = models.DecimalField(
        _('total score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('Total = CA + Exam (max 100)')
    )
    grade = models.ForeignKey(
        'Grade',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_subjects',
        verbose_name=_('grade'),
        help_text=_('Auto-calculated based on total score')
    )
    
    # Position/Rank
    position = models.PositiveIntegerField(
        _('position'),
        null=True,
        blank=True,
        help_text=_('Rank in class for this subject')
    )
    
    # Teacher's Remark
    teacher_comment = models.TextField(
        _('teacher comment'),
        blank=True,
        help_text=_('Subject teacher\'s remark')
    )
    
    # Result Entry Tracking
    result_entered_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='results_entered',
        verbose_name=_('result entered by')
    )
    result_entered_at = models.DateTimeField(
        _('result entered at'),
        null=True,
        blank=True
    )
    
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
    
    def calculate_total(self):
        """Calculate total score from CA and Exam"""
        if self.ca_score is not None and self.exam_score is not None:
            from decimal import Decimal
            return Decimal(str(self.ca_score)) + Decimal(str(self.exam_score))
        return None
    
    def calculate_grade(self):
        """Automatically determine grade based on total score"""
        if self.total_score is not None:
            from api.models.academic import Grade
            return Grade.get_grade_for_score(float(self.total_score))
        return None
    
    def save(self, *args, **kwargs):
        """Auto-calculate total score and grade"""
        # Calculate total if CA and Exam are provided
        if self.ca_score is not None and self.exam_score is not None:
            self.total_score = self.calculate_total()
            
            # Auto-determine grade based on total
            if self.total_score is not None:
                self.grade = self.calculate_grade()
        
        # Manage admin clearance metadata
        if self.cleared:
            if self.cleared_at is None:
                self.cleared_at = timezone.now()
            if self.cleared_by_id is None:
                self.cleared_by = self.cleared_by or None
        else:
            self.cleared_at = None
            self.cleared_by = None

        # Manage open day clearance metadata
        if self.openday_cleared:
            if self.openday_cleared_at is None:
                self.openday_cleared_at = timezone.now()
            if self.openday_clearance_checklist is None:
                self.openday_clearance_checklist = {}
        else:
            self.openday_cleared_at = None
            self.openday_cleared_by = None
            self.openday_clearance_notes = ''
            self.openday_clearance_checklist = {}
 
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate subject registration and scores"""
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
        
        # Validate CA score against subject's ca_max
        if self.ca_score is not None:
            ca_max = float(self.subject.ca_max)
            if self.ca_score < 0 or self.ca_score > ca_max:
                raise ValidationError({
                    'ca_score': _(f'CA score must be between 0 and {ca_max}')
                })
        
        # Validate exam score against subject's exam_max
        if self.exam_score is not None:
            exam_max = float(self.subject.exam_max)
            if self.exam_score < 0 or self.exam_score > exam_max:
                raise ValidationError({
                    'exam_score': _(f'Exam score must be between 0 and {exam_max}')
                })

