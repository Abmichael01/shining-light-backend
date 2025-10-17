from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction


class School(models.Model):
    """Represents school divisions: Nursery, Primary, Junior Secondary, Senior Secondary"""
    
    SCHOOL_TYPE_CHOICES = [
        ('Nursery', 'Nursery School'),
        ('Primary', 'Primary School'),
        ('Junior Secondary', 'Junior Secondary School'),
        ('Senior Secondary', 'Senior Secondary School'),
    ]
    
    id = models.CharField(_('id'), max_length=10, primary_key=True, editable=False)
    name = models.CharField(_('school name'), max_length=100)
    school_type = models.CharField(_('school type'), max_length=20, choices=SCHOOL_TYPE_CHOICES, unique=True)
    code = models.CharField(_('school code'), max_length=10, unique=True, editable=False)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('School')
        verbose_name_plural = _('Schools')
        ordering = ['school_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.school_type})"
    
    def save(self, *args, **kwargs):
        """Auto-generate unique code from school_type and use it as id"""
        if not self.code:
            code_map = {
                'Nursery': 'NUR',
                'Primary': 'PRM',
                'Junior Secondary': 'JNR',
                'Senior Secondary': 'SNR',
            }
            base_code = code_map.get(self.school_type, 'SCH')
            
            # Find the next available number for this school type
            existing_schools = School.objects.filter(
                code__startswith=base_code
            ).exclude(pk=self.pk).count()
            
            # Generate code with counter: NUR-001, NUR-002, etc.
            counter = existing_schools + 1
            self.code = f"{base_code}-{counter:03d}"
            
            # Ensure uniqueness
            while School.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                counter += 1
                self.code = f"{base_code}-{counter:03d}"
        
        # Set id to be the same as code
        if not self.id:
            self.id = self.code
        
        super().save(*args, **kwargs)


# Term model removed - SessionTerm handles everything directly


class Session(models.Model):
    """Academic session/year (e.g., 2024/2025)"""
    
    name = models.CharField(_('session name'), max_length=20, unique=True)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_current = models.BooleanField(_('current session'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Session')
        verbose_name_plural = _('Sessions')
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name}{'*' if self.is_current else ''}"
    
    def clean(self):
        """Validate that end_date is after start_date"""
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(_('End date must be after start date'))
    
    def save(self, *args, **kwargs):
        # Ensure only one session is current
        if self.is_current:
            with transaction.atomic():
                Session.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        
        # Save the session first
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-create only the first SessionTerm for new sessions
        if is_new:
            self._create_first_session_term()
    
    def _create_first_session_term(self):
        """Create only the 1st Term SessionTerm when session is created"""
        SessionTerm.objects.get_or_create(
            session=self,
            term_name='1st Term',
            defaults={
                'start_date': self.start_date,
                'end_date': self.end_date,
                'is_current': True  # First term is current by default
            }
        )
    
    def create_next_term(self, term_name, start_date, end_date):
        """
        Helper method to create the next SessionTerm
        Admin calls this when starting 2nd or 3rd term
        """
        # Deactivate current term
        SessionTerm.objects.filter(session=self, is_current=True).update(is_current=False)
        
        # Create and activate new term
        session_term, created = SessionTerm.objects.get_or_create(
            session=self,
            term_name=term_name,
            defaults={
                'start_date': start_date,
                'end_date': end_date,
                'is_current': True
            }
        )
        
        if not created:
            # If term already exists, just update and activate
            session_term.start_date = start_date
            session_term.end_date = end_date
            session_term.is_current = True
            session_term.save()
        
        return session_term
    
    @classmethod
    def get_current_session_term(cls):
        """Get the currently active session term"""
        current_session = cls.objects.filter(is_current=True).first()
        if current_session:
            return current_session.session_terms.filter(is_current=True).first()
        return None
    
    def clean(self):
        """Validate session dates"""
        super().clean()
        
        # End date must be after start date
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(_('End date must be after start date'))
        
        # Check for overlapping sessions
        from django.db.models import Q
        overlapping = Session.objects.filter(
            Q(start_date__range=(self.start_date, self.end_date)) |
            Q(end_date__range=(self.start_date, self.end_date)) |
            Q(start_date__lte=self.start_date, end_date__gte=self.end_date)
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError(_('Session dates overlap with existing session'))


class SessionTerm(models.Model):
    """Academic term within a session (e.g., 1st Term 2024/2025)"""
    
    TERM_CHOICES = [
        ('1st Term', '1st Term'),
        ('2nd Term', '2nd Term'),
        ('3rd Term', '3rd Term'),
    ]
    
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='session_terms',
        verbose_name=_('session')
    )
    term_name = models.CharField(
        _('term name'),
        max_length=20,
        choices=TERM_CHOICES
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_current = models.BooleanField(_('current term'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Session Term')
        verbose_name_plural = _('Session Terms')
        ordering = ['session', 'term_name']
        unique_together = [['session', 'term_name']]
    
    def __str__(self):
        return f"{self.term_name} - {self.session.name}{'*' if self.is_current else ''}"
    
    @property
    def term_order(self):
        """Get the order of this term (1, 2, or 3)"""
        order_map = {
            '1st Term': 1,
            '2nd Term': 2,
            '3rd Term': 3,
        }
        return order_map.get(self.term_name, 0)
    
    def clean(self):
        """Validate dates"""
        super().clean()
        
        # End date must be after start date
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(_('End date must be after start date'))
        
        # SessionTerm dates must fall within Session dates
        if self.session and self.start_date and self.end_date:
            if self.start_date < self.session.start_date:
                raise ValidationError(_('Term start date cannot be before session start date'))
            if self.end_date > self.session.end_date:
                raise ValidationError(_('Term end date cannot be after session end date'))
    
    def save(self, *args, **kwargs):
        # Ensure only one term is current per session
        if self.is_current:
            with transaction.atomic():
                SessionTerm.objects.filter(
                    session=self.session,
                    is_current=True
                ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Class(models.Model):
    """Represents a class level (e.g., Nursery 1, Primary 1, JSS 1, SSS 2)"""
    
    id = models.CharField(_('id'), max_length=10, primary_key=True, editable=False)
    name = models.CharField(_('class name'), max_length=50, help_text=_('e.g., Nursery 1, Primary 1, JSS 1, SSS 2'))
    class_code = models.CharField(
        _('class code'),
        max_length=10,
        unique=True,
        help_text=_('Short code for class, e.g., SS1, JSS2, PRI1, NUR1')
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='classes',
        verbose_name=_('school')
    )
    class_staff = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_assigned',
        verbose_name=_('class staff')
    )
    order = models.PositiveSmallIntegerField(_('display order'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Class')
        verbose_name_plural = _('Classes')
        ordering = ['school', 'order', 'name']
        unique_together = [['school', 'name']]  # Prevent duplicate class names per school
    
    def __str__(self):
        return f"{self.name} ({self.school.school_type})"
    
    def save(self, *args, **kwargs):
        """Set id to be the same as class_code"""
        if self.class_code and not self.id:
            self.id = self.class_code
        super().save(*args, **kwargs)


class Department(models.Model):
    """Department for Senior School (Science, Arts, Commercial)"""
    
    name = models.CharField(_('department name'), max_length=100)
    code = models.CharField(_('department code'), max_length=10)
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='departments',
        verbose_name=_('school')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['school', 'name']
        unique_together = [['school', 'code']]
    
    def __str__(self):
        return f"{self.name} ({self.school.name})"


class SubjectGroup(models.Model):
    """Groups subjects together (e.g., Science Subjects, Arts Subjects, Trade Subjects)"""
    
    SELECTION_TYPE_CHOICES = [
        ('single', 'Single Selection'),
        ('multiple', 'Multiple Selection'),
    ]
    
    name = models.CharField(_('group name'), max_length=100, unique=True)
    code = models.CharField(_('group code'), max_length=10, blank=True)
    selection_type = models.CharField(
        _('selection type'),
        max_length=10,
        choices=SELECTION_TYPE_CHOICES,
        default='multiple',
        help_text=_('Single: student selects one, Multiple: student can select multiple')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Subject Group')
        verbose_name_plural = _('Subject Groups')
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        # Auto-generate code from name if not provided
        if not self.code:
            # Take first 3 letters of each word, uppercase
            words = self.name.upper().split()
            if len(words) == 1:
                self.code = words[0][:6]  # If single word, take first 6 chars
            else:
                self.code = ''.join([word[:3] for word in words[:2]])  # First 3 chars of first 2 words
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Subject(models.Model):
    """Individual subject with all details"""
    
    id = models.CharField(_('id'), max_length=50, primary_key=True, editable=False)
    name = models.CharField(_('subject name'), max_length=200)
    code = models.CharField(_('subject code'), max_length=50, unique=True, blank=True, help_text=_('Auto-generated from subject name and class code'))
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='subjects',
        verbose_name=_('school')
    )
    class_model = models.ForeignKey(
        Class,
        on_delete=models.PROTECT,
        related_name='subjects',
        verbose_name=_('class')
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects',
        verbose_name=_('department'),
        help_text=_('Only for Senior School subjects')
    )
    subject_group = models.ForeignKey(
        SubjectGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subjects',
        verbose_name=_('subject group')
    )
    is_core = models.BooleanField(_('core/compulsory'), default=False)
    is_trade = models.BooleanField(_('trade subject'), default=False)
    order = models.PositiveSmallIntegerField(_('display order'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
        ordering = ['school', 'class_model', 'order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def _generate_subject_code(self):
        """Generate subject code: SUBJECTNAME-CLASSCODE"""
        # Get subject name in uppercase with spaces replaced by hyphens
        subject_part = self.name.upper().replace(' ', '-')
        
        # Get class code (e.g., SS1, JSS2, PRI1)
        class_code = self.class_model.class_code.upper()
        
        # Build code: ENGLISH-LANGUAGE-SS1, MATHEMATICS-JSS2
        base_code = f"{subject_part}-{class_code}"
        
        return base_code
    
    def save(self, *args, **kwargs):
        """Auto-generate code if not provided and use it as id"""
        if not self.code:
            # Generate base code
            base_code = self._generate_subject_code()
            self.code = base_code
            
            # Ensure uniqueness by adding counter if needed
            counter = 1
            original_code = self.code
            while Subject.objects.filter(code=self.code).exists():
                self.code = f"{base_code}-{counter}"
                counter += 1
        
        # Set id to be the same as code
        if not self.id:
            self.id = self.code
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate subject relationships"""
        super().clean()
        
        # Department should only be set for Senior Secondary School
        if self.department and self.school.school_type != 'Senior Secondary':
            raise ValidationError(_('Department can only be set for Senior Secondary School subjects'))
        
        # Department must belong to the same school
        if self.department and self.department.school != self.school:
            raise ValidationError(_('Department must belong to the same school as the subject'))
        
        # Subject group must belong to same class
        if self.subject_group and self.subject_group.class_model != self.class_model:
            raise ValidationError(_('Subject group must belong to the same class'))

