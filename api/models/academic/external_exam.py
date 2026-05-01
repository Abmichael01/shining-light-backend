from django.db import models
from django.utils.translation import gettext_lazy as _


class ExternalExamBody(models.Model):
    name = models.CharField(_('name'), max_length=100, unique=True)
    short_name = models.CharField(_('short name'), max_length=20)

    class Meta:
        verbose_name = _('External Exam Body')
        verbose_name_plural = _('External Exam Bodies')
        ordering = ['name']

    def __str__(self):
        return self.short_name


class ExternalExam(models.Model):
    SITTING_CHOICES = [
        ('may_june', 'May/June'),
        ('nov_dec', 'Nov/Dec'),
        ('annual', 'Annual'),
    ]

    body = models.ForeignKey(
        ExternalExamBody,
        on_delete=models.PROTECT,
        related_name='exams',
        verbose_name=_('exam body'),
    )
    year = models.PositiveIntegerField(_('year'))
    sitting = models.CharField(_('sitting'), max_length=20, choices=SITTING_CHOICES, blank=True)
    applicable_class = models.ForeignKey(
        'api.Class',
        on_delete=models.PROTECT,
        related_name='external_exams',
        verbose_name=_('applicable class'),
    )
    created_by = models.ForeignKey(
        'api.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_external_exams',
        verbose_name=_('created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('External Exam')
        verbose_name_plural = _('External Exams')
        ordering = ['-year', 'body']
        unique_together = [('body', 'year', 'sitting', 'applicable_class')]

    def __str__(self):
        sitting = f" ({self.get_sitting_display()})" if self.sitting else ""
        return f"{self.body.short_name} {self.year}{sitting}"


class ExternalExamResult(models.Model):
    exam = models.ForeignKey(
        ExternalExam,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('exam'),
    )
    student = models.ForeignKey(
        'api.Student',
        on_delete=models.CASCADE,
        related_name='external_exam_results',
        verbose_name=_('student'),
    )
    # Image/PDF upload of the official result slip
    result_file = models.FileField(
        _('result file'),
        upload_to='external_exams/results/',
        blank=True,
        null=True,
    )
    # Structured grades: [{"subject": "Mathematics", "grade": "A1"}, ...]
    grades = models.JSONField(_('grades'), blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('External Exam Result')
        verbose_name_plural = _('External Exam Results')
        unique_together = [('exam', 'student')]

    def __str__(self):
        return f"{self.student} — {self.exam}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.result_file and not self.grades:
            raise ValidationError('At least one of result file or grades must be provided.')


class ExternalExamAccess(models.Model):
    student = models.ForeignKey(
        'api.Student',
        on_delete=models.CASCADE,
        related_name='external_exam_accesses',
        verbose_name=_('student'),
    )
    exam = models.ForeignKey(
        ExternalExam,
        on_delete=models.CASCADE,
        related_name='accesses',
        verbose_name=_('exam'),
    )
    payment = models.OneToOneField(
        'api.FeePayment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_exam_access',
        verbose_name=_('payment'),
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('External Exam Access')
        verbose_name_plural = _('External Exam Accesses')
        unique_together = [('student', 'exam')]

    def __str__(self):
        return f"{self.student} — {self.exam} (access)"
