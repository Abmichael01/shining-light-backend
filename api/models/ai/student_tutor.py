from django.db import models
from django.conf import settings
from api.models.student import Student
from api.models.academic import Subject, Topic

class StudentAITutorChat(models.Model):
    """
    Persistent chat session for the Student AI Tutor.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='ai_tutor_chats')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Tutor Chat - {self.student.user.get_full_name()} - {self.title or 'New Session'}"

class StudentAITutorMessage(models.Model):
    """
    Messages within a Student AI Tutor chat session.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    chat = models.ForeignKey(StudentAITutorChat, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    # Metadata for the interactive UI (e.g. current step, suggested actions)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role.capitalize()} at {self.created_at}"
