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
from api.permissions import IsSchoolAdmin, IsAdminOrStaff, IsAdminOrStaffOrStudent
from api.models import Class, Subject, Staff, Student
from api.pagination import StandardResultsSetPagination


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
        # ... logic unchanged ...
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
    permission_classes = [IsAdminOrStaffOrStudent]
    pagination_class = StandardResultsSetPagination
    
    def get_permissions(self):
        """
        Allow specific permissions for custom actions
        """
        if self.action in ['initialize_payment', 'verify_payment']:
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()
    
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
        
        user = self.request.user
        user_type = getattr(user, 'user_type', None)
        
        # Student scoping: can only see own payments
        if user_type == 'student':
            if hasattr(user, 'student_profile'):
                queryset = queryset.filter(student=user.student_profile)
            else:
                return FeePayment.objects.none()
        
        # Staff scoping: restrict to students in assigned classes/subjects
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
        
        # ... logic continues ...
        
        # Filter by student (Admin/Staff only logic, for student it's already filtered)
        student_id = self.request.query_params.get('student')
        if student_id:
            # If student is checking, ensure they are querying themselves (redundant due to queryset filter but safer)
            if user_type == 'student' and hasattr(user, 'student_profile'):
                if str(student_id) != str(user.student_profile.id):
                     # If student tries to filter by another student ID, return empty or their own?
                     # Queryset filter already handles it, so this filter just refines inside their own data
                     pass 
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
        from api.utils.email import send_student_fee_receipt
        
        # Only admin/staff can record payments
        if getattr(request.user, 'user_type', None) == 'student':
             return Response(
                {'error': 'Students cannot record payments manually.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RecordFeePaymentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment = serializer.save()
            
            # Send receipt email
            send_student_fee_receipt(payment)
            
            return Response(
                FeePaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], renderer_classes=[])
    def download_receipt(self, request, pk=None):
        """
        Download payment receipt PDF
        """
        from api.utils.receipt_generator import generate_receipt_pdf
        from django.http import HttpResponse
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            payment = self.get_object()
            
            logger.info(f"Generating receipt for payment {payment.id}")
            pdf_file = generate_receipt_pdf(payment)
            
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
            return response
        except Exception as e:
            logger.error(f"Error generating receipt: {str(e)}", exc_info=True)
            return HttpResponse(
                f"Error generating receipt: {str(e)}", 
                status=500,
                content_type='text/plain'
            )
    
    @action(detail=False, methods=['get'])
    def student_fees(self, request):
        """
        Get fees applicable to the logged-in student for a specific session/term
        """
        user = request.user
        
        # 1. Start with Profile Check
        student_id = request.query_params.get('student')
        if student_id and (user.is_superuser or user.user_type in ['admin', 'staff']):
            try:
                student = Student.objects.get(pk=student_id)
            except (Student.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Student not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            student = getattr(user, 'student_profile', None)
            
        if not student:
            return Response(
                {'error': 'No student profile found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Determine Session and Term to View
        session_id = request.query_params.get('session_id')
        term_id = request.query_params.get('term_id')
        
        # Default to current if not provided
        if not session_id and student.current_session:
             session_id = student.current_session.id
        if not term_id and student.current_term:
             term_id = student.current_term.id
             
        # 3. Filter Fee Types
        # Rules: For School, Active, and Applicable Class
        fees_qs = FeeType.objects.filter(
            school=student.school,
            is_active=True
        ).filter(
            models.Q(applicable_classes__isnull=True) | 
            models.Q(applicable_classes=student.class_model)
        ).distinct()
        
        # Session/Term Filter: Active for Term OR Recurring
        if term_id:
            fees_qs = fees_qs.filter(
                models.Q(active_terms__id=term_id) |
                models.Q(is_recurring_per_term=True) |
                models.Q(active_terms__isnull=True)
            )
        
        fee_statuses = []
        for fee_type in fees_qs:
            # 4. Calculate Payment Status using UNIFIED LOGIC
            context = fee_type.get_payment_status_context(
                student=student,
                session=session_id,
                session_term=term_id
            )
            
            # Check Prerequisites (Using SAME Session/Term context)
            is_locked = False
            locked_message = ""
            
            prerequisites = fee_type.prerequisites.all()
            for prereq in prerequisites:
                # Check if prereq is paid FOR THIS SESSION/TERM 
                prereq_context = prereq.get_payment_status_context(
                    student=student,
                    session=session_id,
                    session_term=term_id
                )
                
                if prereq_context['status'] != 'paid':
                    is_locked = True
                    locked_message = f"Requires {prereq.name} to be paid first"
                    break
            
            # Get raw payment objects for API response details (optional, but good for history)
            # The context gave us totals, but front-end might want the list
            payment_filters = {
                'student': student,
                'fee_type': fee_type
            }
            if term_id and fee_type.is_recurring_per_term:
                 payment_filters['session_term_id'] = term_id
            elif session_id:
                 payment_filters['session_id'] = session_id

            payments = FeePayment.objects.filter(**payment_filters)
            
            fee_statuses.append({
                'fee_type_id': fee_type.id,
                'fee_type_name': fee_type.name,
                'fee_type_description': fee_type.description,
                'total_amount': context['applicable_amount'],
                'amount_paid': context['total_paid'],
                'amount_remaining': context['amount_remaining'],
                'installments_made': context['installments_made'],
                'installments_allowed': fee_type.max_installments,
                'is_staff_discount_applied': context['is_staff_child'],
                'status': context['status'],
                'is_mandatory': fee_type.is_mandatory,
                'is_recurring': fee_type.is_recurring_per_term,
                'payments': payments,
                'is_locked': is_locked,
                'locked_message': locked_message
            })
        
        serializer = StudentFeeStatusSerializer(fee_statuses, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['post'])
    def initialize_payment(self, request):
        """
        Initialize a Paystack transaction
        """
        from api.utils.paystack import Paystack
        import uuid
        
        user = request.user
        fee_type_id = request.data.get('fee_type_id')
        amount = request.data.get('amount')
        
        if not fee_type_id or not amount:
            return Response(
                {'error': 'Fee Type ID and Amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            fee_type = FeeType.objects.get(id=fee_type_id)
        except FeeType.DoesNotExist:
            return Response(
                {'error': 'Fee Type not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get student logic (reuse from student_fees)
        if getattr(user, 'user_type', None) == 'student':
            if hasattr(user, 'student_profile'):
                student = user.student_profile
        elif user.is_superuser or user.user_type in ['admin', 'staff']:
            # Admin/Staff initiating on behalf of student
            student_id = request.data.get('student_id')
            if student_id:
                try:
                    student = Student.objects.get(pk=student_id)
                except Student.DoesNotExist:
                    pass

        if not student:
             return Response(
                 {'error': 'Student profile required for payment initialization. If Admin, provide student_id.'},
                 status=status.HTTP_400_BAD_REQUEST
             )
             
        # Check Prerequisites (Security Check)
        prerequisites = fee_type.prerequisites.all()
        for prereq in prerequisites:
            prereq_paid = prereq.get_student_total_paid(student.id) # Should consider session if needed
            if prereq_paid < prereq.amount:
                 return Response(
                     {'error': f'Payment Locked: You must pay {prereq.name} first.'},
                     status=status.HTTP_403_FORBIDDEN
                 )
             
        # Generate Reference
        reference = f"TREF-{uuid.uuid4().hex[:12].upper()}"
        
        # Callback URL (Frontend URL)
        # Using port 3050 as specified
        callback_url = f"http://localhost:3050/portals/student/fees/callback" 
        
        pass_metadata = {
            'fee_type_id': fee_type.id,
            'student_id': student.id,
            'session_id': student.current_session.id if student.current_session else None,
            'term_id': student.current_term.id if student.current_term else None,
            'custom_fields': [
                {
                    'display_name': "Fee Type",
                    'variable_name': "fee_type",
                    'value': fee_type.name
                },
                {
                    'display_name': "Student",
                    'variable_name': "student",
                    'value': student.get_full_name()
                }
            ]
        }
        
        paystack = Paystack()
        email = user.email or f"student_{student.id}@school.com"
        
        response = paystack.initialize_transaction(
            email=email,
            amount=amount,
            reference=reference,
            callback_url=callback_url,
            metadata=pass_metadata
        )
        
        if response:
            return Response({
                'authorization_url': response['authorization_url'],
                'access_code': response['access_code'],
                'reference': reference
            })
        else:
            return Response(
                {'error': 'Failed to initialize payment with Paystack'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """
        Verify Paystack transaction and record payment
        """
        from api.utils.paystack import Paystack
        from django.db import transaction
        
        reference = request.data.get('reference')
        fee_type_id = request.data.get('fee_type_id')
        student_id = request.data.get('student_id') # Optional if we trust the user session context
        
        if not reference:
             return Response(
                {'error': 'Reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        paystack = Paystack()
        data = paystack.verify_transaction(reference)
        
        if data and data['status'] == 'success':
            # Payment Verified
            amount_paid = float(data['amount']) / 100 # Convert kobo to Naira
            
            # Check if payment already exists
            if FeePayment.objects.filter(reference_number=reference).exists():
                 return Response({
                    'status': 'success',
                    'message': 'Payment already verified',
                    'amount': amount_paid
                })
            
            try:
                with transaction.atomic():
                    # Get IDs from Metadata if not provided in request
                    metadata = data.get('metadata', {})
                    if not fee_type_id:
                        fee_type_id = metadata.get('fee_type_id')
                    
                    if not fee_type_id: 
                         return Response({'error': 'Fee Type ID required for verification'}, status=400)
                         
                    fee_type = FeeType.objects.get(id=fee_type_id)
                    
                    student = None
                    if hasattr(request.user, 'student_profile'):
                        student = request.user.student_profile
                    elif student_id:
                        student = Student.objects.get(id=student_id)
                    
                    if not student:
                        return Response({'error': 'Student not identified'}, status=400)

                    # Create Payment Record
                    payment = FeePayment.objects.create(
                        student=student,
                        fee_type=fee_type,
                        amount=amount_paid,
                        payment_method='online', # Paystack
                        payment_date=timezone.now().date(),
                        reference_number=reference,
                        notes=f"Paystack Ref: {reference}",
                        processed_by=request.user # The student themselves initiated it
                    )
                    
                    return Response({
                        'status': 'success',
                        'message': 'Payment verified and recorded',
                        'payment_id': payment.id,
                        'amount': amount_paid
                    })
            except Exception as e:
                print(f"Verification Error: {e}")
                return Response(
                    {'error': f'Payment verified but recording failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'error': 'Transaction verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
