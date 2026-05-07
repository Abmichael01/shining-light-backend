from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class AdmissionExamResult(models.Model):
    """Overall result for an admission exam taken by an applicant"""
    student = models.OneToOneField('Student', on_delete=models.CASCADE, related_name='admission_result', verbose_name=_('student'))
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='admission_results', verbose_name=_('exam'))
    
    total_score = models.DecimalField(_('total score'), max_digits=6, decimal_places=2, default=0)
    total_marks = models.DecimalField(_('total marks'), max_digits=6, decimal_places=2, default=0)
    percentage = models.DecimalField(_('percentage'), max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(_('passed'), default=False)
    
    is_published = models.BooleanField(_('is published'), default=False)
    submitted_at = models.DateTimeField(_('submitted at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Admission Exam Result')
        verbose_name_plural = _('Admission Exam Results')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Admission Result: {self.student.get_full_name()} ({self.total_score}/{self.total_marks})"

class AdmissionExamSubjectResult(models.Model):
    """Subject-specific breakdown for an admission exam"""
    result = models.ForeignKey(AdmissionExamResult, on_delete=models.CASCADE, related_name='subject_results', verbose_name=_('exam result'))
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='admission_subject_results', verbose_name=_('subject'))
    
    score = models.DecimalField(_('score'), max_digits=5, decimal_places=2, default=0)
    total_marks = models.DecimalField(_('total marks'), max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = _('Admission Exam Subject Result')
        verbose_name_plural = _('Admission Exam Subject Results')
        unique_together = [['result', 'subject']]

    def __str__(self):
        return f"{self.subject.name}: {self.score}/{self.total_marks}"
