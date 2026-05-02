from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from api.models import (
    ResultScoreSubmission, Student, StudentSubject, SystemSetting, Staff as StaffModelAlias,
    Class as ClassModelAlias, Subject as SubjectModelAlias
)
from api.serializers import ResultScoreSubmissionSerializer, StudentSubjectSerializer
from api.permissions import IsAdminOrStaff, IsAdminOrStaffOrStudent, IsSchoolAdmin
from django.db import models
from django.utils import timezone

from .subjects_reg import SubjectRegistrationMixin
from .subjects_logic import SubjectLogicMixin

class StudentSubjectViewSet(SubjectRegistrationMixin, SubjectLogicMixin, viewsets.ModelViewSet):
    """ViewSet for StudentSubject CRUD operations"""
    queryset = StudentSubject.objects.select_related(
        'student', 'student__biodata', 'subject', 'session', 'session_term', 'grade'
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


class ResultScoreSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin/staff view for pending teacher score submissions."""
    queryset = ResultScoreSubmission.objects.select_related(
        'student_subject',
        'student_subject__student',
        'student_subject__student__biodata',
        'student_subject__subject',
        'student_subject__subject__class_model',
        'student_subject__session',
        'student_subject__session_term',
        'submitted_by',
        'reviewed_by',
    ).all()
    serializer_class = ResultScoreSubmissionSerializer
    permission_classes = [IsAdminOrStaff]

    def _is_admin_like(self, user):
        return getattr(user, 'is_superuser', False) or getattr(user, 'user_type', '') == 'admin'

    def _staff_subject_filter(self, user):
        staff = getattr(user, 'staff_profile', None)
        if not staff:
            return models.Q(pk__isnull=True)
        assigned_classes = ClassModelAlias.objects.filter(
            models.Q(class_staff=user) | models.Q(assigned_teachers__user=user)
        ).distinct()
        assigned_subjects = SubjectModelAlias.objects.filter(assigned_teachers=staff)
        return (
            models.Q(submitted_by=user) |
            models.Q(student_subject__subject__in=assigned_subjects) |
            models.Q(student_subject__subject__class_model__in=assigned_classes)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not self._is_admin_like(user):
            queryset = queryset.filter(self._staff_subject_filter(user)).distinct()

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        subject = self.request.query_params.get('subject')
        if subject:
            queryset = queryset.filter(student_subject__subject_id=subject)

        session = self.request.query_params.get('session')
        if session:
            queryset = queryset.filter(student_subject__session_id=session)

        session_term = self.request.query_params.get('session_term')
        if session_term:
            queryset = queryset.filter(student_subject__session_term_id=session_term)

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsSchoolAdmin])
    def approve(self, request, pk=None):
        submission = self.get_object()
        if submission.status != 'pending':
            return Response({'error': 'Only pending submissions can be approved.'}, status=status.HTTP_400_BAD_REQUEST)

        settings_obj = SystemSetting.load()
        serializer = StudentSubjectSerializer(
            submission.student_subject,
            data=submission.proposed_scores,
            partial=True,
            context={
                **self.get_serializer_context(),
                'allow_ca_score_editing': settings_obj.allow_ca_score_editing,
            },
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(
            result_entered_by=submission.submitted_by or request.user,
            result_entered_at=timezone.now(),
        )

        submission.status = 'approved'
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.rejection_reason = ''
        submission.save()

        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=['post'], permission_classes=[IsSchoolAdmin])
    def reject(self, request, pk=None):
        submission = self.get_object()
        if submission.status != 'pending':
            return Response({'error': 'Only pending submissions can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

        submission.status = 'rejected'
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.rejection_reason = request.data.get('reason', '')
        submission.save()

        return Response(self.get_serializer(submission).data)
