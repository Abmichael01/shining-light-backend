from django.db import models
from django.conf import settings
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
    order = models.PositiveSmallIntegerField(_('display order'), default=0)
    
    # Assessment Configuration
    ca_max = models.DecimalField(
        _('CA maximum score'),
        max_digits=5,
        decimal_places=2,
        default=40,
        help_text=_('Maximum Continuous Assessment score (default: 40)')
    )
    exam_max = models.DecimalField(
        _('Exam maximum score'),
        max_digits=5,
        decimal_places=2,
        default=60,
        help_text=_('Maximum Examination score (default: 60)')
    )
    
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


class Topic(models.Model):
    """Topics within a subject for better question organization"""
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics',
        verbose_name=_('subject')
    )
    name = models.CharField(
        _('topic name'),
        max_length=200,
        help_text=_('e.g., Algebra, Geometry, Kinematics, Organic Chemistry')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        help_text=_('Brief description of what this topic covers')
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Inactive topics won\'t be available for exam creation')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')
        ordering = ['subject', 'name']
        unique_together = [['subject', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.subject.name})"
    
    @property
    def question_count(self):
        """Return the number of questions in this topic"""
        return self.questions.count()


class Grade(models.Model):
    """Configurable grading system - Admin can define grade ranges"""
    
    GRADE_LETTER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
        ('F', 'F'),
    ]
    
    grade_letter = models.CharField(
        _('grade letter'),
        max_length=1,
        choices=GRADE_LETTER_CHOICES,
        unique=True,
        help_text=_('Grade letter: A, B, C, D, E, or F')
    )
    grade_name = models.CharField(
        _('grade name'),
        max_length=20,
        help_text=_('Display name: A1, A+, B2, etc.')
    )
    grade_description = models.CharField(
        _('grade description'),
        max_length=100,
        help_text=_('Text description: Excellent, Very Good, Good, etc.')
    )
    min_score = models.DecimalField(
        _('minimum score'),
        max_digits=5,
        decimal_places=2,
        help_text=_('Minimum score for this grade (e.g., 75.00)')
    )
    max_score = models.DecimalField(
        _('maximum score'),
        max_digits=5,
        decimal_places=2,
        help_text=_('Maximum score for this grade (e.g., 100.00)')
    )
    order = models.PositiveSmallIntegerField(
        _('display order'),
        editable=False,
        help_text=_('Auto-generated from grade letter (A=1, B=2, etc.)')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Grade')
        verbose_name_plural = _('Grades')
        ordering = ['order', '-min_score']
    
    def __str__(self):
        return f"{self.grade_name} ({self.min_score}-{self.max_score})"
    
    def save(self, *args, **kwargs):
        """Auto-generate order from grade letter"""
        # Map grade letters to order (A=1, B=2, C=3, D=4, E=5, F=6)
        grade_order_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6}
        self.order = grade_order_map.get(self.grade_letter, 99)
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate grade ranges"""
        super().clean()
        
        # Ensure min_score is less than max_score
        if self.min_score >= self.max_score:
            raise ValidationError(_('Minimum score must be less than maximum score'))
        
        # Ensure scores are within 0-100
        if self.min_score < 0 or self.max_score > 100:
            raise ValidationError(_('Scores must be between 0 and 100'))
        
        # Check for overlapping grade ranges
        overlapping_grades = Grade.objects.exclude(pk=self.pk).filter(
            models.Q(min_score__lte=self.max_score, max_score__gte=self.min_score)
        )
        if overlapping_grades.exists():
            raise ValidationError(
                _('This grade range overlaps with existing grades: %(grades)s') % 
                {'grades': ', '.join([g.grade_name for g in overlapping_grades])}
            )
    
    @classmethod
    def get_grade_for_score(cls, score):
        """Get the appropriate grade for a given score"""
        try:
            return cls.objects.get(
                min_score__lte=score,
                max_score__gte=score
            )
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # If multiple grades match (shouldn't happen with proper validation), return the first
            return cls.objects.filter(
                min_score__lte=score,
                max_score__gte=score
            ).first()


class Question(models.Model):
    """Represents a question in the question bank for CBT"""
    
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
        ('short_answer', 'Short Answer'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('subject')
    )
    topic_model = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='questions',
        blank=True,
        null=True,
        verbose_name=_('topic'),
        help_text=_('Specific topic or unit this question covers')
    )
    question_text = models.TextField(
        _('question text'),
        help_text=_('The question text (supports HTML and LaTeX for math formulas)')
    )
    question_type = models.CharField(
        _('question type'),
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='multiple_choice'
    )
    difficulty = models.CharField(
        _('difficulty level'),
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium'
    )
    
    # For multiple choice questions
    option_a = models.TextField(_('option A'), blank=True, null=True)
    option_b = models.TextField(_('option B'), blank=True, null=True)
    option_c = models.TextField(_('option C'), blank=True, null=True)
    option_d = models.TextField(_('option D'), blank=True, null=True)
    option_e = models.TextField(_('option E'), blank=True, null=True)
    
    correct_answer = models.TextField(
        _('correct answer'),
        help_text=_('For multiple choice: A, B, C, D, or E. For true/false: True or False. For others: the complete answer')
    )
    
    # Additional information
    explanation = models.TextField(
        _('explanation'),
        blank=True,
        null=True,
        help_text=_('Explanation of the correct answer (supports HTML and LaTeX)')
    )
    marks = models.PositiveSmallIntegerField(
        _('marks'),
        default=1,
        help_text=_('Points awarded for correct answer')
    )
    
    # Status and usage tracking
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_('Indicates if the question has been reviewed and approved')
    )
    usage_count = models.PositiveIntegerField(
        _('usage count'),
        default=0,
        help_text=_('Number of times this question has been used in exams')
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_questions',
        verbose_name=_('created by')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'topic_model']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['question_type']),
        ]
    
    def __str__(self):
        topic_display = self.topic_model.name if self.topic_model else 'No Topic'
        return f"{self.subject.name} - {topic_display} ({self.get_difficulty_display()})"
    
    def clean(self):
        """Validate question based on type"""
        super().clean()
        
        # Validate multiple choice questions
        if self.question_type == 'multiple_choice':
            if not all([self.option_a, self.option_b, self.option_c, self.option_d]):
                raise ValidationError(_('Multiple choice questions must have at least 4 options (A-D)'))
            
            if self.correct_answer.upper() not in ['A', 'B', 'C', 'D', 'E']:
                raise ValidationError(_('Correct answer for multiple choice must be A, B, C, D, or E'))
            
            # Ensure the selected option actually exists
            option_map = {'A': self.option_a, 'B': self.option_b, 'C': self.option_c, 
                         'D': self.option_d, 'E': self.option_e}
            if not option_map.get(self.correct_answer.upper()):
                raise ValidationError(_('The selected correct answer option does not exist'))
        
        # Validate true/false questions
        elif self.question_type == 'true_false':
            if self.correct_answer.lower() not in ['true', 'false']:
                raise ValidationError(_('Correct answer for true/false must be True or False'))
    
    @property
    def school(self):
        """Get the school from the subject's class"""
        return self.subject.school if self.subject and self.subject.school else None
    
    @property
    def class_level(self):
        """Get the class level from the subject"""
        return self.subject.class_model
    
    def increment_usage(self):
        """Increment usage count when question is used in an exam"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class Exam(models.Model):
    """CBT Exam/Test configuration"""
    
    EXAM_TYPE_CHOICES = [
        ('test', 'Test'),
        ('exam', 'Examination'),
        ('quiz', 'Quiz'),
        ('practice', 'Practice'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(
        _('exam title'),
        max_length=200,
        help_text=_('e.g., Mathematics Mid-Term Test, Physics Final Exam')
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name=_('subject')
    )
    topics = models.ManyToManyField(
        Topic,
        blank=True,
        related_name='exams',
        verbose_name=_('topics'),
        help_text=_('Select topics for random question selection')
    )
    questions = models.ManyToManyField(
        Question,
        blank=True,
        related_name='exams',
        verbose_name=_('questions'),
        help_text=_('Select specific questions (use this OR topics, not both)')
    )
    exam_type = models.CharField(
        _('exam type'),
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default='test'
    )
    session_term = models.ForeignKey(
        SessionTerm,
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name=_('session term')
    )
    
    # Exam scheduling
    start_date = models.DateField(_('start date'))
    start_time = models.TimeField(_('start time'))
    end_date = models.DateField(_('end date'))
    end_time = models.TimeField(_('end time'))
    
    # Duration and configuration
    duration_minutes = models.PositiveIntegerField(
        _('duration (minutes)'),
        help_text=_('Total time allowed for the exam in minutes')
    )
    total_marks = models.PositiveIntegerField(
        _('total marks'),
        help_text=_('Total marks for the exam')
    )
    pass_mark = models.PositiveIntegerField(
        _('pass mark'),
        help_text=_('Minimum marks required to pass')
    )
    
    # Question selection
    total_questions = models.PositiveIntegerField(
        _('total questions'),
        help_text=_('Number of questions in the exam (auto-calculated from selected questions/topics)')
    )
    
    # Settings
    shuffle_questions = models.BooleanField(
        _('shuffle questions'),
        default=True,
        help_text=_('Randomize question order for each student')
    )
    shuffle_options = models.BooleanField(
        _('shuffle options'),
        default=True,
        help_text=_('Randomize option order for multiple choice questions')
    )
    show_results_immediately = models.BooleanField(
        _('show results immediately'),
        default=False,
        help_text=_('Show score to students after submission')
    )
    allow_review = models.BooleanField(
        _('allow review'),
        default=True,
        help_text=_('Allow students to review answers before submission')
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # Instructions
    instructions = models.TextField(
        _('instructions'),
        blank=True,
        null=True,
        help_text=_('Instructions to be shown to students before the exam')
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_exams',
        verbose_name=_('created by')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Exam')
        verbose_name_plural = _('Exams')
        ordering = ['-start_date', '-start_time']
        indexes = [
            models.Index(fields=['subject', 'session_term']),
            models.Index(fields=['status', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.subject.name})"
    
    def clean(self):
        """Validate exam configuration"""
        super().clean()
        
        # Validate dates
        if self.end_date < self.start_date:
            raise ValidationError(_('End date cannot be before start date'))
        
        if self.end_date == self.start_date and self.end_time <= self.start_time:
            raise ValidationError(_('End time must be after start time on the same day'))
        
        # Validate marks
        if self.pass_mark > self.total_marks:
            raise ValidationError(_('Pass mark cannot exceed total marks'))
    
    @property
    def is_active(self):
        """Check if exam is currently active"""
        from django.utils import timezone
        now = timezone.now()
        start_datetime = timezone.make_aware(timezone.datetime.combine(self.start_date, self.start_time))
        end_datetime = timezone.make_aware(timezone.datetime.combine(self.end_date, self.end_time))
        return self.status == 'active' and start_datetime <= now <= end_datetime
    
    @property
    def has_started(self):
        """Check if exam has started"""
        from django.utils import timezone
        now = timezone.now()
        start_datetime = timezone.make_aware(timezone.datetime.combine(self.start_date, self.start_time))
        return now >= start_datetime
    
    @property
    def has_ended(self):
        """Check if exam has ended"""
        from django.utils import timezone
        now = timezone.now()
        end_datetime = timezone.make_aware(timezone.datetime.combine(self.end_date, self.end_time))
        return now > end_datetime


class StudentExam(models.Model):
    """Student exam attempt/session"""
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]
    
    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name='exam_attempts',
        verbose_name=_('student')
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='student_attempts',
        verbose_name=_('exam')
    )
    
    # Timing
    started_at = models.DateTimeField(
        _('started at'),
        blank=True,
        null=True
    )
    submitted_at = models.DateTimeField(
        _('submitted at'),
        blank=True,
        null=True
    )
    time_remaining_seconds = models.PositiveIntegerField(
        _('time remaining (seconds)'),
        blank=True,
        null=True,
        help_text=_('Used for pause/resume functionality')
    )
    
    # Results
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    score = models.DecimalField(
        _('score'),
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Total marks obtained')
    )
    percentage = models.DecimalField(
        _('percentage'),
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    passed = models.BooleanField(
        _('passed'),
        blank=True,
        null=True
    )
    
    # Question order for this student (if shuffled)
    question_order = models.JSONField(
        _('question order'),
        blank=True,
        null=True,
        help_text=_('Randomized question order for this student: [question_id1, question_id2, ...]')
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Exam')
        verbose_name_plural = _('Student Exams')
        ordering = ['-created_at']
        unique_together = [['student', 'exam']]
        indexes = [
            models.Index(fields=['student', 'exam']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.exam.title}"
    
    def calculate_score(self):
        """Calculate total score from answers"""
        total = 0
        for answer in self.answers.all():
            if answer.is_correct:
                total += answer.marks_obtained
        
        self.score = total
        self.percentage = (total / self.exam.total_marks) * 100 if self.exam.total_marks > 0 else 0
        self.passed = self.score >= self.exam.pass_mark
        self.status = 'graded'
        self.save()
        
        return self.score


class StudentAnswer(models.Model):
    """Student's answer to an exam question"""
    
    student_exam = models.ForeignKey(
        StudentExam,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('student exam')
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_answers',
        verbose_name=_('question')
    )
    question_number = models.PositiveSmallIntegerField(
        _('question number'),
        help_text=_('Question number in the exam')
    )
    
    # Answer data
    answer_text = models.TextField(
        _('answer text'),
        help_text=_('Student\'s answer (A, B, C, D, E for multiple choice, or text for other types)')
    )
    is_correct = models.BooleanField(
        _('is correct'),
        blank=True,
        null=True
    )
    marks_obtained = models.DecimalField(
        _('marks obtained'),
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Metadata
    answered_at = models.DateTimeField(_('answered at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Answer')
        verbose_name_plural = _('Student Answers')
        ordering = ['student_exam', 'question_number']
        unique_together = [['student_exam', 'question']]
    
    def __str__(self):
        return f"{self.student_exam.student} - Q{self.question_number}"
    
    def auto_grade(self):
        """Auto-grade the answer for multiple choice and true/false questions"""
        if self.question.question_type in ['multiple_choice', 'true_false']:
            # Compare answers (case-insensitive)
            self.is_correct = self.answer_text.strip().upper() == self.question.correct_answer.strip().upper()
            
            if self.is_correct:
                self.marks_obtained = self.question.marks
            else:
                self.marks_obtained = 0
            
            self.save()
        
        return self.is_correct

