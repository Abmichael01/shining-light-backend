from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from api.models import Assignment, AssignmentSubmission, StudentSubject
from api.serializers.assignment import (
    AssignmentSerializer, 
    AssignmentDetailSerializer, 
    AssignmentSubmissionSerializer
)
from api.permissions import IsAdminOrStaff, IsAdminOrStaffOrStudent
from django.utils import timezone
class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAdminOrStaffOrStudent]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subject', 'is_published', 'class_model']
    search_fields = ['title', 'description', 'subject__name', 'class_model__name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AssignmentDetailSerializer
        return AssignmentSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Assignment.objects.all()
        
        if getattr(user, 'user_type', None) == 'staff':
            # Staff can see assignments they created or assignments for subjects they teach
            queryset = queryset.filter(staff__user=user)
        elif getattr(user, 'user_type', None) == 'student':
            # Students see assignments for their class and subjects they are registered for
            student = getattr(user, 'student_profile', None)
            if student:
                # Get subjects the student is registered for in the current session
                registered_subjects = StudentSubject.objects.filter(
                    student=student,
                    is_active=True
                ).values_list('subject_id', flat=True)
                
                queryset = queryset.filter(
                    class_model=student.class_model,
                    subject_id__in=registered_subjects,
                    is_published=True
                )
            else:
                queryset = Assignment.objects.none()
        
        return queryset

    def perform_create(self, serializer):
        # Auto-assign staff if creating as a staff member
        if getattr(self.request.user, 'user_type', None) == 'staff':
            from api.models import Staff
            staff = Staff.objects.filter(user=self.request.user).first()
            if staff:
                serializer.save(staff=staff)
            else:
                serializer.save()
        else:
            serializer.save()

class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['assignment', 'status', 'student']
    search_fields = ['student__biodata__first_name', 'student__biodata__surname', 'student__admission_number']

    def get_queryset(self):
        user = self.request.user
        queryset = AssignmentSubmission.objects.all()
        
        if getattr(user, 'user_type', None) == 'student':
            queryset = queryset.filter(student__user=user)
        elif getattr(user, 'user_type', None) == 'staff':
            queryset = queryset.filter(assignment__staff__user=user)
            
        return queryset

    def perform_create(self, serializer):
        student = getattr(self.request.user, 'student_profile', None)
        if student:
            serializer.save(student=student, status='submitted', submitted_at=timezone.now())
        else:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def grade(self, request, pk=None):
        submission = self.get_object()
        marks = request.data.get('marks', {})
        feedback = request.data.get('feedback', '')
        
        # Update marks
        if not submission.marks:
            submission.marks = {}
            
        submission.marks.update(marks)
        
        # Update feedback if provided
        if feedback:
            submission.feedback = feedback
        
        # Recalculate score
        score, _ = submission.calculate_score()
        
        submission.score = score
        submission.status = 'graded'
        submission.save()
        
        return Response(self.get_serializer(submission).data)
