from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from .curriculum import Subject, Topic
from .sessions import SessionTerm
from .classes import Class, ExamHall

class Question(models.Model):
    """Represents a question in the question bank for CBT"""
    
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
        ('short_answer', 'Short Answer'),
        ('file_upload', 'File Upload'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions', verbose_name=_('subject'))
    topic_model = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions', blank=True, null=True, verbose_name=_('topic'))
    question_text = models.TextField(_('question text'))
    question_type = models.CharField(_('question type'), max_length=20, choices=QUESTION_TYPE_CHOICES, default='multiple_choice')
    difficulty = models.CharField(_('difficulty level'), max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    
    option_a = models.TextField(_('option A'), blank=True, null=True)
    option_b = models.TextField(_('option B'), blank=True, null=True)
    option_c = models.TextField(_('option C'), blank=True, null=True)
    option_d = models.TextField(_('option D'), blank=True, null=True)
    option_e = models.TextField(_('option E'), blank=True, null=True)
    
    correct_answer = models.TextField(_('correct answer'))
    explanation = models.TextField(_('explanation'), blank=True, null=True)
    marks = models.PositiveSmallIntegerField(_('marks'), default=1)
    
    is_verified = models.BooleanField(_('verified'), default=False)
    usage_count = models.PositiveIntegerField(_('usage count'), default=0)

    question_image = models.ImageField(_('question image'), upload_to='cbt/questions/', blank=True, null=True)
    option_a_image = models.ImageField(upload_to='cbt/options/', blank=True, null=True)
    option_b_image = models.ImageField(upload_to='cbt/options/', blank=True, null=True)
    option_c_image = models.ImageField(upload_to='cbt/options/', blank=True, null=True)
    option_d_image = models.ImageField(upload_to='cbt/options/', blank=True, null=True)
    option_e_image = models.ImageField(upload_to='cbt/options/', blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_questions', verbose_name=_('created by'))
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
        super().clean()
        if self.question_type == 'multiple_choice':
            if not all([self.option_a, self.option_b, self.option_c, self.option_d]):
                raise ValidationError(_('Multiple choice questions must have at least 4 options (A-D)'))
            if self.correct_answer.upper() not in ['A', 'B', 'C', 'D', 'E']:
                raise ValidationError(_('Correct answer for multiple choice must be A, B, C, D, or E'))
            option_map = {'A': self.option_a, 'B': self.option_b, 'C': self.option_c, 'D': self.option_d, 'E': self.option_e}
            if not option_map.get(self.correct_answer.upper()):
                raise ValidationError(_('The selected correct answer option does not exist'))
        elif self.question_type == 'true_false':
            if self.correct_answer.lower() not in ['true', 'false']:
                raise ValidationError(_('Correct answer for true/false must be True or False'))
    
    @property
    def school(self):
        return self.subject.school if self.subject and self.subject.school else None
    
    @property
    def class_level(self):
        return self.subject.class_model
    
    def increment_usage(self):
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class Exam(models.Model):
    """CBT Exam/Test configuration"""
    
    id = models.CharField(_('exam ID'), max_length=20, primary_key=True, editable=False)
    
    EXAM_TYPE_CHOICES = [('test', 'Test'), ('exam', 'Examination'), ('quiz', 'Quiz'), ('practice', 'Practice')]
    STATUS_CHOICES = [('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    
    title = models.CharField(_('exam title'), max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams', verbose_name=_('subject'), null=True, blank=True)
    exam_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='admission_exams', verbose_name=_('exam class'))
    topics = models.ManyToManyField(Topic, blank=True, related_name='exams', verbose_name=_('topics'))
    questions = models.ManyToManyField(Question, blank=True, related_name='exams', verbose_name=_('questions'))
    exam_type = models.CharField(_('exam type'), max_length=20, choices=EXAM_TYPE_CHOICES, default='test')
    session_term = models.ForeignKey(SessionTerm, on_delete=models.CASCADE, related_name='exams', verbose_name=_('session term'))
    
    duration_minutes = models.PositiveIntegerField(_('duration (minutes)'))
    total_marks = models.PositiveIntegerField(_('total marks'))
    pass_mark = models.PositiveIntegerField(_('pass mark'))
    total_questions = models.PositiveIntegerField(_('total questions'))
    
    shuffle_questions = models.BooleanField(_('shuffle questions'), default=True)
    shuffle_options = models.BooleanField(_('shuffle options'), default=True)
    show_results_immediately = models.BooleanField(_('show results immediately'), default=False)
    allow_review = models.BooleanField(_('allow review'), default=True)
    allow_calculator = models.BooleanField(_('allow calculator'), default=False)
    
    is_applicant_exam = models.BooleanField(_('is applicant exam'), default=False)
    question_selection_count = models.PositiveIntegerField(_('question selection count'), null=True, blank=True)
    
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    instructions = models.TextField(_('instructions'), blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_exams', verbose_name=_('created by'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Exam')
        verbose_name_plural = _('Exams')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'session_term']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.subject.name if self.subject else 'General'})"
    
    def save(self, *args, **kwargs):
        if not self.id:
            from api.utils.id_generator import generate_exam_id
            self.id = generate_exam_id()
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        if self.pass_mark > self.total_marks:
            raise ValidationError(_('Pass mark cannot exceed total marks'))
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def can_be_taken(self):
        return self.status == 'active'


class CBTExamCode(models.Model):
    """Stores CBT exam passcodes with exam hall and seat assignment"""
    
    id = models.CharField(_('id'), max_length=20, primary_key=True, editable=False)
    code = models.CharField(_('passcode'), max_length=6, unique=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='cbt_codes', verbose_name=_('exam'), null=True, blank=True)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='cbt_exam_codes', verbose_name=_('student'))
    exam_hall = models.ForeignKey(ExamHall, on_delete=models.SET_NULL, related_name='cbt_codes', verbose_name=_('exam hall'), null=True, blank=True)
    seat_number = models.PositiveIntegerField(_('seat number'), null=True, blank=True)
    is_used = models.BooleanField(_('used'), default=False)
    used_at = models.DateTimeField(_('used at'), null=True, blank=True)
    expires_at = models.DateTimeField(_('expires at'))
    
    access_start_datetime = models.DateTimeField(_('access start datetime'), null=True, blank=True)
    access_end_datetime = models.DateTimeField(_('access end datetime'), null=True, blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_cbt_codes', verbose_name=_('created by'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('CBT Exam Code')
        verbose_name_plural = _('CBT Exam Codes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['student', 'is_used']),
            models.Index(fields=['exam_hall', 'seat_number']),
        ]
    
    def __str__(self):
        status = "Used" if self.is_used else "Active"
        hall_info = f" - {self.exam_hall.name}" if self.exam_hall else ""
        seat_info = f" Seat {self.seat_number}" if self.seat_number else ""
        return f"{self.code} ({self.student}) {hall_info}{seat_info} - {status}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            import random
            import string
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.id = f"CBTCODE-{random_code}"
            while CBTExamCode.objects.filter(id=self.id).exists():
                random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                self.id = f"CBTCODE-{random_code}"
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        if self.seat_number and not self.exam_hall:
            raise ValidationError(_('Seat number requires an exam hall'))
        if self.exam_hall and self.seat_number:
            if self.seat_number > self.exam_hall.number_of_seats:
                raise ValidationError(_(f'Seat number {self.seat_number} exceeds hall capacity of {self.exam_hall.number_of_seats}'))
    
    def mark_as_used(self):
        if not self.is_used:
            self.is_used = True
            self.used_at = timezone.now()
            self.save(update_fields=['is_used', 'used_at'])
