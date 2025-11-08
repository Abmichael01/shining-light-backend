from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.utils import timezone

from api.models import Student, BioData, Guardian, Document, Biometric, StudentSubject
from api.serializers import (
    StudentSerializer,
    StudentListSerializer,
    StudentRegistrationSerializer,
    BioDataSerializer,
    GuardianSerializer,
    DocumentSerializer,
    BiometricSerializer,
    StudentSubjectSerializer
)
from api.permissions import IsSchoolAdmin, IsAdminOrStaff
from api.models import Class as ClassModelAlias, Subject as SubjectModelAlias, Staff as StaffModelAlias


class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Student CRUD operations
    Handles both applications and enrolled students
    """
    queryset = Student.objects.select_related(
        'school', 'class_model', 'department', 'club', 'user', 'biodata'
    ).prefetch_related(
        'guardians', 'documents', 'subject_registrations'
    ).all().order_by('-created_at')
    permission_classes = [IsSchoolAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return StudentListSerializer
        elif self.action == 'register':
            return StudentRegistrationSerializer
        return StudentSerializer
    
    def get_queryset(self):
        """Filter students by various parameters"""
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by school
        school = self.request.query_params.get('school', None)
        if school:
            queryset = queryset.filter(school=school)
        
        # Filter by class
        class_model = self.request.query_params.get('class', None)
        if class_model:
            queryset = queryset.filter(class_model=class_model)
        
        # Filter by source
        source = self.request.query_params.get('source', None)
        if source:
            queryset = queryset.filter(source=source)
        
        # Search by name, admission number, or email
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(biodata__surname__icontains=search) |
                models.Q(biodata__first_name__icontains=search) |
                models.Q(biodata__other_names__icontains=search) |
                models.Q(admission_number__icontains=search) |
                models.Q(application_number__icontains=search) |
                models.Q(user__email__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new student (admin creates student directly)
        This creates Student, BioData, Guardians in one transaction
        """
        serializer = StudentRegistrationSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        
        # Return full student data
        response_serializer = StudentSerializer(student)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve an application and convert to enrolled student
        Creates user account and updates status
        """
        student = self.get_object()
        
        if student.status not in ['applicant', 'under_review']:
            return Response(
                {'detail': 'Only applicants can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                from api.models import User
                from datetime import date
                
                # Create user account if not exists
                if not student.user:
                    # Generate username from biodata
                    biodata = student.biodata
                    username = f"{biodata.first_name.lower()}.{biodata.surname.lower()}@school.com"
                    
                    # Create user
                    user = User.objects.create_user(
                        email=username,
                        password=request.data.get('password', 'temp123'),
                        user_type='student'
                    )
                    student.user = user
                
                # Update status and dates
                student.status = 'enrolled'
                student.acceptance_date = date.today()
                student.enrollment_date = date.today()
                student.reviewed_by = request.user
                student.review_date = date.today()
                student.save()
                
                return Response({
                    'detail': 'Application approved successfully',
                    'student': StudentSerializer(student).data
                })
                
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an application"""
        student = self.get_object()
        
        if student.status not in ['applicant', 'under_review']:
            return Response(
                {'detail': 'Only applicants can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        
        from datetime import date
        student.status = 'rejected'
        student.rejection_reason = rejection_reason
        student.reviewed_by = request.user
        student.review_date = date.today()
        student.save()
        
        return Response({'detail': 'Application rejected'})
    
    @action(detail=True, methods=['post'])
    def send_credentials(self, request, pk=None):
        """
        Send student login credentials via email
        Generates a new password and sends it to the student's email
        """
        student = self.get_object()
        
        if not student.user:
            return Response(
                {'detail': 'Student does not have a user account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from api.utils.email import generate_password, send_student_registration_email
            from django.contrib.auth.hashers import make_password
            
            # Generate new password
            new_password = generate_password()
            
            # Update user password
            student.user.set_password(new_password)
            student.user.save()
            
            # Send email with credentials
            email_sent = send_student_registration_email(student, new_password, request)
            
            if email_sent:
                return Response({
                    'detail': 'Credentials sent successfully',
                    'email': student.user.email
                })
            else:
                return Response(
                    {'detail': 'Failed to send email, but password was updated'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'detail': f'Error sending credentials: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BioDataViewSet(viewsets.ModelViewSet):
    """ViewSet for BioData CRUD operations"""
    queryset = BioData.objects.all().order_by('-created_at')
    serializer_class = BioDataSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by student if provided"""
        queryset = super().get_queryset()
        student = self.request.query_params.get('student', None)
        if student:
            queryset = queryset.filter(student=student)
        return queryset


class GuardianViewSet(viewsets.ModelViewSet):
    """ViewSet for Guardian CRUD operations"""
    queryset = Guardian.objects.all().order_by('-is_primary_contact', 'guardian_type')
    serializer_class = GuardianSerializer
    permission_classes = [IsAdminOrStaff]
    
    def get_queryset(self):
        """Filter by student if provided"""
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


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document CRUD operations"""
    queryset = Document.objects.all().order_by('-uploaded_at')
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminOrStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """Filter by student if provided"""
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
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a document"""
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
        """Filter by student if provided"""
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
        """Set captured_by when creating biometric"""
        serializer.save(captured_by=self.request.user)


class StudentSubjectViewSet(viewsets.ModelViewSet):
    """ViewSet for StudentSubject CRUD operations"""
    queryset = StudentSubject.objects.select_related(
        'student', 'subject', 'session', 'session_term', 'grade'
    ).all().order_by('-registered_at')
    serializer_class = StudentSubjectSerializer
    permission_classes = [IsAdminOrStaff]
    
    def get_queryset(self):
        """Filter by student, subject, or session"""
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
        
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(subject=subject)
        
        session = self.request.query_params.get('session', None)
        if session:
            queryset = queryset.filter(session=session)
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def clear(self, request, pk=None):
        """
        Mark or unmark a student's subject as cleared by staff/admin.
        """
        student_subject = self.get_object()
        cleared_value = request.data.get('cleared', True)
        cleared = str(cleared_value).lower() not in ['false', '0', 'no']

        if cleared:
            student_subject.cleared = True
            student_subject.cleared_by = request.user
            student_subject.cleared_at = timezone.now()
        else:
            student_subject.cleared = False
            student_subject.cleared_by = None
            student_subject.cleared_at = None

        student_subject.save(update_fields=['cleared', 'cleared_by', 'cleared_at', 'updated_at'])
        serializer = self.get_serializer(student_subject)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def bulk_register(self, request):
        """
        Register a student for multiple subjects at once
        Expects: { student: id, session: id, session_term: id (optional), subjects: [id1, id2, ...] }
        """
        student_id = request.data.get('student')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        subject_ids = request.data.get('subjects', [])
        
        if not all([student_id, session_id, subject_ids]):
            return Response(
                {'detail': 'student, session, and subjects are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_registrations = []
        errors = []
        
        with transaction.atomic():
            for subject_id in subject_ids:
                try:
                    # Check if already registered
                    existing = StudentSubject.objects.filter(
                        student_id=student_id,
                        subject_id=subject_id,
                        session_id=session_id
                    ).first()
                    
                    if existing:
                        errors.append(f"Already registered for {existing.subject.name}")
                        continue
                    
                    # Create registration
                    registration = StudentSubject.objects.create(
                        student_id=student_id,
                        subject_id=subject_id,
                        session_id=session_id,
                        session_term_id=session_term_id if session_term_id else None,
                        is_active=True
                    )
                    created_registrations.append(registration)
                except Exception as e:
                    errors.append(str(e))
        
        # Return created registrations
        serializer = StudentSubjectSerializer(created_registrations, many=True, context={'request': request})
        
        response_data = {
            'registered': len(created_registrations),
            'errors': errors,
            'data': serializer.data
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED if created_registrations else status.HTTP_400_BAD_REQUEST)


