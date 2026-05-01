from rest_framework import status, renderers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Sum
from api.models import FeePayment, FeeType, Student
from api.serializers import FeePaymentSerializer, StudentFeeStatusSerializer
from django.utils import timezone

class FeeActionsMixin:
    """Mixin for Fee ViewSet custom actions"""

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        queryset = self.get_queryset()
        total_collected = queryset.aggregate(total=Sum('amount'))['total'] or 0
        total_payments = queryset.count()
        today = timezone.now().date()
        today_collection = queryset.filter(payment_date=today).aggregate(total=Sum('amount'))['total'] or 0
        today_count = queryset.filter(payment_date=today).count()
        
        return Response({
            'total_collected': float(total_collected),
            'total_payments': total_payments,
            'today_collected': float(today_collection),
            'today_count': today_count
        })

    @action(detail=False, methods=['post'])
    def record_payment(self, request):
        from api.serializers import RecordFeePaymentSerializer
        from api.utils.email import send_student_fee_receipt
        
        if getattr(request.user, 'user_type', None) == 'student':
             return Response({'error': 'Students cannot record payments manually.'}, status=403)

        serializer = RecordFeePaymentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment = serializer.save()
            send_student_fee_receipt(payment)
            return Response(FeePaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def download_receipt(self, request, pk=None):
        from api.utils.simple_receipt_generator import generate_receipt_html
        from django.http import HttpResponse
        payment = self.get_object()
        html_content = generate_receipt_html(payment)
        return HttpResponse(html_content, content_type='text/html')

    @action(detail=True, methods=['get'])
    def download_receipt_pdf(self, request, pk=None):
        from api.utils.simple_receipt_generator import generate_receipt_html
        from api.views.reports import generate_pdf_from_html
        from django.http import HttpResponse
        payment = self.get_object()
        html_content = generate_receipt_html(payment)
        pdf_data = generate_pdf_from_html(html_content, orientation='portrait')
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Receipt-{payment.receipt_number}.pdf"'
        return response

    @action(detail=False, methods=['get'])
    def student_fees(self, request):
        """
        Get fee statuses and receipt/payment history for a student.

        Students can only see their own fees. Admin/staff users may pass
        ?student=<id> to inspect a selected student's fee status.
        """
        user = request.user
        can_select_student = (
            getattr(user, 'is_superuser', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'user_type', None) in ['admin', 'staff', 'principal']
        )

        student_id = request.query_params.get('student')
        if student_id and can_select_student:
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

        session_id = (
            request.query_params.get('session_id')
            or request.query_params.get('session')
        )
        term_id = (
            request.query_params.get('term_id')
            or request.query_params.get('session_term')
        )

        if not session_id and student.current_session:
            session_id = student.current_session.id
        if not term_id and student.current_term:
            term_id = student.current_term.id

        base_fees = FeeType.objects.filter(school=student.school, is_active=True)
        fees_qs = base_fees.filter(
            models.Q(applicable_classes=student.class_model)
            | models.Q(applicable_students=student)
            | (
                models.Q(applicable_classes__isnull=True)
                & models.Q(applicable_students__isnull=True)
            )
        ).distinct()

        if term_id:
            fees_qs = fees_qs.filter(
                models.Q(active_terms__id=term_id)
                | models.Q(is_recurring_per_term=True)
                | models.Q(active_terms__isnull=True)
            ).distinct()

        fee_statuses = []
        for fee_type in fees_qs:
            context = fee_type.get_payment_status_context(
                student=student,
                session=session_id,
                session_term=term_id,
            )

            is_locked = False
            locked_message = ""
            for prerequisite in fee_type.prerequisites.all():
                prerequisite_context = prerequisite.get_payment_status_context(
                    student=student,
                    session=session_id,
                    session_term=term_id,
                )
                if prerequisite_context['status'] != 'paid':
                    is_locked = True
                    locked_message = f"Requires {prerequisite.name} to be paid first"
                    break

            payment_filters = {
                'student': student,
                'fee_type': fee_type,
            }
            if term_id and fee_type.is_recurring_per_term:
                payment_filters['session_term_id'] = term_id
            elif session_id:
                payment_filters['session_id'] = session_id

            payments = FeePayment.objects.filter(**payment_filters).order_by(
                '-payment_date',
                '-created_at'
            )

            fee_statuses.append({
                'fee_type_id': fee_type.id,
                'fee_type_name': fee_type.name,
                'fee_type_description': fee_type.description,
                'total_amount': context['applicable_amount'],
                'amount_paid': context['total_paid'],
                'amount_remaining': context['amount_remaining'],
                'installments_made': context['installments_made'],
                'installments_allowed': fee_type.max_installments,
                'status': context['status'],
                'is_mandatory': fee_type.is_mandatory,
                'is_recurring': fee_type.is_recurring_per_term,
                'staff_children_amount': fee_type.staff_children_amount,
                'is_staff_discount_applied': context['is_staff_child'],
                'payments': payments,
                'is_locked': is_locked,
                'locked_message': locked_message,
            })

        serializer = StudentFeeStatusSerializer(fee_statuses, many=True)
        return Response(serializer.data)
