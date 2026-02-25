from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .student import Student

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

    is_late_registration = models.BooleanField(_('is late registration'), default=False)
    late_fee_paid = models.BooleanField(_('late fee paid'), default=False)
    
    objective_score = models.DecimalField(
        _('objective score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('CBT Objective score')
    )
    theory_score = models.DecimalField(
        _('theory score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('Theory/Written examination score (max 40)')
    )
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
    
    position = models.PositiveIntegerField(
        _('position'),
        null=True,
        blank=True,
        help_text=_('Rank in class for this subject')
    )
    
    teacher_comment = models.TextField(
        _('teacher comment'),
        blank=True,
        help_text=_('Subject teacher\'s remark')
    )
    
    highest_score = models.DecimalField(
        _('highest score in class'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Highest score achieved in this class for this subject')
    )
    lowest_score = models.DecimalField(
        _('lowest score in class'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Lowest score achieved in this class for this subject')
    )
    subject_average = models.DecimalField(
        _('class average'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Average score of students in this class for this subject')
    )
    
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
    
    registered_at = models.DateTimeField(_('registered at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Subject')
        verbose_name_plural = _('Student Subjects')
        ordering = ['student', 'subject']
        unique_together = [['student', 'subject', 'session', 'session_term']]
    
    def __str__(self):
        return f"{self.student} - {self.subject} ({self.session})"
    
    def calculate_total(self):
        ca = self.ca_score or 0
        exam = self.exam_score or 0
        from decimal import Decimal
        return Decimal(str(ca)) + Decimal(str(exam))
    
    def calculate_exam_score(self):
        if self.objective_score is None and self.theory_score is None:
            return self.exam_score
        obj = self.objective_score or 0
        theory = self.theory_score or 0
        from decimal import Decimal
        return Decimal(str(obj)) + Decimal(str(theory))
    
    def calculate_grade(self):
        if self.total_score is not None:
            from api.models.academic import Grade
            return Grade.get_grade_for_score(float(self.total_score))
        return None
    
    def save(self, *args, **kwargs):
        self.exam_score = self.calculate_exam_score()
        if self.ca_score is not None or self.exam_score is not None:
            self.total_score = self.calculate_total()
            self.grade = self.calculate_grade()
        
        if self.cleared:
            if self.cleared_at is None:
                self.cleared_at = timezone.now()
        else:
            self.cleared_at = None
            self.cleared_by = None

        if self.openday_cleared:
            if self.openday_cleared_at is None:
                self.openday_cleared_at = timezone.now()
        else:
            self.openday_cleared_at = None
            self.openday_cleared_by = None
 
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        if self.subject.class_model != self.student.class_model:
            raise ValidationError(_('Subject must belong to the student\'s class'))
        if self.subject.school != self.student.school:
            raise ValidationError(_('Subject must belong to the student\'s school'))
        
        if self.ca_score is not None:
            ca_max = float(self.student.school.ca_max_score)
            if self.ca_score < 0 or self.ca_score > ca_max:
                raise ValidationError({'ca_score': _(f'CA score must be between 0 and {ca_max}')})
        
        if self.exam_score is not None:
            exam_max = float(self.student.school.exam_max_score)
            if self.exam_score < 0 or self.exam_score > exam_max:
                raise ValidationError({'exam_score': _(f'Exam score must be between 0 and {exam_max}')})
