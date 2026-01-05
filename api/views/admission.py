"""
Admission API Views
Handles admission portal endpoints for applicant registration and application management
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import (
    Student, BioData, Guardian, Document, AdmissionSettings,
    School, Class, PaymentPurpose, ApplicationSlip
)
from api.models.user import User
from api.serializers.admission import (
    AdmissionSettingsSerializer,
    EmailOtpRequestSerializer,
    OtpRegistrationSerializer,
    ApplicantRegistrationSerializer,
    ApplicantLoginSerializer,
    ApplicantChangePasswordSerializer,
    ApplicantDashboardSerializer,
    ApplicationSubmissionSerializer,
    ApplicationSlipSerializer,
    PaymentPurposeSerializer,
    PaymentStatusSerializer
)
from api.serializers.student import BioDataSerializer, GuardianSerializer, DocumentSerializer
from api.services.admission_service import AdmissionService
from api.permissions import IsApplicant


class AdmissionSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing admission settings
    Admin only
    """
    queryset = AdmissionSettings.objects.all()
    serializer_class = AdmissionSettingsSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Allow filtering by school"""
        queryset = AdmissionSettings.objects.all()
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school__id=school_id)
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Track updates"""
        serializer.save()
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def check_status(self, request):
        """
        Public endpoint to check if admission is open for a school
        GET /api/admission/settings/check_status/?school=<school_id>
        """
        school_id = request.query_params.get('school')
        
        if not school_id:
            return Response(
                {'error': 'School ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            school = School.objects.get(id=school_id)
            settings_obj = AdmissionSettings.objects.filter(school=school).first()
            
            if not settings_obj:
                return Response({
                    'is_open': False,
                    'message': 'Admission settings not configured for this school'
                })
            
            return Response({
                'is_open': settings_obj.is_admission_open,
                'start_datetime': settings_obj.admission_start_datetime,
                'end_datetime': settings_obj.admission_end_datetime,
                'application_fee': settings_obj.application_fee_amount
            })
            
        except School.DoesNotExist:
            return Response(
                {'error': 'School not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['GET'])
@permission_classes([AllowAny])
def admission_metadata(request):
    """
    Get public admission metadata (schools, classes)
    """
    """
    Get public admission metadata (schools, classes)
    Only returns schools with active admission settings
    """
    # Get IDs of schools with open admission
    open_school_ids = AdmissionSettings.objects.filter(is_admission_open=True).values_list('school_id', flat=True)
    
    schools = School.objects.filter(id__in=open_school_ids).values('id', 'name')
    classes = Class.objects.filter(school_id__in=open_school_ids).values('id', 'name', 'school_id')
    
    return Response({
        'schools': schools,
        'classes': classes
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send OTP to email for verification
    """
    serializer = EmailOtpRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    school_name = serializer.validated_data['school'].name
    
    # Generate and send OTP
    otp = AdmissionService.generate_otp(email)
    sent = AdmissionService.send_otp_email(email, otp, school_name)
    
    if sent:
        return Response({
            'success': True, 
            'message': 'Verification code sent to your email.'
        })
    else:
        return Response(
            {'error': 'Failed to send email. Please try again.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_and_register(request):
    """
    Verify OTP and create account + login
    """
    serializer = OtpRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    email = serializer.validated_data['email']
    code = serializer.validated_data['otp_code']
    school = serializer.validated_data['school']
    class_applying_for = serializer.validated_data['class_applying_for']
    
    # Verify OTP
    if not AdmissionService.verify_otp(email, code):
        return Response(
            {'error': 'Invalid or expired verification code.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Proceed to Registration
    try:
        with transaction.atomic():
            # Generate permanent password
            password = AdmissionService.generate_temporary_password()
            
            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                user_type='applicant',
                is_active=True
            )
            
            # Create student
            student = Student.objects.create(
                user=user,
                school=school,
                class_model=class_applying_for,
                status='applicant',
                source='online_application',
                application_checklist={}
            )
            
            # Send welcome details
            AdmissionService.send_welcome_email_with_credentials(student, password, email)
            
            return Response({
                'success': True,
                'message': 'Registration successful! Please check your email for login credentials.',
                'user': {
                    'email': user.email,
                    'user_type': user.user_type
                }
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Kept for backward compatibility if needed, but deprecated
@api_view(['POST'])
@permission_classes([AllowAny])
def register_applicant(request):
    """Deprecated - Use send_otp + verify_and_register instead"""
    return Response({
        'error': 'This endpoint is deprecated. Please use the OTP flow instead.',
        'use_instead': {
            'step_1': '/admission/send-otp/',
            'step_2': '/admission/verify-otp/'
        }
    }, status=410)




@api_view(['POST'])
@permission_classes([IsApplicant])
def change_applicant_password(request):
    """
    Change applicant password
    Requires current password for verification
    """
    serializer = ApplicantChangePasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    # Verify current password
    if not user.check_password(serializer.validated_data['current_password']):
        return Response(
            {'error': 'Current password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set new password
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    
    return Response({
        'success': True,
        'message': 'Password changed successfully'
    })


@api_view(['GET'])
@permission_classes([IsApplicant])
def applicant_dashboard(request):
    """
    Get applicant dashboard data with checklist status
    """
    try:
        student = Student.objects.select_related(
            'school', 'class_model', 'biodata'
        ).prefetch_related(
            'guardians', 'documents'
        ).get(user=request.user)
        
        serializer = ApplicantDashboardSerializer(student)
        return Response(serializer.data)
        
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST', 'PUT', 'GET'])
@permission_classes([IsApplicant])
def applicant_biodata(request):
    """
    Manage applicant biodata
    GET: Retrieve biodata
    POST: Create biodata
    PUT: Update biodata
    """
    try:
        student = Student.objects.get(user=request.user)
        
        if request.method == 'GET':
            try:
                biodata = BioData.objects.get(student=student)
                serializer = BioDataSerializer(biodata)
                return Response(serializer.data)
            except BioData.DoesNotExist:
                return Response(
                    {'error': 'Biodata not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif request.method in ['POST', 'PUT']:
            try:
                biodata = BioData.objects.get(student=student)
                serializer = BioDataSerializer(biodata, data=request.data, partial=True)
            except BioData.DoesNotExist:
                serializer = BioDataSerializer(data=request.data)
            
            if serializer.is_valid():
                biodata = serializer.save(student=student)
                
                # Update checklist
                AdmissionService.update_checklist_item(student, 'biodata_complete', True)
                
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET', 'POST'])
@permission_classes([IsApplicant])
def applicant_guardians(request):
    """
    Manage applicant guardians
    GET: List all guardians
    POST: Add new guardian
    """
    try:
        student = Student.objects.get(user=request.user)
        
        if request.method == 'GET':
            guardians = Guardian.objects.filter(student=student)
            serializer = GuardianSerializer(guardians, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = GuardianSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save(student=student)
                
                # Check if at least father or mother is added
                has_guardian = Guardian.objects.filter(
                    student=student,
                    guardian_type__in=['father', 'mother']
                ).exists()
                
                if has_guardian:
                    AdmissionService.update_checklist_item(student, 'guardians_complete', True)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT', 'DELETE'])
@permission_classes([IsApplicant])
def applicant_guardian_detail(request, pk):
    """
    Update or delete specific guardian
    """
    try:
        student = Student.objects.get(user=request.user)
        guardian = get_object_or_404(Guardian, pk=pk, student=student)
        
        if request.method == 'PUT':
            serializer = GuardianSerializer(guardian, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            guardian.delete()
            
            # Recheck guardian completion
            has_guardian = Guardian.objects.filter(
                student=student,
                guardian_type__in=['father', 'mother']
            ).exists()
            
            AdmissionService.update_checklist_item(student, 'guardians_complete', has_guardian)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
    
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET', 'POST'])
@permission_classes([IsApplicant])
def applicant_documents(request):
    """
    Manage applicant documents
    GET: List all documents
    POST: Upload new document
    """
    try:
        student = Student.objects.get(user=request.user)
        
        if request.method == 'GET':
            documents = Document.objects.filter(student=student)
            serializer = DocumentSerializer(documents, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = DocumentSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save(student=student)
                
                # Check if required documents are uploaded
                required_types = ['birth_certificate', 'passport']
                uploaded_types = Document.objects.filter(student=student).values_list('document_type', flat=True)
                
                has_required = all(doc_type in uploaded_types for doc_type in required_types)
                
                if has_required:
                    AdmissionService.update_checklist_item(student, 'documents_complete', True)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsApplicant])
def applicant_document_detail(request, pk):
    """
    Delete specific document
    """
    try:
        student = Student.objects.get(user=request.user)
        document = get_object_or_404(Document, pk=pk, student=student)
        
        document.delete()
        
        # Recheck document completion
        required_types = ['birth_certificate', 'passport']
        uploaded_types = Document.objects.filter(student=student).values_list('document_type', flat=True)
        
        has_required = all(doc_type in uploaded_types for doc_type in required_types)
        
        AdmissionService.update_checklist_item(student, 'documents_complete', has_required)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsApplicant])
def payment_status(request):
    """
    Check applicant payment status
    """
    try:
        student = Student.objects.get(user=request.user)
        
        payment_info = AdmissionService.check_payment_status(student)
        
        # Update checklist
        if payment_info['has_paid']:
            AdmissionService.update_checklist_item(student, 'payment_complete', True)
        
        serializer = PaymentStatusSerializer(payment_info)
        return Response(serializer.data)
        
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsApplicant])
def initialize_payment(request):
    """
    Initialize Paystack payment for application fee
    """
    import os
    import uuid
    from django.conf import settings
    
    try:
        student = Student.objects.get(user=request.user)
        
        # Check if already paid
        payment_info = AdmissionService.check_payment_status(student)
        if payment_info['has_paid']:
            return Response(
                {'error': 'Application fee already paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get required amount from admission settings
        required_amount = payment_info.get('required_amount', 0)
        
        if required_amount <= 0:
            # Try to get from settings directly
            try:
                admission_settings = AdmissionSettings.objects.get(
                    school=student.school,
                    is_admission_open=True
                )
                required_amount = float(admission_settings.application_fee_amount)
            except AdmissionSettings.DoesNotExist:
                return Response(
                    {'error': 'Admission settings not configured. Please contact the school administrator.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if required_amount <= 0:
            return Response(
                {'error': 'Application fee amount not set. Please contact the school administrator.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get Paystack public key from settings
        paystack_public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', os.getenv('PAYSTACK_PUBLIC_KEY'))
        
        if not paystack_public_key:
            return Response(
                {'error': 'Payment gateway not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Generate unique reference
        reference = f"ADM-{student.application_number}-{uuid.uuid4().hex[:8].upper()}"
        
        return Response({
            'reference': reference,
            'email': student.user.email,
            'amount': int(required_amount),
            'public_key': paystack_public_key,
        })
        
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"❌ Payment initialization error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Failed to initialize payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsApplicant])
def verify_payment(request):
    """
    Verify Paystack payment and record in database
    """
    import os
    import requests
    from django.conf import settings
    from api.models.fee import FeeType, FeePayment, PaymentPurpose
    
    try:
        student = Student.objects.get(user=request.user)
        reference = request.data.get('reference')
        
        if not reference:
            return Response(
                {'error': 'Payment reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get Paystack secret key
        paystack_secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', os.getenv('PAYSTACK_SECRET_KEY'))
        
        if not paystack_secret_key:
            return Response(
                {'error': 'Payment gateway not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Verify payment with Paystack
        headers = {
            'Authorization': f'Bearer {paystack_secret_key}',
            'Content-Type': 'application/json'
        }
        
        verify_url = f'https://api.paystack.co/transaction/verify/{reference}'
        response = requests.get(verify_url, headers=headers)
        
        if response.status_code != 200:
            return Response(
                {'error': 'Failed to verify payment'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = response.json()
        
        if not data.get('status') or not data.get('data'):
            return Response(
                {'error': 'Invalid payment response'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_data = data['data']
        
        if payment_data['status'] != 'success':
            return Response(
                {'error': 'Payment not successful'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already recorded
        existing_payment = FeePayment.objects.filter(
            student=student,
            reference_number=reference
        ).exists()
        
        if existing_payment:
            return Response(
                {'message': 'Payment already recorded'},
                status=status.HTTP_200_OK
            )
        
        # Get or create admission fee type
        admission_purpose, _ = PaymentPurpose.objects.get_or_create(
            code='admission',
            defaults={'name': 'Application Fee', 'description': 'Admission application fee'}
        )
        
        # Get admission settings to get the fee amount
        from api.models.admission import AdmissionSettings
        admission_settings = AdmissionSettings.objects.filter(
            school=student.school,
            is_admission_open=True
        ).first()
        
        if not admission_settings:
            return Response(
                {'error': 'Admission settings not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create application fee type
        fee_type, _ = FeeType.objects.get_or_create(
            school=student.school,
            name='Application Fee',
            defaults={
                'amount': admission_settings.application_fee_amount,
                'description': 'Admission application fee',
                'is_mandatory': True,
                'is_active': True
            }
        )
        
        # Record payment
        amount_paid = payment_data['amount'] / 100  # Convert from kobo to naira
        
        FeePayment.objects.create(
            student=student,
            fee_type=fee_type,
            amount=amount_paid,
            payment_purpose=admission_purpose,
            payment_method='online',
            reference_number=reference,
            processed_by=None  # Auto-processed
        )
        
        # Update checklist
        AdmissionService.update_checklist_item(student, 'payment_complete', True)
        
        return Response({
            'message': 'Payment verified successfully',
            'amount': amount_paid
        })
        
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except requests.exceptions.RequestException as e:
        import traceback
        print(f"❌ Paystack API error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Payment verification failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        import traceback
        print(f"❌ Payment verification error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Payment verification failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsApplicant])
def submit_application(request):
    """
    Submit final application
    Generates seat number and application slip
    """
    try:
        student = Student.objects.get(user=request.user)
        
        # Submit application
        result = AdmissionService.submit_application(student)
        
        serializer = ApplicationSubmissionSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsApplicant])
def application_slip(request):
    """
    Get application slip details (not direct download)
    """
    try:
        student = Student.objects.get(user=request.user)
        
        # Check if application is submitted
        if not student.application_submitted_at:
            return Response(
                {'error': 'Application not yet submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get slip
        try:
            slip = ApplicationSlip.objects.get(student=student)
            serializer = ApplicationSlipSerializer(slip)
            return Response(serializer.data)
        except ApplicationSlip.DoesNotExist:
            return Response(
                {'error': 'Application slip not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Handle Paystack webhook notifications for all payment types
    """
    import os
    import hmac
    import hashlib
    from django.conf import settings
    from api.models.fee import FeeType, FeePayment, PaymentPurpose
    
    try:
        # Get Paystack secret key for signature verification
        paystack_secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', os.getenv('PAYSTACK_SECRET_KEY'))
        
        if not paystack_secret_key:
            return Response({'error': 'Webhook not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify webhook signature
        signature = request.headers.get('X-Paystack-Signature', '')
        body = request.body
        
        # Compute expected signature
        expected_signature = hmac.new(
            paystack_secret_key.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        if signature != expected_signature:
            print("❌ Invalid webhook signature")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Process webhook data
        data = request.data
        event = data.get('event')
        
        if event != 'charge.success':
            return Response({'message': 'Event ignored'}, status=status.HTTP_200_OK)
        
        payment_data = data.get('data', {})
        reference = payment_data.get('reference')
        metadata = payment_data.get('metadata', {})
        
        if not reference:
            return Response({'error': 'No reference provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine payment type and get student
        student = None
        payment_purpose_code = metadata.get('purpose', 'general')
        
        # Handle admission payments (ADM-APP123-XXXXXXXX or ADM-APP-2025-0003-XXXXXXXX)
        if reference.startswith('ADM-'):
            try:
                # Remove 'ADM-' prefix and the random suffix (last 8 chars after last dash)
                # Reference format: ADM-{app_number}-{random_8_chars}
                parts = reference[4:].rsplit('-', 1)  # Split from right, once
                app_number = parts[0] if len(parts) > 0 else reference[4:]
                student = Student.objects.get(application_number=app_number)
                payment_purpose_code = 'admission'
            except (IndexError, Student.DoesNotExist):
                print(f"❌ Student not found for admission reference: {reference}")
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle student payments with student ID in metadata
        elif metadata.get('student_id'):
            try:
                student = Student.objects.get(id=metadata['student_id'])
            except Student.DoesNotExist:
                print(f"❌ Student not found for ID: {metadata['student_id']}")
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle student payments with admission number in metadata
        elif metadata.get('admission_number'):
            try:
                student = Student.objects.get(admission_number=metadata['admission_number'])
            except Student.DoesNotExist:
                print(f"❌ Student not found for admission number: {metadata['admission_number']}")
                return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not student:
            print(f"❌ No student identified for reference: {reference}")
            return Response({'error': 'Student not identified'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if payment already recorded
        existing = FeePayment.objects.filter(student=student, reference_number=reference).exists()
        if existing:
            return Response({'message': 'Payment already recorded'}, status=status.HTTP_200_OK)
        
        # Get or create payment purpose
        payment_purpose, _ = PaymentPurpose.objects.get_or_create(
            code=payment_purpose_code,
            defaults={
                'name': metadata.get('purpose_name', payment_purpose_code.replace('_', ' ').title()),
                'description': f'Payment for {payment_purpose_code}'
            }
        )
        
        # Get fee type from metadata or find matching one
        fee_type_id = metadata.get('fee_type_id')
        if fee_type_id:
            try:
                fee_type = FeeType.objects.get(id=fee_type_id, school=student.school)
            except FeeType.DoesNotExist:
                print(f"❌ Fee type not found: {fee_type_id}")
                return Response({'error': 'Fee type not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # For admission, get/create application fee
            if payment_purpose_code == 'admission':
                admission_settings = AdmissionSettings.objects.filter(
                    school=student.school, is_admission_open=True
                ).first()
                
                if not admission_settings:
                    return Response({'error': 'Admission settings not found'}, status=status.HTTP_404_NOT_FOUND)
                
                fee_type, _ = FeeType.objects.get_or_create(
                    school=student.school,
                    name='Application Fee',
                    defaults={
                        'amount': admission_settings.application_fee_amount,
                        'description': 'Admission application fee',
                        'is_mandatory': True,
                        'is_active': True
                    }
                )
            else:
                # Try to find a matching fee type for this purpose
                fee_type = FeeType.objects.filter(
                    school=student.school,
                    is_active=True
                ).first()
                
                if not fee_type:
                    print(f"❌ No fee type found for purpose: {payment_purpose_code}")
                    return Response({'error': 'Fee type not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Record payment
        amount_paid = payment_data.get('amount', 0) / 100  # Convert from kobo to naira
        
        FeePayment.objects.create(
            student=student,
            fee_type=fee_type,
            amount=amount_paid,
            payment_purpose=payment_purpose,
            payment_method='online',
            reference_number=reference,
            notes=metadata.get('notes', ''),
            processed_by=None  # Auto-processed by webhook
        )
        
        # Update admission checklist if applicable
        if payment_purpose_code == 'admission':
            AdmissionService.update_checklist_item(student, 'payment_complete', True)
        
        print(f"✅ Webhook processed: {reference} - ₦{amount_paid} ({payment_purpose_code})")
        return Response({
            'message': 'Webhook processed successfully',
            'reference': reference,
            'amount': amount_paid,
            'purpose': payment_purpose_code
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"❌ Webhook error: {str(e)}")
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentPurposeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing payment purposes
    Read-only for applicants, full CRUD for admins
    """
    queryset = PaymentPurpose.objects.filter(is_active=True)
    serializer_class = PaymentPurposeSerializer
    permission_classes = [AllowAny]
