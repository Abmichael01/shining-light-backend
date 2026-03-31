from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from api.models import (
    FeeType, FeePayment, Student, SystemSetting, ResultPin
)
from api.utils.paystack import Paystack
import uuid

class PaystackMixin:
    """Mixin for Paystack related actions in FeePaymentViewSet"""

    @action(detail=False, methods=['post'])
    def initialize_payment(self, request):
        user = request.user
        fee_type_id = request.data.get('fee_type_id')
        amount = request.data.get('amount')
        
        if not fee_type_id or not amount:
            return Response({'error': 'Fee Type ID and Amount are required'}, status=400)
            
        fee_type = FeeType.objects.get(id=fee_type_id)
        student = getattr(user, 'student_profile', None)
        
        if not student and (user.is_superuser or user.user_type in ['admin', 'staff']):
            student_id = request.data.get('student_id')
            if student_id:
                student = Student.objects.get(pk=student_id)

        if not student:
             return Response({'error': 'Student profile required.'}, status=400)
             
        reference = f"TREF-{uuid.uuid4().hex[:12].upper()}"
        settings_obj = SystemSetting.load()
        callback_url = f"{settings_obj.FRONTEND_URL}/portals/student/fees/callback"
        
        metadata = {
            'fee_type_id': fee_type.id,
            'student_id': student.id,
            'session_id': student.current_session.id if student.current_session else None,
            'term_id': student.current_term.id if student.current_term else None,
            'custom_fields': [
                {'display_name': "Fee Type", 'variable_name': "fee_type", 'value': fee_type.name},
                {'display_name': "Student", 'variable_name': "student", 'value': student.get_full_name()}
            ]
        }
        
        paystack = Paystack()
        response = paystack.initialize_transaction(
            email=user.email, amount=float(amount), reference=reference,
            callback_url=callback_url, metadata=metadata
        )
        
        if response:
            return Response({
                'authorization_url': response['authorization_url'],
                'access_code': response['access_code'],
                'reference': reference
            })
        return Response({'error': 'Failed to initialize payment'}, status=500)

    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        reference = request.data.get('reference')
        fee_type_id = request.data.get('fee_type_id')
        student_id = request.data.get('student_id')
        
        if not reference:
             return Response({'error': 'Reference is required'}, status=400)
            
        paystack = Paystack()
        data = paystack.verify_transaction(reference)
        
        if data and data['status'] == 'success':
            amount_paid = float(data['amount']) / 100
            
            if FeePayment.objects.filter(reference_number=reference).exists():
                  return Response({'status': 'success', 'message': 'Already verified', 'amount': amount_paid})
            
            try:
                with transaction.atomic():
                    metadata = data.get('metadata', {})
                    student = getattr(request.user, 'student_profile', None)
                    if not student and student_id:
                        student = Student.objects.get(id=student_id)
                    
                    if not student:
                        return Response({'error': 'Student not identified'}, status=400)

                    # 1. Handle PIN Purchase
                    if metadata.get('is_pin_purchase'):
                        pin_fee_type, _ = FeeType.objects.get_or_create(
                            name="Result PIN",
                            defaults={
                                'school': student.school, 'amount': amount_paid,
                                'description': "Fee for checking results via PIN",
                                'is_active': True, 'is_mandatory': False
                            }
                        )
                        
                        payment = FeePayment.objects.create(
                            student=student, fee_type=pin_fee_type, amount=amount_paid,
                            session=student.current_session, session_term=student.current_term,
                            payment_method='online', payment_date=timezone.now().date(),
                            reference_number=reference, notes=f"Result PIN Purchase ({reference})",
                            processed_by=request.user
                        )
                        
                        pin_record = ResultPin.objects.create(payment=payment, student=student)
                        return Response({
                            'status': 'success', 'message': 'PIN purchased',
                            'pin': pin_record.pin, 'serial': pin_record.serial_number, 'amount': amount_paid
                        })

                    # 2. Handle Regular Fee Payment
                    if not fee_type_id: fee_type_id = metadata.get('fee_type_id')
                    fee_type = FeeType.objects.get(id=fee_type_id)
                    payment = FeePayment.objects.create(
                        student=student, fee_type=fee_type, amount=amount_paid,
                        session=student.current_session, session_term=student.current_term,
                        payment_method='online', payment_date=timezone.now().date(),
                        reference_number=reference, notes=f"Paystack Ref: {reference}",
                        processed_by=request.user
                    )
                    return Response({'status': 'success', 'message': 'Recorded', 'amount': amount_paid})
            except Exception as e:
                return Response({'error': f'Failed: {str(e)}'}, status=500)
        return Response({'error': 'Verification failed'}, status=400)

    @action(detail=False, methods=['post'])
    def initialize_pin_purchase(self, request):
        import uuid
        user = request.user
        student = getattr(user, 'student_profile', None)
        
        if not student:
            return Response({'error': 'Only students can purchase PINs.'}, status=400)
            
        settings_obj = SystemSetting.load()
        amount = settings_obj.result_pin_price
        
        if not amount or amount <= 0:
            return Response({'error': 'Result PIN price not configured.'}, status=400)
            
        reference = f"PIN-{uuid.uuid4().hex[:12].upper()}"
        callback_url = f"{request.build_absolute_uri('/')[:-1].replace(':8007', ':3050')}/portals/student/results/callback"

        metadata = {
            'is_pin_purchase': True, 'student_id': student.id, 'amount': float(amount),
            'custom_fields': [
                {'display_name': "Payment For", 'variable_name': "payment_for", 'value': "Result Checking PIN"},
                {'display_name': "Student", 'variable_name': "student", 'value': student.get_full_name()}
            ]
        }
        
        paystack = Paystack()
        response = paystack.initialize_transaction(
            email=user.email, amount=float(amount), reference=reference,
            callback_url=callback_url, metadata=metadata
        )
        
        if response:
            return Response({
                'authorization_url': response['authorization_url'],
                'reference': reference, 'amount': float(amount)
            })
        return Response({'error': 'Failed'}, status=500)
