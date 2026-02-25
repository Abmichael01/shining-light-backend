from django.db import models
from django.utils.translation import gettext_lazy as _
from .exams import Exam, Question

class StudentExam(models.Model):
    """Student exam attempt/session"""
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='exam_attempts', verbose_name=_('student'))
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_attempts', verbose_name=_('exam'))
    
    started_at = models.DateTimeField(_('started at'), blank=True, null=True)
    submitted_at = models.DateTimeField(_('submitted at'), blank=True, null=True)
    time_remaining_seconds = models.PositiveIntegerField(_('time remaining (seconds)'), blank=True, null=True)
    
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='not_started')
    score = models.DecimalField(_('score'), max_digits=6, decimal_places=2, blank=True, null=True)
    percentage = models.DecimalField(_('percentage'), max_digits=5, decimal_places=2, blank=True, null=True)
    passed = models.BooleanField(_('passed'), blank=True, null=True)
    
    question_order = models.JSONField(_('question order'), blank=True, null=True)
    
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
    
    student_exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, related_name='answers', verbose_name=_('student exam'))
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_answers', verbose_name=_('question'))
    question_number = models.PositiveSmallIntegerField(_('question number'))
    
    answer_text = models.TextField(_('answer text'))
    is_correct = models.BooleanField(_('is correct'), blank=True, null=True)
    marks_obtained = models.DecimalField(_('marks obtained'), max_digits=5, decimal_places=2, default=0)
    
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
        if self.question.question_type in ['multiple_choice', 'true_false']:
            self.is_correct = self.answer_text.strip().upper() == self.question.correct_answer.strip().upper()
            if self.is_correct:
                self.marks_obtained = self.question.marks
            else:
                self.marks_obtained = 0
            self.save()
        return self.is_correct
