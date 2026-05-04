from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from api.models import (
    FeeType, FeePayment, Student, SystemSetting, ResultPin, Session, SessionTerm,
    ExternalExam, ExternalExamAccess
)
from api.utils.paystack import Paystack
import uuid

class PaystackMixin:
    """Mixin for Paystack related actions in FeePaymentViewSet"""

    def _get_frontend_url(self):
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3050')
        return (frontend_url or 'http://localhost:3050').rstrip('/')

    def _get_payment_student(self, request, student_id=None):
        student = getattr(request.user, 'student_profile', None)
        if student:
            return student

        can_select_student = (
            request.user.is_superuser or
            getattr(request.user, 'user_type', None) in ['admin', 'staff']
        )
        if student_id and can_select_student:
            return Student.objects.get(pk=student_id)
        return None

    def _resolve_payment_period(self, student, session_id=None, term_id=None):
        session = student.current_session
        session_term = student.current_term

        try:
            if session_id:
                session = Session.objects.get(pk=session_id)
            if term_id:
                session_term = SessionTerm.objects.select_related('session').get(pk=term_id)
                if session and session_term.session_id != session.id:
                    raise ValueError('Selected term does not belong to selected session.')
                session = session_term.session
        except (Session.DoesNotExist, SessionTerm.DoesNotExist, ValueError, TypeError):
            raise ValueError('Selected session or term is invalid.')

        return session, session_term

    @action(detail=False, methods=['post'])
    def initialize_payment(self, request):
        user = request.user
        fee_type_id = request.data.get('fee_type_id')
        amount = request.data.get('amount')
        session_id = request.data.get('session_id') or request.data.get('session')
        term_id = request.data.get('term_id') or request.data.get('session_term')
        
        if not fee_type_id or not amount:
            return Response({'error': 'Fee Type ID and Amount are required'}, status=400)
            
        try:
            fee_type = FeeType.objects.get(id=fee_type_id)
        except FeeType.DoesNotExist:
            return Response({'error': 'Fee type not found.'}, status=404)

        student = self._get_payment_student(request, request.data.get('student_id'))

        if not student:
             return Response({'error': 'Student profile required.'}, status=400)

        try:
            payment_session, payment_term = self._resolve_payment_period(student, session_id, term_id)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)
             
        reference = f"TREF-{uuid.uuid4().hex[:12].upper()}"
        frontend_url = self._get_frontend_url()
        callback_url = f"{frontend_url}/portals/student/fees/callback"
        
        metadata = {
            'fee_type_id': fee_type.id,
            'student_id': student.id,
            'session_id': payment_session.id if payment_session else None,
            'term_id': payment_term.id if payment_term else None,
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
        session_id = request.data.get('session_id') or request.data.get('session')
        term_id = request.data.get('term_id') or request.data.get('session_term')
        
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
                    if not isinstance(metadata, dict):
                        metadata = {}

                    student = self._get_payment_student(
                        request,
                        student_id or metadata.get('student_id')
                    )
                    
                    if not student:
                        return Response({'error': 'Student not identified'}, status=400)

                    session_id = session_id or metadata.get('session_id')
                    term_id = term_id or metadata.get('term_id')
                    payment_session, payment_term = self._resolve_payment_period(
                        student,
                        session_id,
                        term_id
                    )

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

                    # 3. Handle External Exam Access
                    if metadata.get('is_external_exam_access'):
                        exam_id = metadata.get('exam_id')
                        try:
                            exam = ExternalExam.objects.get(id=exam_id)
                        except ExternalExam.DoesNotExist:
                            return Response({'error': 'Exam not found'}, status=404)

                        fee_type, _ = FeeType.objects.get_or_create(
                            name="External Exam Access",
                            defaults={
                                'school': student.school, 'amount': amount_paid,
                                'description': f"Access fee for {exam.body_short_name} {exam.year}",
                                'is_active': True, 'is_mandatory': False
                            }
                        )

                        payment = FeePayment.objects.create(
                            student=student, fee_type=fee_type, amount=amount_paid,
                            session=payment_session, session_term=payment_term,
                            payment_method='online', payment_date=timezone.now().date(),
                            reference_number=reference, notes=f"External Exam Access ({exam.body_short_name})",
                            processed_by=request.user
                        )

                        # Grant access
                        ExternalExamAccess.objects.get_or_create(
                            student=student, exam=exam,
                            defaults={'payment': payment}
                        )

                        return Response({
                            'status': 'success', 'message': 'Access granted',
                            'exam_id': exam_id, 'amount': amount_paid
                        })

                    # 4. Handle Regular Fee Payment
                    if not fee_type_id: fee_type_id = metadata.get('fee_type_id')
                    fee_type = FeeType.objects.get(id=fee_type_id)
                    payment = FeePayment.objects.create(
                        student=student, fee_type=fee_type, amount=amount_paid,
                        session=payment_session, session_term=payment_term,
                        payment_method='online', payment_date=timezone.now().date(),
                        reference_number=reference, notes=f"Paystack Ref: {reference}",
                        processed_by=request.user
                    )
                    return Response({'status': 'success', 'message': 'Recorded', 'amount': amount_paid})
            except Exception as e:
                return Response({'error': f'Failed: {str(e)}'}, status=500)
        return Response({'error': 'Verification failed'}, status=400)

    @action(detail=False, methods=['post'])
    def initialize_external_exam_payment(self, request):
        user = request.user
        student = getattr(user, 'student_profile', None)
        exam_id = request.data.get('exam_id')

        if not student:
            return Response({'error': 'Only students can request access.'}, status=400)
        
        if not exam_id:
            return Response({'error': 'Exam ID is required.'}, status=400)

        try:
            exam = ExternalExam.objects.get(id=exam_id)
        except ExternalExam.DoesNotExist:
            return Response({'error': 'Exam not found.'}, status=404)

        if ExternalExamAccess.objects.filter(student=student, exam=exam).exists():
            return Response({'error': 'Access already granted.'}, status=400)

        settings_obj = SystemSetting.load()
        amount = settings_obj.external_exam_access_fee
        
        if not amount or amount <= 0:
            return Response({'error': 'Access fee not configured.'}, status=400)
            
        reference = f"EXT-{uuid.uuid4().hex[:12].upper()}"
        callback_url = f"{self._get_frontend_url()}/portals/student/external-results"

        metadata = {
            'is_external_exam_access': True, 
            'student_id': student.id, 
            'exam_id': exam.id,
            'amount': float(amount),
            'custom_fields': [
                {'display_name': "Payment For", 'variable_name': "payment_for", 'value': f"Access to {exam.body_short_name} {exam.year}"},
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
        return Response({'error': 'Failed to initialize payment'}, status=500)

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
        callback_url = f"{self._get_frontend_url()}/portals/student/results/callback"

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
