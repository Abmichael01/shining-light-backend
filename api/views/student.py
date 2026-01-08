from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import Student, BioData, Guardian, Document, Biometric, StudentSubject, Session, SessionTerm, TermReport
from api.serializers import (
    StudentSerializer,
    StudentListSerializer,
    StudentRegistrationSerializer,
    BioDataSerializer,
    GuardianSerializer,
    DocumentSerializer,
    BiometricSerializer,
    StudentSubjectSerializer,
    TermReportSerializer
)
from api.permissions import IsSchoolAdmin, IsAdminOrStaff, IsAdminOrStaffOrStudent
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
    permission_classes = [IsAdminOrStaffOrStudent]
    
    def get_queryset(self):
        """Filter by student if provided. Students can only see their own biodata."""
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
        """Filter by student if provided. Students can only see their own guardians."""
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
        """Filter by student if provided. Students can only see their own documents."""
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
    permission_classes = [IsAdminOrStaffOrStudent]
    
    def get_queryset(self):
        """Filter by student, subject, or session"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students can only see their own subjects
        if getattr(user, 'user_type', None) == 'student':
            try:
                student = Student.objects.select_related('user').get(user=user)
                queryset = queryset.filter(student=student)
            except Student.DoesNotExist:
                return StudentSubject.objects.none()
        
        # Staff can see subjects for their assigned classes/subjects
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
        
        # Filter by query parameters
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
        
        # DEBUG: Print query parameters and results
        print(f"\n=== GET STUDENT SUBJECTS DEBUG ===")
        print(f"Query params - student: {student}, session: {session}, subject: {subject}, session_term: {session_term}")
        print(f"User: {self.request.user} (type: {getattr(self.request.user, 'user_type', 'N/A')})")
        count = queryset.count()
        print(f"Total results: {count}")
        if count > 0:
            print("Sample results:")
            for item in queryset[:5]:
                print(f"  - ID: {item.id}, Subject ID: {item.subject_id} (type: {type(item.subject_id)}), Subject Code: {item.subject.code if item.subject else 'N/A'}, Term: {item.session_term_id}")
        
        return queryset
    
    def perform_update(self, serializer):
        user = self.request.user
        if getattr(user, 'user_type', None) != 'admin':
            raise PermissionDenied('Only administrators can update results.')
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        # Allow admin or the student who owns the record
        is_admin = getattr(user, 'user_type', None) == 'admin'
        is_owner = getattr(user, 'user_type', None) == 'student' and instance.student.user == user
        
        if not (is_admin or is_owner):
            raise PermissionDenied('You do not have permission to remove this subject registration.')
            
        super().perform_destroy(instance)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='bulk_register')
    def bulk_register(self, request):
        """
        Bulk register multiple subjects for a student within a single session.
        Expects payload with: student (id), session (id), optional session_term, and subjects (list of ids/codes).
        - Admin: Can register for any student
        - Students: Can only register for themselves
        """
        student_id = request.data.get('student')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        subjects = request.data.get('subjects', [])
        
        user = request.user
        user_type = getattr(user, 'user_type', None)
        
        # If student, ensure they can only register for themselves
        if user_type == 'student':
            try:
                student = Student.objects.select_related('user').get(user=user)
                if str(student.id) != str(student_id):
                    return Response({
                        'detail': 'You can only register subjects for yourself.'
                    }, status=status.HTTP_403_FORBIDDEN)
            except Student.DoesNotExist:
                return Response({
                    'detail': 'Student profile not found for current user.'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Admin check for non-students
        elif user_type != 'admin':
            return Response({
                'detail': 'Only administrators and students can register subjects.'
            }, status=status.HTTP_403_FORBIDDEN)

        if not student_id or not session_id:
            return Response({
                'detail': 'student and session are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(subjects, (list, tuple)) or len(subjects) == 0:
            return Response({
                'detail': 'subjects must be a non-empty list.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Auto-get current term if not provided (before processing subjects)
        if not session_term_id:
            current_session = Session.objects.filter(is_current=True).first()
            if current_session:
                current_term = current_session.session_terms.filter(is_current=True).first()
                session_term_id = current_term.id if current_term else None
        
        # DEBUG: Print incoming parameters
        print(f"\n=== BULK REGISTER DEBUG ===")
        print(f"student_id: {student_id} (type: {type(student_id)})")
        print(f"session_id: {session_id} (type: {type(session_id)})")
        print(f"session_term_id: {session_term_id} (type: {type(session_term_id)})")
        print(f"subjects: {subjects} (type: {type(subjects)})")
        print(f"subjects list: {list(subjects)}")
        
        # DEBUG: Check existing registrations for this student/session/term
        existing_registrations = StudentSubject.objects.filter(
            student_id=student_id,
            session_id=session_id
        )
        if session_term_id:
            existing_registrations = existing_registrations.filter(session_term_id=session_term_id)
        
        print(f"\nExisting registrations for student {student_id}, session {session_id}, term {session_term_id}:")
        for reg in existing_registrations:
            print(f"  - Subject ID: {reg.subject_id} (type: {type(reg.subject_id)}), Subject Code: {reg.subject.code if reg.subject else 'N/A'}")
        print(f"Total existing: {existing_registrations.count()}")
        
        created_items = []
        errors = []
        
        with transaction.atomic():
            for subject in subjects:
                subject_id = subject
                print(f"\n--- Processing subject: {subject_id} (type: {type(subject_id)}) ---")
                try:
                    # Check if subject is already registered for this session AND term
                    # Registration is per term, so same subject can be registered for different terms
                    filter_query = {
                        'student_id': student_id,
                        'subject_id': subject_id,
                        'session_id': session_id
                    }
                    
                    # Always check for session_term if we have one (required for per-term registration)
                    if session_term_id:
                        filter_query['session_term_id'] = session_term_id
                    
                    print(f"Filter query: {filter_query}")
                    
                    # DEBUG: Check what the query returns
                    matching_registrations = StudentSubject.objects.filter(**filter_query)
                    print(f"Matching registrations count: {matching_registrations.count()}")
                    for match in matching_registrations:
                        print(f"  Match - Subject ID: {match.subject_id} (type: {type(match.subject_id)}), Term: {match.session_term_id}")
                    
                    exists = matching_registrations.exists()
                    print(f"Subject {subject_id} already exists: {exists}")
                    
                    if exists:
                        if session_term_id:
                            errors.append(f'Subject {subject_id} already registered for this session and term.')
                        else:
                            errors.append(f'Subject {subject_id} already registered for this session.')
                        continue
                    
                    # Get the subject and student objects for validation
                    from api.models import Subject
                    subject_obj = Subject.objects.get(id=subject_id)
                    student_obj = Student.objects.get(id=student_id)
                    
                    # Validate subject belongs to student's class and school
                    if subject_obj.class_model != student_obj.class_model:
                        errors.append(f'Subject {subject_obj.name} does not belong to your class ({student_obj.class_model.name}).')
                        continue
                    
                    if subject_obj.school != student_obj.school:
                        errors.append(f'Subject {subject_obj.name} does not belong to your school.')
                        continue
                    
                    registration = StudentSubject(
                        student_id=student_id,
                        subject_id=subject_id,
                        session_id=session_id,
                        session_term_id=session_term_id if session_term_id else None,
                        is_active=True
                    )
                    # Validate before saving
                    registration.full_clean()
                    registration.save()
                    created_items.append(registration)
                except Subject.DoesNotExist:
                    errors.append(f'Subject with ID {subject_id} not found.')
                except Student.DoesNotExist:
                    errors.append(f'Student with ID {student_id} not found.')
                except ValidationError as ve:
                    # Handle Django validation errors
                    error_msg = ve.message if hasattr(ve, 'message') else str(ve)
                    if hasattr(ve, 'error_dict'):
                        error_msg = ', '.join([f"{k}: {v[0]}" for k, v in ve.error_dict.items()])
                    errors.append(f'Validation error for subject {subject_id}: {error_msg}')
                except Exception as exc:
                    errors.append(f'Error registering subject {subject_id}: {str(exc)}')

        serializer = StudentSubjectSerializer(created_items, many=True, context={'request': request})
        
        # DEBUG: Print final results
        print(f"\n=== BULK REGISTER FINAL RESULTS ===")
        print(f"Registered: {len(created_items)} subjects")
        print(f"Errors: {len(errors)} errors")
        if errors:
            print(f"Error messages: {errors}")
        print(f"Status code: {status.HTTP_201_CREATED if created_items else status.HTTP_400_BAD_REQUEST}")
        print("=" * 40 + "\n")
        
        response_data = {
            'registered': len(created_items),
            'errors': errors,
            'data': serializer.data
        }
        
        status_code = status.HTTP_201_CREATED if created_items else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=status_code)

    @action(detail=True, methods=['post'], permission_classes=[IsSchoolAdmin])
    def mark_clear(self, request, pk=None):
        """Allow administrators to mark a subject registration as cleared/uncleared."""
        student_subject = self.get_object()
        cleared_value = request.data.get('cleared', True)
        cleared = str(cleared_value).lower() not in ['false', '0', 'no', 'none']

        if cleared:
            student_subject.cleared = True
            student_subject.cleared_by = request.user
            student_subject.cleared_at = timezone.now()
        else:
            student_subject.cleared = False
            student_subject.cleared_by = None
            student_subject.cleared_at = None

        student_subject.save(update_fields=[
            'cleared',
            'cleared_by',
            'cleared_at',
            'updated_at'
        ])

        serializer = self.get_serializer(student_subject)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsSchoolAdmin])
    def bulk_mark_clear(self, request):
        """Allow administrators to mark all subject registrations for a student as cleared/uncleared."""
        student_id = request.data.get('student')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        cleared_value = request.data.get('cleared', True)
        cleared = str(cleared_value).lower() not in ['false', '0', 'no', 'none']

        if not student_id or not session_id or not session_term_id:
            return Response({'error': 'Student, session and term are required'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(
            student_id=student_id,
            session_id=session_id,
            session_term_id=session_term_id
        )
        
        count = queryset.count()

        if cleared:
            queryset.update(
                cleared=True,
                cleared_by=request.user,
                cleared_at=timezone.now(),
                updated_at=timezone.now()
            )
        else:
            queryset.update(
                cleared=False,
                cleared_by=None,
                cleared_at=None,
                updated_at=timezone.now()
            )

        return Response({'message': f'Updated {count} subjects', 'count': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='open-day-clear', permission_classes=[IsAdminOrStaff])
    def open_day_clear(self, request, pk=None):
        """Mark or unmark a student's subject as cleared for Open Day."""
        student_subject = self.get_object()

        # Authorization: allow admins/superusers; staff must be assigned to the subject
        user = request.user
        is_admin_like = getattr(user, 'is_superuser', False) or getattr(user, 'user_type', '') == 'admin'
        if not is_admin_like:
            # Staff-specific checks
            staff_profile = getattr(user, 'staff_profile', None)
            if staff_profile is None:
                return Response({'detail': 'Only staff members can perform Open Day clearance.'}, status=status.HTTP_403_FORBIDDEN)

            subject = student_subject.subject
            # Conditions:
            # 1) Staff is explicitly assigned to the subject
            assigned_to_subject = subject.assigned_teachers.filter(pk=staff_profile.pk).exists()
            # 2) Staff is assigned to the class of the subject (via FK)
            assigned_class_match = bool(staff_profile.assigned_class_id) and (staff_profile.assigned_class_id == subject.class_model_id)
            # 3) Staff is listed among the class assigned teachers (M2M)
            in_class_assigned_teachers = subject.class_model.assigned_teachers.filter(pk=staff_profile.pk).exists()

            if not (assigned_to_subject or assigned_class_match or in_class_assigned_teachers):
                return Response({'detail': 'You are not permitted to clear this subject for Open Day.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}

        cleared_value = data.get('cleared', True)
        cleared = str(cleared_value).lower() not in ['false', '0', 'no', 'none']
        notes = data.get('notes', '') or ''
        checklist = data.get('checklist') or {}
        if not isinstance(checklist, dict):
            checklist = {}

        if cleared:
            student_subject.openday_cleared = True
            student_subject.openday_cleared_by = request.user
            student_subject.openday_cleared_at = timezone.now()
            student_subject.openday_clearance_notes = notes
            student_subject.openday_clearance_checklist = checklist
        else:
            student_subject.openday_cleared = False
            student_subject.openday_cleared_by = None
            student_subject.openday_cleared_at = None
            student_subject.openday_clearance_notes = ''
            student_subject.openday_clearance_checklist = {}

        student_subject.save(update_fields=[
            'openday_cleared',
            'openday_cleared_by',
            'openday_cleared_at',
            'openday_clearance_notes',
            'openday_clearance_checklist',
            'updated_at'
        ])

        serializer = self.get_serializer(student_subject)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsSchoolAdmin])
    def calculate_rankings(self, request):
        """
        Calculate subject positions for all students in a specific session and term.
        """
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        
        if not session_id or not session_term_id:
            return Response({'error': 'Session and term are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            # 1. Subject Positions
            # Get all subjects that have results in this term
            subjects = SubjectModelAlias.objects.filter(
                student_registrations__session_id=session_id,
                student_registrations__session_term_id=session_term_id
            ).distinct()
            
            for subject in subjects:
                # Get all registrations for this subject, session, term, ordered by total_score desc
                registrations = StudentSubject.objects.filter(
                    subject=subject,
                    session_id=session_id,
                    session_term_id=session_term_id,
                    total_score__isnull=False
                ).order_by('-total_score')
                
                # Calculate class statistics for this subject
                stats = registrations.aggregate(
                    max_score=models.Max('total_score'),
                    min_score=models.Min('total_score'),
                    avg_score=models.Avg('total_score')
                )
                
                # Assign positions (handling ties) and save statistics
                current_pos = 1
                last_score = None
                for i, reg in enumerate(registrations):
                    if last_score is not None and reg.total_score < last_score:
                        current_pos = i + 1
                    
                    reg.position = current_pos
                    reg.highest_score = stats['max_score']
                    reg.lowest_score = stats['min_score']
                    reg.subject_average = stats['avg_score']
                    reg.save(update_fields=['position', 'highest_score', 'lowest_score', 'subject_average'])
                    last_score = reg.total_score

            # 2. Overall Class Positions
            # Get all students who have registrations in this term
            student_ids = list(StudentSubject.objects.filter(
                session_id=session_id,
                session_term_id=session_term_id,
                total_score__isnull=False
            ).values_list('student_id', flat=True).distinct())
            
            student_averages = []
            for st_id in student_ids:
                regs = StudentSubject.objects.filter(
                    student_id=st_id,
                    session_id=session_id,
                    session_term_id=session_term_id,
                    total_score__isnull=False
                )
                avg = regs.aggregate(models.Avg('total_score'))['total_score__avg']
                total = regs.aggregate(models.Sum('total_score'))['total_score__sum']
                
                if avg is not None:
                    # Upsert TermReport
                    report, created = TermReport.objects.get_or_create(
                        student_id=st_id,
                        session_id=session_id,
                        session_term_id=session_term_id
                    )
                    report.average_score = avg
                    report.total_score = total
                    
                    # CUMULATIVE AVERAGE CALCULATION (3rd Term Logic)
                    # Check if this is the 3rd term (assuming term_order=3 or term_name contains "3rd" or "Third")
                    # Ideally SessionTerm should have an 'order' field or similar. 
                    # We'll check the SessionTerm object associated with the ID.
                    current_term = SessionTerm.objects.get(id=session_term_id)
                    is_third_term = '3rd' in current_term.term_name or 'Third' in current_term.term_name or current_term.term_order == 3
                    
                    if is_third_term:
                        # Fetch all reports for this student in this session
                        all_terms_reports = TermReport.objects.filter(
                            student_id=st_id,
                            session_id=session_id
                        ).exclude(id=report.id) # Exclude current one to avoid double counting if it was already saved
                        
                        # Sum up previous averages + current average
                        total_avg_sum = avg
                        term_count = 1
                        
                        for prev_report in all_terms_reports:
                            if prev_report.average_score:
                                total_avg_sum += prev_report.average_score
                                term_count += 1
                        
                        cumulative_avg = total_avg_sum / term_count
                        report.cumulative_average = cumulative_avg
                    else:
                        # Ensure cumulative_average is None for 1st and 2nd terms
                        report.cumulative_average = None
                    
                    # AUTOMATED REMARKS (Teacher & Principal)
                    # Based on the average_score, find the corresponding Grade and use its remarks
                    from api.models import Grade
                    grade_obj = Grade.get_grade_for_score(float(avg))
                    
                    if grade_obj:
                        # Only set if currently empty to allow for manual overrides
                        if not report.class_teacher_report and grade_obj.teacher_remark:
                            report.class_teacher_report = grade_obj.teacher_remark
                            
                        if not report.principal_report and grade_obj.principal_remark:
                            report.principal_report = grade_obj.principal_remark
                        
                    report.save()
                    student_averages.append({'id': report.id, 'avg': avg})
            
            # Rank students by average score
            # 2. Ranking Logic (Arm vs Set)
            # Fetch all generated reports
            all_reports = TermReport.objects.filter(
                session_id=session_id,
                session_term_id=session_term_id,
                average_score__isnull=False
            ).select_related('student__class_model')
            
            # --- A. Arm Ranking (Position in Class Arm) ---
            # Group reports by class_model (e.g. JSS 1A, JSS 1B)
            from collections import defaultdict
            reports_by_arm = defaultdict(list)
            for rep in all_reports:
                reports_by_arm[rep.student.class_model_id].append(rep)
            
            for arm_code, arm_reports in reports_by_arm.items():
                # Sort descending by average
                arm_reports.sort(key=lambda x: x.average_score, reverse=True)
                
                total_in_arm = len(arm_reports)
                current_pos = 1
                last_avg = None
                
                for i, rep in enumerate(arm_reports):
                    if last_avg is not None and rep.average_score < last_avg:
                        current_pos = i + 1
                    
                    # Update DB directly
                    TermReport.objects.filter(pk=rep.id).update(
                        class_position=current_pos,
                        total_students=total_in_arm
                    )
                    last_avg = rep.average_score

            # --- B. Set Ranking (Position in Grade Level) ---
            # Group reports by grade_level (e.g. JSS 1)
            # If grade_level is not set, we can fallback to grouping by None, or just skip
            reports_by_set = defaultdict(list)
            for rep in all_reports:
                g_level = rep.student.class_model.grade_level
                if g_level: # Only rank if categorized
                    reports_by_set[g_level].append(rep)
            
            for set_name, set_reports in reports_by_set.items():
                # Sort descending by average
                set_reports.sort(key=lambda x: x.average_score, reverse=True)
                
                total_in_set = len(set_reports)
                current_pos = 1
                last_avg = None
                
                for i, rep in enumerate(set_reports):
                    if last_avg is not None and rep.average_score < last_avg:
                        current_pos = i + 1
                    
                    # Update DB directly
                    TermReport.objects.filter(pk=rep.id).update(
                        grade_position=current_pos,
                        total_students_grade=total_in_set
                    )
                    last_avg = rep.average_score

        return Response({'message': 'Rankings calculated successfully'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def student_me(request):
    """
    Get the authenticated user's student profile (for student portal)
    """
    try:
        student = Student.objects.select_related(
            'user', 'school', 'class_model', 'department', 'club', 'biodata'
        ).prefetch_related(
            'guardians', 'documents', 'subject_registrations'
        ).filter(user=request.user).first()
        
        if not student:
            return Response({
                'error': 'Student profile not found for current user'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'GET':
            serializer = StudentSerializer(student, context={'request': request})
            return Response(serializer.data)
        
        # For PATCH, we'll allow limited updates (similar to staff portal)
        # For now, return read-only message - can be extended later
        return Response({
            'error': 'Student profile updates are not yet supported'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TermReportViewSet(viewsets.ModelViewSet):
    """ViewSet for TermReport CRUD operations"""
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

