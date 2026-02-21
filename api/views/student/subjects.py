from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from api.models import (
    Student, StudentSubject, Staff as StaffModelAlias, 
    Class as ClassModelAlias, Subject as SubjectModelAlias
)
from api.serializers import StudentSubjectSerializer
from api.permissions import IsAdminOrStaffOrStudent
from django.db import models

from .subjects_reg import SubjectRegistrationMixin
from .subjects_logic import SubjectLogicMixin

class StudentSubjectViewSet(SubjectRegistrationMixin, SubjectLogicMixin, viewsets.ModelViewSet):
    """ViewSet for StudentSubject CRUD operations"""
    queryset = StudentSubject.objects.select_related(
        'student', 'subject', 'session', 'session_term', 'grade'
    ).all().order_by('-registered_at')
    serializer_class = StudentSubjectSerializer
    permission_classes = [IsAdminOrStaffOrStudent]
    
    def get_queryset(self):
        """Filter by student, subject, or session"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if getattr(user, 'user_type', None) == 'student':
            try:
                student = Student.objects.select_related('user').get(user=user)
                queryset = queryset.filter(student=student)
            except Student.DoesNotExist:
                return StudentSubject.objects.none()
        
        if getattr(user, 'user_type', None) == 'staff':
            staff = StaffModelAlias.objects.filter(user=user).first()
            assigned_classes = ClassModelAlias.objects.filter(
                models.Q(class_staff=user) | models.Q(assigned_teachers__user=user)
            ).distinct()
            assigned_subjects = SubjectModelAlias.objects.none()
            if staff:
                assigned_subjects = SubjectModelAlias.objects.filter(assigned_teachers=staff)
            queryset = queryset.filter(
                models.Q(student__class_model__in=assigned_classes) |
                models.Q(student__subject_registrations__subject__in=assigned_subjects)
            ).distinct()
        
        student = self.request.query_params.get('student', None)
        if student:
            queryset = queryset.filter(student=student)
        
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(subject=subject)
        
        session = self.request.query_params.get('session', None)
        if session:
            queryset = queryset.filter(session=session)
        
        session_term = self.request.query_params.get('session_term', None)
        if session_term:
            queryset = queryset.filter(session_term=session_term)
        
        return queryset
    
    def perform_update(self, serializer):
        user = self.request.user
        if getattr(user, 'user_type', None) != 'admin':
            raise PermissionDenied('Only administrators can update results.')
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        is_admin = getattr(user, 'user_type', None) == 'admin'
        is_owner = getattr(user, 'user_type', None) == 'student' and instance.student.user == user
        
        if not (is_admin or is_owner):
            raise PermissionDenied('You do not have permission to remove this subject registration.')
        super().perform_destroy(instance)
