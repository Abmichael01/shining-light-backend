from django.db import models
from django.utils.translation import gettext_lazy as _
from .academic import Class, Subject, Question
from .student import Student
from django.conf import settings

class Assignment(models.Model):
    """
    Assignment created by staff for a specific class and subject.
    """
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    
    staff = models.ForeignKey(
        'Staff',
        on_delete=models.CASCADE,
        related_name='assignments_created',
        verbose_name=_('staff'),
        null=True,
        blank=True
    )
    
    class_model = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('class'),
        null=True,
        blank=True
    )
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('subject'),
        null=True,
        blank=True
    )
    
    questions = models.ManyToManyField(
        Question,
        related_name='assignments',
        verbose_name=_('questions')
    )
    
    due_date = models.DateTimeField(_('due date'), null=True, blank=True)
    is_published = models.BooleanField(_('is published'), default=False)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Assignment')
        verbose_name_plural = _('Assignments')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.class_model} {self.subject}"


class AssignmentSubmission(models.Model):
    """
    Student submission for an assignment.
    """
    SUBMISSION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('late', 'Late'),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_('assignment')
    )
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        verbose_name=_('student')
    )
    
    answers = models.JSONField(_('answers'), default=dict)
    
    # Store manual marks per question: {"question_id": score}
    marks = models.JSONField(_('marks'), default=dict, blank=True)
    
    score = models.DecimalField(
        _('score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=SUBMISSION_STATUS_CHOICES,
        default='pending'
    )
    
    feedback = models.TextField(_('feedback'), blank=True)
    
    submitted_at = models.DateTimeField(_('submitted at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    def calculate_score(self):
        """Calculate score for auto-gradable questions only"""
        if not self.answers:
            return 0
        
        total_marks = 0
        obtained_marks = 0
        
        # Get all questions associated with the assignment
        questions = self.assignment.questions.all()
        
        # Check if we can auto-grade everything
        # If there are manual questions (essay, file_upload), we can't fully grade yet
        # But we can calculate partial score for MCQs
        
        has_manual_questions = False
        
        for question in questions:
            total_marks += question.marks
            
            # If manual grading required
            if question.question_type in ['essay', 'file_upload']:
                has_manual_questions = True
                # Check if teacher has already graded this
                if str(question.id) in self.marks:
                     obtained_marks += float(self.marks.get(str(question.id), 0))
                continue

            # Auto-grading for others
            student_answer = self.answers.get(str(question.id))
            if student_answer and question.correct_answer and student_answer.lower() == question.correct_answer.lower():
                obtained_marks += question.marks
        
        if total_marks == 0:
            return 0
            
        return round((obtained_marks / total_marks) * 100, 2), has_manual_questions

    def save(self, *args, **kwargs):
        # Auto-grade logic
        if not self.pk and self.status == 'submitted' and self.score is None:
            calculated_score, has_manual_questions = self.calculate_score()
            self.score = calculated_score
            # We keep status as 'submitted' (Pending Review)
            # as per user requirement: assignments need teacher review before marking.

            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Assignment Submission')
        verbose_name_plural = _('Assignment Submissions')
        ordering = ['-submitted_at', '-created_at']
        unique_together = [['assignment', 'student']]

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"
