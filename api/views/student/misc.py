from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import models
from django.utils import timezone
from api.models import (
    Student, BioData, Guardian, Document, Biometric, 
    TermReport, Staff as StaffModelAlias, Class as ClassModelAlias,
    Subject as SubjectModelAlias
)
from api.serializers import (
    StudentSerializer,
    BioDataSerializer,
    GuardianSerializer,
    DocumentSerializer,
    BiometricSerializer,
    TermReportSerializer
)
from api.permissions import IsAdminOrStaff, IsAdminOrStaffOrStudent

class BioDataViewSet(viewsets.ModelViewSet):
    """ViewSet for BioData CRUD operations"""
    queryset = BioData.objects.all().order_by('-created_at')
    serializer_class = BioDataSerializer
    permission_classes = [IsAdminOrStaffOrStudent]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if getattr(user, 'user_type', None) == 'student':
            try:
                student = Student.objects.get(user=user)
                return queryset.filter(student=student)
            except Student.DoesNotExist:
                return queryset.none()
                
        student = self.request.query_params.get('student', None)
        if student:
            queryset = queryset.filter(student=student)
        return queryset

class GuardianViewSet(viewsets.ModelViewSet):
    """ViewSet for Guardian CRUD operations"""
    queryset = Guardian.objects.all().order_by('-is_primary_contact', 'guardian_type')
    serializer_class = GuardianSerializer
    permission_classes = [IsAdminOrStaffOrStudent]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if getattr(user, 'user_type', None) == 'student':
            try:
                student = Student.objects.get(user=user)
                return queryset.filter(student=student)
            except Student.DoesNotExist:
                return queryset.none()
                
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
        return queryset

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document CRUD operations"""
    queryset = Document.objects.all().order_by('-uploaded_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminOrStaffOrStudent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if getattr(user, 'user_type', None) == 'student':
            try:
                student = Student.objects.get(user=user)
                return queryset.filter(student=student)
            except Student.DoesNotExist:
                return queryset.none()
                
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
        return queryset
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        document = self.get_object()
        document.verified = True
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.save()
        return Response({
            'detail': 'Document verified successfully',
            'document': DocumentSerializer(document).data
        })

class BiometricViewSet(viewsets.ModelViewSet):
    """ViewSet for Biometric CRUD operations"""
    queryset = Biometric.objects.all().order_by('-captured_at')
    serializer_class = BiometricSerializer
    permission_classes = [IsAdminOrStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
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
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(captured_by=self.request.user)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def student_me(request):
    try:
        student = Student.objects.select_related(
            'user', 'school', 'class_model', 'department', 'club', 'biodata'
        ).prefetch_related(
            'guardians', 'documents', 'subject_registrations'
        ).filter(user=request.user).first()
        
        if not student:
            return Response({'error': 'Student profile not found for current user'}, status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'GET':
            serializer = StudentSerializer(student, context={'request': request})
            return Response(serializer.data)
        
        return Response({'error': 'Student profile updates are not yet supported'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TermReportViewSet(viewsets.ModelViewSet):
    queryset = TermReport.objects.all()
    serializer_class = TermReportSerializer
    permission_classes = [IsAdminOrStaffOrStudent]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student', None)
        session_id = self.request.query_params.get('session', None)
        session_term_id = self.request.query_params.get('session_term', None)
        
        user = self.request.user
        if getattr(user, 'user_type', None) == 'student':
            try:
                student = Student.objects.get(user=user)
                queryset = queryset.filter(student=student)
            except Student.DoesNotExist:
                return queryset.none()
        elif student_id:
            queryset = queryset.filter(student=student_id)
            
        if session_id:
            queryset = queryset.filter(session=session_id)
        if session_term_id:
            queryset = queryset.filter(session_term=session_term_id)
        return queryset
