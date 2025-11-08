"""
ViewSets for staff-related models
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db import models
from django.db.models import Q, Sum
from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from api.models import (
    Staff,
    StaffEducation,
    SalaryGrade,
    StaffSalary,
    SalaryPayment,
    LoanApplication,
    LoanPayment,
    Student,
    Class
)
from api.serializers import (
    StaffSerializer,
    StaffListSerializer,
    StaffRegistrationSerializer,
    StaffPortalUpdateSerializer,
    StaffEducationSerializer,
    SalaryGradeSerializer,
    StaffSalarySerializer,
    SalaryPaymentSerializer,
    LoanApplicationSerializer,
    LoanPaymentSerializer,
    StudentListSerializer,
    StudentSerializer
)
from api.permissions import IsSchoolAdmin, IsAdminOrStaff
from api.utils.email import generate_password, send_staff_registration_email


class StaffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Staff model
    Supports CRUD operations and staff registration
    """
    queryset = Staff.objects.all()
    permission_classes = [IsSchoolAdmin]
    lookup_field = 'staff_id'
    lookup_value_regex = '[^/\s]+'

    def get_object(self):
        """Allow lookups by staff_id (default) or numeric primary key for backwards compatibility."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(self.lookup_field) or self.kwargs.get(lookup_url_kwarg)

        print(f"[StaffViewSet.get_object] lookup_value raw: {lookup_value}")

        if lookup_value is None:
            print("[StaffViewSet.get_object] No lookup value provided; raising 404")
            raise Http404

        # Try staff_id lookup first
        obj = queryset.filter(staff_id=lookup_value).first()
        print(f"[StaffViewSet.get_object] Staff lookup by staff_id found: {bool(obj)}")

        # Fallback to numeric primary key when applicable
        if obj is None and lookup_value.isdigit():
            print(f"[StaffViewSet.get_object] Falling back to numeric PK lookup for value: {lookup_value}")
            obj = queryset.filter(pk=lookup_value).first()
            print(f"[StaffViewSet.get_object] Staff lookup by pk found: {bool(obj)}")

        if obj is None:
            print("[StaffViewSet.get_object] No staff record found; raising 404")
            raise Http404

        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        print(f"StaffViewSet.get_serializer_class called for action: {self.action}")
        if self.action == 'list':
            print("Using StaffListSerializer")
            return StaffListSerializer
        elif self.action == 'register':
            print("Using StaffRegistrationSerializer")
            return StaffRegistrationSerializer
        print("Using StaffSerializer")
        return StaffSerializer
    
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        print(f"StaffViewSet.get_queryset called with params: {self.request.query_params}")
        
        queryset = Staff.objects.select_related(
            'user',
            'assigned_class',
            'created_by'
        ).prefetch_related('education_records')
        
        print(f"Initial queryset count: {queryset.count()}")
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            print(f"After status filter ({status_param}): {queryset.count()}")
        
        # Filter by staff type
        staff_type = self.request.query_params.get('staff_type')
        if staff_type:
            queryset = queryset.filter(staff_type=staff_type)
            print(f"After staff_type filter ({staff_type}): {queryset.count()}")
        
        # Filter by zone
        zone = self.request.query_params.get('zone')
        if zone:
            queryset = queryset.filter(zone=zone)
            print(f"After zone filter ({zone}): {queryset.count()}")
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(staff_id__icontains=search) |
                Q(surname__icontains=search) |
                Q(first_name__icontains=search) |
                Q(other_names__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(user__email__icontains=search)
            )
            print(f"After search filter ({search}): {queryset.count()}")
        
        final_queryset = queryset.order_by('-entry_date')
        print(f"Final queryset count: {final_queryset.count()}")
        return final_queryset
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new staff member with user account
        """
        print(f"StaffViewSet.register called with data keys: {list(request.data.keys())}")
        
        # Print data without base64 fields
        filtered_data = {}
        for key, value in request.data.items():
            if key in ['passport_photo'] or (isinstance(value, str) and value.startswith('data:')):
                filtered_data[key] = f"[BASE64_DATA_{len(str(value))}_chars]"
            elif key == 'education_records' and isinstance(value, list):
                filtered_records = []
                for record in value:
                    filtered_record = {}
                    for k, v in record.items():
                        if k == 'certificate' and isinstance(v, str) and v.startswith('data:'):
                            filtered_record[k] = f"[BASE64_DATA_{len(str(v))}_chars]"
                        else:
                            filtered_record[k] = v
                    filtered_records.append(filtered_record)
                filtered_data[key] = filtered_records
            else:
                filtered_data[key] = value
        print(f"Request data (filtered): {filtered_data}")
        
        serializer = StaffRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            print("Serializer is valid, creating staff member")
            staff = serializer.save()
            print(f"Staff member created with ID: {staff.id}")
            return Response(
                StaffSerializer(staff).data,
                status=status.HTTP_201_CREATED
            )
        print(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def send_credentials(self, request, *args, **kwargs):
        """
        Reset a staff member's password and email updated credentials.
        """
        staff = self.get_object()

        if not staff.user or not staff.user.email:
            return Response(
                {'detail': 'Staff does not have an associated email account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_password = generate_password()
            staff.user.set_password(new_password)
            staff.user.save(update_fields=['password'])

            email_sent = send_staff_registration_email(staff, new_password, request)

            if email_sent:
                return Response({
                    'detail': 'Credentials sent successfully.',
                    'email': staff.user.email,
                })

            return Response(
                {'detail': 'Password updated, but email delivery failed.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as exc:
            return Response(
                {'detail': f'Error sending credentials: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """
        Update staff status (active, on_leave, suspended, terminated, retired)
        """
        staff = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in dict(Staff.STATUS_CHOICES).keys():
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        staff.status = new_status
        staff.save()
        
        return Response(StaffSerializer(staff).data)
    
    @action(detail=True, methods=['get'])
    def salary_history(self, request, pk=None):
        """
        Get salary payment history for a staff member
        """
        staff = self.get_object()
        payments = SalaryPayment.objects.filter(staff=staff).order_by('-year', '-month')
        serializer = SalaryPaymentSerializer(payments, many=True)
        return Response(serializer.data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def staff_me(request):
    """
    Get the authenticated user's staff profile (for staff portal)
    """
    try:
        staff = Staff.objects.select_related('user', 'assigned_class').prefetch_related('education_records').filter(user=request.user).first()
        if not staff:
            return Response({
                'error': 'Staff profile not found for current user'
            }, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'GET':
            serializer = StaffSerializer(staff, context={'request': request})
            return Response(serializer.data)

        update_serializer = StaffPortalUpdateSerializer(staff, data=request.data, partial=True, context={'request': request})
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()
        return Response(StaffSerializer(staff, context={'request': request}).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_students(request):
    """
    List students visible to the authenticated staff member:
    - Students whose class_model.class_staff = current user
    Optional query params: search, status
    """
    try:
        from api.models import Staff as StaffModel, Subject as SubjectModel, StudentSubject as StudentSubjectModel
        assigned_classes = Class.objects.filter(models.Q(class_staff=request.user) | models.Q(assigned_teachers__user=request.user)).distinct()
        staff = StaffModel.objects.filter(user=request.user).first()
        assigned_subjects = SubjectModel.objects.filter(assigned_teachers=staff) if staff else SubjectModel.objects.none()
        queryset = Student.objects.select_related('user', 'class_model', 'school', 'biodata').filter(
            models.Q(class_model__in=assigned_classes) |
            models.Q(subject_registrations__subject__in=assigned_subjects)
        ).distinct()

        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(admission_number__icontains=search) |
                models.Q(application_number__icontains=search) |
                models.Q(user__email__icontains=search) |
                models.Q(biodata__surname__icontains=search) |
                models.Q(biodata__first_name__icontains=search) |
                models.Q(biodata__other_names__icontains=search)
            )

        queryset = queryset.order_by('class_model__order', 'class_model__name', 'admission_number')
        serializer = StudentListSerializer(queryset, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def staff_student_detail_update(request, student_id):
    """
    Get or update a student if the authenticated staff is assigned to the student's class.
    GET: returns student detail
    PATCH: allows partial update of student (limited to safe fields)
    """
    try:
        # Assignment check
        from api.models import Staff as StaffModel, Subject as SubjectModel
        assigned_classes = Class.objects.filter(models.Q(class_staff=request.user) | models.Q(assigned_teachers__user=request.user)).distinct()
        staff = StaffModel.objects.filter(user=request.user).first()
        assigned_subjects = SubjectModel.objects.filter(assigned_teachers=staff) if staff else SubjectModel.objects.none()
        student = Student.objects.select_related('class_model', 'school', 'user').filter(
            id=student_id
        ).filter(
            models.Q(class_model__in=assigned_classes) |
            models.Q(subject_registrations__subject__in=assigned_subjects)
        ).distinct().first()
        if not student:
            return Response({'error': 'Not permitted to access this student'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'GET':
            serializer = StudentSerializer(student, context={'request': request})
            return Response(serializer.data)

        if request.method == 'PATCH':
            # Allow full update with StudentSerializer when staff is assigned
            serializer = StudentSerializer(student, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if request.method == 'DELETE':
            student.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def loan_history(self, request, pk=None):
        """
        Get loan application history for a staff member
        """
        staff = self.get_object()
        loans = LoanApplication.objects.filter(staff=staff).order_by('-application_date')
        serializer = LoanApplicationSerializer(loans, many=True)
        return Response(serializer.data)


class StaffEducationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StaffEducation model
    """
    queryset = StaffEducation.objects.all()
    serializer_class = StaffEducationSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by staff if provided"""
        queryset = StaffEducation.objects.select_related('staff')
        
        staff_param = self.request.query_params.get('staff')
        if staff_param:
            if staff_param.isdigit():
                queryset = queryset.filter(staff_id=staff_param)
            else:
                queryset = queryset.filter(staff__staff_id=staff_param)
        
        return queryset


class SalaryGradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SalaryGrade model
    """
    queryset = SalaryGrade.objects.all()
    serializer_class = SalaryGradeSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter salary grades"""
        queryset = SalaryGrade.objects.select_related('created_by')
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(grade_number__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('grade_number')
    
    def perform_create(self, serializer):
        """Set created_by when creating salary grade"""
        serializer.save(created_by=self.request.user)


class StaffSalaryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StaffSalary model
    """
    queryset = StaffSalary.objects.all()
    serializer_class = StaffSalarySerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by staff or school"""
        queryset = StaffSalary.objects.select_related(
            'staff',
            'staff__user',
            'staff__school',
            'salary_grade',
            'assigned_by'
        )
        
        staff_param = self.request.query_params.get('staff')
        if staff_param:
            if staff_param.isdigit():
                queryset = queryset.filter(staff_id=staff_param)
            else:
                queryset = queryset.filter(staff__staff_id=staff_param)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set assigned_by when assigning salary"""
        serializer.save(assigned_by=self.request.user)


class SalaryPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SalaryPayment model
    """
    queryset = SalaryPayment.objects.all()
    serializer_class = SalaryPaymentSerializer
    permission_classes = [IsAdminOrStaff]
    
    def get_queryset(self):
        """Filter by various parameters"""
        queryset = SalaryPayment.objects.select_related(
            'staff',
            'staff__user',
            'salary_grade',
            'processed_by'
        )
        # If user is staff, restrict to their own payments only
        user = self.request.user
        if getattr(user, 'user_type', None) == 'staff':
            queryset = queryset.filter(staff__user=user)
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by school
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(staff__school_id=school_id)
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by year
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        # Filter by month
        month = self.request.query_params.get('month')
        if month:
            queryset = queryset.filter(month=month)
        
        # Search (by staff name, staff ID, or reference number)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(staff__staff_id__icontains=search) |
                Q(staff__surname__icontains=search) |
                Q(staff__first_name__icontains=search) |
                Q(reference_number__icontains=search)
            )
        
        return queryset.order_by('-year', '-month', 'staff__surname')
    
    def perform_create(self, serializer):
        """Set processed_by when creating payment"""
        serializer.save(processed_by=self.request.user)
    
    @action(detail=True, methods=['patch'])
    def mark_paid(self, request, pk=None):
        """
        Mark a salary payment as paid
        """
        payment = self.get_object()
        payment_date = request.data.get('payment_date')
        reference_number = request.data.get('reference_number')
        
        payment.status = 'paid'
        if payment_date:
            payment.payment_date = payment_date
        if reference_number:
            payment.reference_number = reference_number
        payment.processed_by = request.user
        payment.save()
        
        return Response(SalaryPaymentSerializer(payment).data)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create salary payments for multiple staff at once
        Expects: month, year, and optionally staff_ids (if not provided, creates for all active staff)
        """
        month = request.data.get('month')
        year = request.data.get('year')
        school_id = request.data.get('school')
        staff_ids = request.data.get('staff_ids', [])
        
        if not month or not year:
            return Response(
                {'error': 'Month and year are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get staff to create payments for
        staff_members = Staff.objects.filter(status='active')
        if school_id:
            staff_members = staff_members.filter(school_id=school_id)
        if staff_ids:
            staff_members = staff_members.filter(id__in=staff_ids)
        
        # Check if they have assigned salary
        staff_members = staff_members.filter(current_salary__isnull=False).select_related('current_salary__salary_grade')
        
        created_payments = []
        errors = []
        
        for staff in staff_members:
            # Check if payment already exists
            if SalaryPayment.objects.filter(staff=staff, month=month, year=year).exists():
                errors.append(f"Payment for {staff.get_full_name()} already exists for {month}/{year}")
                continue
            
            try:
                payment = SalaryPayment.objects.create(
                    staff=staff,
                    salary_grade=staff.current_salary.salary_grade,
                    month=month,
                    year=year,
                    amount=staff.current_salary.salary_grade.monthly_amount,
                    deductions=0,
                    status='pending',
                    processed_by=request.user
                )
                created_payments.append(payment)
            except Exception as e:
                errors.append(f"Error creating payment for {staff.get_full_name()}: {str(e)}")
        
        return Response({
            'created': len(created_payments),
            'payments': SalaryPaymentSerializer(created_payments, many=True).data,
            'errors': errors
        })


class LoanApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LoanApplication model
    """
    queryset = LoanApplication.objects.all()
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by various parameters"""
        queryset = LoanApplication.objects.select_related(
            'staff',
            'staff__user',
            'staff__assigned_class',
            'staff__assigned_class__school',
            'reviewed_by'
        ).prefetch_related('loan_payments')
        
        # Filter by staff
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by school (via assigned_class)
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(staff__assigned_class__school_id=school_id)
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Search (by staff name, staff ID, or application number)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(application_number__icontains=search) |
                Q(staff__staff_id__icontains=search) |
                Q(staff__surname__icontains=search) |
                Q(staff__first_name__icontains=search)
            )
        
        return queryset.order_by('-application_date')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a loan application
        """
        loan = self.get_object()
        
        if loan.status != 'pending':
            return Response(
                {'error': 'Only pending loans can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        loan.status = 'approved'
        loan.reviewed_by = request.user
        loan.review_notes = request.data.get('review_notes', '')
        from django.utils import timezone
        loan.approval_date = timezone.now().date()
        loan.save()
        
        return Response(LoanApplicationSerializer(loan).data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a loan application
        """
        loan = self.get_object()
        
        if loan.status != 'pending':
            return Response(
                {'error': 'Only pending loans can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        loan.status = 'rejected'
        loan.reviewed_by = request.user
        loan.rejection_reason = rejection_reason
        loan.review_notes = request.data.get('review_notes', '')
        loan.save()
        
        return Response(LoanApplicationSerializer(loan).data)
    
    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """
        Mark loan as disbursed
        """
        loan = self.get_object()
        
        if loan.status != 'approved':
            return Response(
                {'error': 'Only approved loans can be disbursed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        loan.status = 'disbursed'
        from django.utils import timezone
        loan.disbursement_date = timezone.now().date()
        loan.save()
        
        return Response(LoanApplicationSerializer(loan).data)


class LoanPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LoanPayment model
    """
    queryset = LoanPayment.objects.all()
    serializer_class = LoanPaymentSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by loan application"""
        queryset = LoanPayment.objects.select_related(
            'loan_application',
            'loan_application__staff',
            'processed_by'
        )
        
        loan_id = self.request.query_params.get('loan_application')
        if loan_id:
            queryset = queryset.filter(loan_application_id=loan_id)
        
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(loan_application__staff_id=staff_id)
        
        return queryset.order_by('-payment_date')
    
    def perform_create(self, serializer):
        """Set processed_by and check if loan is completed"""
        payment = serializer.save(processed_by=self.request.user)
        
        # Check if loan is fully paid
        loan = payment.loan_application
        if loan.get_amount_remaining() <= 0:
            loan.status = 'completed'
            loan.save()


