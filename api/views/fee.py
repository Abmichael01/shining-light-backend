"""
ViewSets for fee-related models
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Q, Sum, Count
from api.models import FeeType, FeePayment, Student
from api.serializers import (
    FeeTypeSerializer,
    FeePaymentSerializer,
    StudentFeeStatusSerializer,
    RecordFeePaymentSerializer
)
from api.permissions import IsSchoolAdmin


class FeeTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FeeType model
    """
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = FeeType.objects.select_related(
            'school',
            'created_by'
        ).prefetch_related('applicable_classes')
        
        # Filter by school
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by mandatory
        is_mandatory = self.request.query_params.get('is_mandatory')
        if is_mandatory is not None:
            queryset = queryset.filter(is_mandatory=is_mandatory.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by when creating fee type"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def payment_summary(self, request, pk=None):
        """
        Get payment summary for a fee type
        """
        fee_type = self.get_object()
        
        payments = FeePayment.objects.filter(fee_type=fee_type)
        
        summary = {
            'total_payments': payments.count(),
            'total_collected': payments.aggregate(total=Sum('amount'))['total'] or 0,
            'unique_students': payments.values('student').distinct().count(),
        }
        
        return Response(summary)


class FeePaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FeePayment model
    """
    queryset = FeePayment.objects.all()
    serializer_class = FeePaymentSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = FeePayment.objects.select_related(
            'student',
            'student__biodata',
            'fee_type',
            'session',
            'session_term',
            'processed_by'
        )
        
        # Filter by student
        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Filter by fee type
        fee_type_id = self.request.query_params.get('fee_type')
        if fee_type_id:
            queryset = queryset.filter(fee_type_id=fee_type_id)
        
        # Filter by school
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(fee_type__school_id=school_id)
        
        # Filter by session
        session_id = self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        # Filter by session term
        session_term_id = self.request.query_params.get('session_term')
        if session_term_id:
            queryset = queryset.filter(session_term_id=session_term_id)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)
        
        # Search (by student name, admission number, or reference number)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(student__biodata__surname__icontains=search) |
                models.Q(student__biodata__first_name__icontains=search) |
                models.Q(student__admission_number__icontains=search) |
                models.Q(reference_number__icontains=search)
            )
        
        return queryset.order_by('-payment_date', '-created_at')
    
    def perform_create(self, serializer):
        """Set processed_by when creating payment"""
        serializer.save(processed_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def record_payment(self, request):
        """
        Record a new fee payment with validation
        """
        serializer = RecordFeePaymentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment = serializer.save()
            return Response(
                FeePaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def student_fees(self, request):
        """
        Get all applicable fees and payment status for a student
        """
        student_id = request.query_params.get('student')
        if not student_id:
            return Response(
                {'error': 'Student ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get current session and term
        session = request.query_params.get('session')
        session_term = request.query_params.get('session_term')
        
        # Get all applicable fee types for this student
        fee_types = FeeType.objects.filter(
            school=student.school,
            is_active=True
        ).filter(
            Q(applicable_classes__isnull=True) |  # No classes = all classes
            Q(applicable_classes=student.class_model)  # Or student's class
        ).distinct()
        
        # Build status for each fee
        fee_statuses = []
        for fee_type in fee_types:
            # Get payments
            payment_filters = {
                'student': student,
                'fee_type': fee_type,
            }
            
            if fee_type.is_recurring_per_term and session_term:
                payment_filters['session_term_id'] = session_term
            elif session:
                payment_filters['session_id'] = session
            
            payments = FeePayment.objects.filter(**payment_filters)
            total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
            installments_made = payments.count()
            
            # Calculate status
            if total_paid >= fee_type.amount:
                fee_status = 'paid'
            elif total_paid > 0:
                fee_status = 'partial'
            else:
                fee_status = 'unpaid'
            
            fee_statuses.append({
                'fee_type_id': fee_type.id,
                'fee_type_name': fee_type.name,
                'fee_type_description': fee_type.description,
                'total_amount': fee_type.amount,
                'amount_paid': total_paid,
                'amount_remaining': max(0, fee_type.amount - total_paid),
                'installments_made': installments_made,
                'installments_allowed': fee_type.max_installments,
                'status': fee_status,
                'is_mandatory': fee_type.is_mandatory,
                'is_recurring': fee_type.is_recurring_per_term,
                'payments': FeePaymentSerializer(payments, many=True).data,
            })
        
        serializer = StudentFeeStatusSerializer(fee_statuses, many=True)
        return Response(serializer.data)


