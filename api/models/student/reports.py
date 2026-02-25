from django.db import models
from django.utils.translation import gettext_lazy as _
from .student import Student

class TermReport(models.Model):
    """Overall term report for a student, including traits, skills and remarks"""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='term_reports',
        verbose_name=_('student')
    )
    session = models.ForeignKey(
        'api.Session',
        on_delete=models.PROTECT,
        related_name='term_reports',
        verbose_name=_('session')
    )
    session_term = models.ForeignKey(
        'api.SessionTerm',
        on_delete=models.PROTECT,
        related_name='term_reports',
        verbose_name=_('session term'),
        null=True,
        blank=True
    )
    
    # Affective Traits (Rating 1-5)
    punctuality = models.PositiveSmallIntegerField(_('punctuality'), default=0)
    mental_alertness = models.PositiveSmallIntegerField(_('mental alertness'), default=0)
    behavior = models.PositiveSmallIntegerField(_('behavior'), default=0)
    reliability = models.PositiveSmallIntegerField(_('reliability'), default=0)
    attentiveness = models.PositiveSmallIntegerField(_('attentiveness'), default=0)
    respect = models.PositiveSmallIntegerField(_('respect'), default=0)
    neatness = models.PositiveSmallIntegerField(_('neatness'), default=0)
    politeness = models.PositiveSmallIntegerField(_('politeness'), default=0)
    honesty = models.PositiveSmallIntegerField(_('honesty'), default=0)
    relationship_staff = models.PositiveSmallIntegerField(_('relationship with staff'), default=0)
    relationship_students = models.PositiveSmallIntegerField(_('relationship with students'), default=0)
    attitude_school = models.PositiveSmallIntegerField(_('attitude to school'), default=0)
    self_control = models.PositiveSmallIntegerField(_('self control'), default=0)
    
    # Psychomotor Skills (Rating 1-5)
    handwriting = models.PositiveSmallIntegerField(_('handwriting'), default=0)
    reading = models.PositiveSmallIntegerField(_('reading'), default=0)
    verbal_fluency = models.PositiveSmallIntegerField(_('verbal fluency'), default=0)
    musical_skills = models.PositiveSmallIntegerField(_('musical skills'), default=0)
    creative_arts = models.PositiveSmallIntegerField(_('creative arts'), default=0)
    physical_education = models.PositiveSmallIntegerField(_('physical education'), default=0)
    general_reasoning = models.PositiveSmallIntegerField(_('general reasoning'), default=0)
    
    class_teacher_report = models.TextField(_('class teacher report'), blank=True)
    ict_report = models.TextField(_('ict report'), blank=True)
    principal_report = models.TextField(_('principal report'), blank=True)
    
    days_present = models.PositiveIntegerField(_('days present'), null=True, blank=True)
    days_absent = models.PositiveIntegerField(_('days absent'), null=True, blank=True)
    total_days = models.PositiveIntegerField(_('total days'), null=True, blank=True)
    
    promoted_to = models.CharField(_('promoted to'), max_length=100, blank=True)
    
    total_score = models.DecimalField(_('overall total score'), max_digits=10, decimal_places=2, null=True, blank=True)
    average_score = models.DecimalField(_('average score'), max_digits=5, decimal_places=2, null=True, blank=True)
    cumulative_average = models.DecimalField(
        _('cumulative average'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Average of all term averages for the session (only for 3rd term)')
    )
    class_position = models.PositiveIntegerField(_('position in arm'), null=True, blank=True)
    grade_position = models.PositiveIntegerField(_('position in set'), null=True, blank=True)
    
    total_students = models.PositiveIntegerField(_('total students in arm'), null=True, blank=True)
    total_students_grade = models.PositiveIntegerField(_('total students in set'), null=True, blank=True)
    
    download_count = models.PositiveIntegerField(_('download count'), default=0)
    first_downloaded_at = models.DateTimeField(_('first downloaded at'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Term Report')
        verbose_name_plural = _('Term Reports')
        unique_together = [['student', 'session', 'session_term']]
        ordering = ['student', 'session', 'session_term']

    def __str__(self):
        return f"Report - {self.student} ({self.session_term or self.session})"
