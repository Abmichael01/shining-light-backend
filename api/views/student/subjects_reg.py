from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, models
from django.utils import timezone
from api.models import (
    Student, StudentSubject, SessionTerm, Subject
)
from api.serializers import StudentSubjectSerializer
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSchoolAdmin

class SubjectRegistrationMixin:
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='check_late_registration')
    def check_late_registration(self, request):
        user = request.user
        if getattr(user, 'user_type', None) != 'student':
            return Response({'is_late': False, 'late_fee_paid': True})
            
        student_id = request.query_params.get('student')
        session_id = request.query_params.get('session')
        session_term_id = request.query_params.get('session_term')
        
        if not student_id or not session_term_id:
            return Response({'error': 'student and session_term required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if user.student_profile.id != student.id:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            session_term = SessionTerm.objects.get(id=session_term_id)
        except SessionTerm.DoesNotExist:
            return Response({'error': 'Session term not found'}, status=status.HTTP_404_NOT_FOUND)
            
        is_late = False
        if session_term.registration_deadline and timezone.now().date() > session_term.registration_deadline:
            is_late = True
            
        paid_late_fee = False
        fee_type_id = None
        amount = 0
        
        if is_late:
            from api.models.fee.payment import FeePayment
            paid_late_fee = FeePayment.objects.filter(
                student_id=student.id, 
                session_term_id=session_term.id, 
                payment_purpose__code='late_registration'
            ).exists()
            
            if not paid_late_fee:
                from api.models.academic import SystemSetting
                from api.models.fee.structure import FeeType, PaymentPurpose
                
                setting, _ = SystemSetting.objects.get_or_create(pk=1)
                amount = setting.late_subject_registration_fee
                
                purpose, _ = PaymentPurpose.objects.get_or_create(
                    code='late_registration',
                    defaults={'name': 'Late Registration Fee', 'description': 'Fee for registering subjects after the deadline'}
                )
                
                fee_type, created = FeeType.objects.get_or_create(
                    school=student.school,
                    name='Late Subject Registration Fee',
                    defaults={
                        'amount': amount,
                        'is_mandatory': False,
                        'is_recurring_per_term': True,
                    }
                )
                if not created and fee_type.amount != amount:
                    fee_type.amount = amount
                    fee_type.save()
                    
                fee_type_id = fee_type.id
                
        return Response({
            'is_late': is_late,
            'late_fee_paid': paid_late_fee,
            'fee_type_id': fee_type_id,
            'amount': amount
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='bulk_register')
    def bulk_register(self, request):
        student_id = request.data.get('student')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        subjects = request.data.get('subjects', [])
        
        user = request.user
        user_type = getattr(user, 'user_type', None)
        
        if user_type == 'student':
            try:
                student = Student.objects.select_related('user').get(user=user)
                if str(student.id) != str(student_id):
                    return Response({'detail': 'You can only register subjects for yourself.'}, status=status.HTTP_403_FORBIDDEN)
            except Student.DoesNotExist:
                return Response({'detail': 'Student profile not found for current user.'}, status=status.HTTP_404_NOT_FOUND)
        elif user_type != 'admin':
            return Response({'detail': 'Only administrators and students can register subjects.'}, status=status.HTTP_403_FORBIDDEN)

        if not student_id or not session_id:
            return Response({'detail': 'student and session are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(subjects, (list, tuple)) or len(subjects) == 0:
            return Response({'detail': 'subjects must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)

        session_term_obj = None
        if session_term_id:
            try:
                session_term_obj = SessionTerm.objects.get(id=session_term_id)
            except SessionTerm.DoesNotExist:
                pass

        is_late_global = False
        if session_term_obj and session_term_obj.registration_deadline:
            if timezone.now().date() > session_term_obj.registration_deadline:
                is_late_global = True
        
        if user_type == 'student':
            from api.models.fee import FeeType
            mandatory_fees = FeeType.objects.filter(
                school_id=request.user.student_profile.school_id, is_active=True
            ).filter(
                models.Q(is_mandatory=True) | models.Q(name__icontains='Tuition')
            ).filter(
                models.Q(applicable_classes__isnull=True) | models.Q(applicable_classes=request.user.student_profile.class_model)
            ).filter(
                models.Q(active_terms__id=session_term_id) | models.Q(is_recurring_per_term=True)
            ).distinct()
            
            unpaid_mandatory_fees = []
            for fee in mandatory_fees:
                paid_amount = fee.get_student_total_paid(request.user.student_profile.id, session=session_id, session_term=session_term_id)
                if paid_amount < fee.amount:
                    unpaid_mandatory_fees.append(fee.name)
            
            if unpaid_mandatory_fees:
                return Response({
                    'detail': f'Registration Locked: Please pay the following mandatory fees first: {", ".join(unpaid_mandatory_fees)}',
                    'unpaid_fees': unpaid_mandatory_fees
                }, status=status.HTTP_403_FORBIDDEN)
        
        created_items = []
        errors = []
        with transaction.atomic():
            for subject_id in subjects:
                try:
                    filter_query = {'student_id': student_id, 'subject_id': subject_id, 'session_id': session_id}
                    if session_term_id:
                        filter_query['session_term_id'] = session_term_id
                    
                    if StudentSubject.objects.filter(**filter_query).exists():
                        errors.append(f'Subject {subject_id} already registered.')
                        continue
                    
                    subject_obj = Subject.objects.get(id=subject_id)
                    student_obj = Student.objects.get(id=student_id)
                    
                    if subject_obj.class_model != student_obj.class_model:
                        errors.append(f'Subject {subject_obj.name} does not belong to your class.')
                        continue
                    
                    paid_late_fee = False
                    if is_late_global:
                        from api.models.fee import FeePayment
                        paid_late_fee = FeePayment.objects.filter(
                            student_id=student_id, session_term_id=session_term_id, payment_purpose__code='late_registration'
                        ).exists()

                    registration = StudentSubject(
                        student_id=student_id, subject_id=subject_id, session_id=session_id,
                        session_term_id=session_term_id if session_term_id else None,
                        is_active=True, is_late_registration=is_late_global, late_fee_paid=paid_late_fee
                    )
                    registration.full_clean()
                    registration.save()
                    created_items.append(registration)
                except Exception as exc:
                    errors.append(f'Error registering subject {subject_id}: {str(exc)}')

        serializer = StudentSubjectSerializer(created_items, many=True, context={'request': request})
        return Response({'registered': len(created_items), 'errors': errors, 'data': serializer.data}, 
                        status=status.HTTP_201_CREATED if created_items else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsSchoolAdmin])
    def mark_clear(self, request, pk=None):
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
        student_subject.save()
        return Response(StudentSubjectSerializer(student_subject).data)

    @action(detail=False, methods=['post'], permission_classes=[IsSchoolAdmin])
    def bulk_mark_clear(self, request):
        student_id = request.data.get('student')
        session_id = request.data.get('session')
        session_term_id = request.data.get('session_term')
        cleared_value = request.data.get('cleared', True)
        cleared = str(cleared_value).lower() not in ['false', '0', 'no', 'none']
        if not (student_id and session_id and session_term_id):
            return Response({'error': 'Required fields missing'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = StudentSubject.objects.filter(student_id=student_id, session_id=session_id, session_term_id=session_term_id)
        if cleared:
            queryset.update(cleared=True, cleared_by=request.user, cleared_at=timezone.now(), updated_at=timezone.now())
        else:
            queryset.update(cleared=False, cleared_by=None, cleared_at=None, updated_at=timezone.now())
        return Response({'message': f'Updated {queryset.count()} subjects'})
