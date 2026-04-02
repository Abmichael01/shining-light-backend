from rest_framework import viewsets, status, renderers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Q, Sum, Count
from api.models import FeeType, FeePayment, Student, SystemSetting, ResultPin
from api.serializers import (
    FeeTypeSerializer,
    FeePaymentSerializer,
    StudentFeeStatusSerializer,
    RecordFeePaymentSerializer
)
from api.permissions import IsSchoolAdmin, IsAdminOrStaff, IsAdminOrStaffOrStudent
from api.models import Class, Subject, Staff, Student
from api.pagination import StandardResultsSetPagination

class PDFRenderer(renderers.BaseRenderer):
    media_type = 'application/pdf'
    format = 'pdf'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data


class FeeTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FeeType model
    """
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer
    permission_classes = [IsSchoolAdmin]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = FeeType.objects.select_related(
            'school',
            'created_by'
        ).prefetch_related('applicable_classes')
        
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        is_mandatory = self.request.query_params.get('is_mandatory')
        if is_mandatory is not None:
            queryset = queryset.filter(is_mandatory=is_mandatory.lower() == 'true')
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def payment_summary(self, request, pk=None):
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
    permission_classes = [IsAdminOrStaffOrStudent]
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in ['initialize_payment', 'verify_payment', 'initialize_pin_purchase']:
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = FeePayment.objects.select_related(
            'student', 'student__biodata', 'fee_type', 
            'session', 'session_term', 'processed_by'
        )
        
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        
        if user_type == 'student' and hasattr(user, 'student_profile'):
            queryset = queryset.filter(student=user.student_profile)
        elif user_type == 'staff':
            staff = Staff.objects.filter(user=user).first()
            assigned_classes = Class.objects.filter(
                models.Q(class_staff=user) | models.Q(assigned_teachers__user=user)
            ).distinct()
            assigned_subjects = Subject.objects.none()
            if staff:
                assigned_subjects = Subject.objects.filter(assigned_teachers=staff)
            queryset = queryset.filter(
                models.Q(student__class_model__in=assigned_classes) |
                models.Q(student__subject_registrations__subject__in=assigned_subjects)
            ).distinct()
        
        query_params = getattr(self.request, 'query_params', self.request.GET)
        student_id = query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        fee_type_id = query_params.get('fee_type')
        if fee_type_id:
            queryset = queryset.filter(fee_type_id=fee_type_id)
        
        school_id = query_params.get('school')
        if school_id:
            queryset = queryset.filter(fee_type__school_id=school_id)
        
        session_id = query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        term_id = query_params.get('session_term')
        if term_id:
            queryset = queryset.filter(session_term_id=term_id)
            
        search = query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(student__biodata__surname__icontains=search) |
                models.Q(student__biodata__first_name__icontains=search) |
                models.Q(student__admission_number__icontains=search) |
                models.Q(reference_number__icontains=search)
            )
        
        return queryset.order_by('-payment_date', '-created_at')

    @action(detail=False, methods=['get'], url_path='clearance-status')
    def clearance_status(self, request):
        """Check if student has any unpaid penalty fees"""
        user = request.user
        if not hasattr(user, 'student_profile'):
            return Response({"is_cleared": True, "unpaid_penalties": []})
        
        student = user.student_profile
        
        # Penalties can be assigned to the student directly OR their class
        penalties = FeeType.objects.filter(
            is_penalty=True,
            is_active=True,
            school=student.school
        ).filter(
            Q(applicable_classes=student.class_model) | 
            Q(applicable_students=student)
        ).distinct()

        unpaid_penalties = []
        for p in penalties:
            status_context = p.get_payment_status_context(student)
            if status_context['status'] != 'paid':
                unpaid_penalties.append({
                    'id': p.id,
                    'name': p.name,
                    'reason': p.penalty_reason or p.description,
                    'amount': status_context['applicable_amount'],
                    'remaining': status_context['amount_remaining'],
                    'status': status_context['status']
                })
        
        return Response({
            "is_cleared": len(unpaid_penalties) == 0,
            "unpaid_penalties": unpaid_penalties
        })

    def perform_create(self, serializer):
        serializer.save(processed_by=self.request.user)
