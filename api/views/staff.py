"""
ViewSets for staff-related models
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Q, Sum
from api.models import (
    Staff,
    StaffEducation,
    SalaryGrade,
    StaffSalary,
    SalaryPayment,
    LoanApplication,
    LoanPayment
)
from api.serializers import (
    StaffSerializer,
    StaffListSerializer,
    StaffRegistrationSerializer,
    StaffEducationSerializer,
    SalaryGradeSerializer,
    StaffSalarySerializer,
    SalaryPaymentSerializer,
    LoanApplicationSerializer,
    LoanPaymentSerializer
)
from api.permissions import IsSchoolAdmin


class StaffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Staff model
    Supports CRUD operations and staff registration
    """
    queryset = Staff.objects.all()
    permission_classes = [IsSchoolAdmin]
    
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
        
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
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
        
        staff_id = self.request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
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
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by various parameters"""
        queryset = SalaryPayment.objects.select_related(
            'staff',
            'staff__user',
            'salary_grade',
            'processed_by'
        )
        
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


