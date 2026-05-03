import zipfile
import os
import csv
import io
from django.core.files.base import ContentFile
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from api.models import (
    ExternalExamBody, ExternalExam, ExternalExamResult, ExternalExamAccess,
    Student, FeePayment, FeeType, SystemSetting,
)
from api.permissions import IsAdminOrStaff, IsAdminOrStaffOrStudent
from api.serializers import (
    ExternalExamBodySerializer,
    ExternalExamSerializer,
    ExternalExamResultSerializer,
    ExternalExamAccessSerializer,
    StudentExternalExamSerializer,
)


class ExternalExamBodyViewSet(viewsets.ModelViewSet):
    queryset = ExternalExamBody.objects.all()
    serializer_class = ExternalExamBodySerializer
    permission_classes = [IsAdminOrStaff]


class ExternalExamViewSet(viewsets.ModelViewSet):
    queryset = ExternalExam.objects.select_related('body', 'applicable_class').all()
    serializer_class = ExternalExamSerializer
    permission_classes = [IsAdminOrStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        staff = getattr(self.request.user, 'staff_profile', None)
        serializer.save(created_by=staff)

    @action(detail=True, methods=['post'], url_path='upload-result')
    def upload_result(self, request, pk=None):
        """Upload or update a single student's result (file + grades)."""
        exam = self.get_object()
        student_id = request.data.get('student_id')
        grades_raw = request.data.get('grades')
        result_file = request.FILES.get('result_file')

        if not student_id:
            return Response({'error': 'student_id is required.'}, status=400)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=404)

        grades = None
        if grades_raw:
            import json
            try:
                grades = json.loads(grades_raw) if isinstance(grades_raw, str) else grades_raw
            except (ValueError, TypeError):
                return Response({'error': 'grades must be valid JSON.'}, status=400)

        if not result_file and not grades:
            return Response({'error': 'Provide at least a result file or grades.'}, status=400)

        result, created = ExternalExamResult.objects.get_or_create(
            exam=exam, student=student
        )
        if result_file:
            result.result_file = result_file
        if grades:
            result.grades = grades
        result.save()

        serializer = ExternalExamResultSerializer(result, context={'request': request})
        return Response(serializer.data, status=201 if created else 200)

    @action(detail=True, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request, pk=None):
        """
        Bulk upload results via:
        - ZIP file: each file named {admission_number}.pdf/.jpg/.png
        - CSV file: columns admission_number, subject, grade (multiple rows per student)
        """
        exam = self.get_object()
        zip_file = request.FILES.get('zip_file')
        csv_file = request.FILES.get('csv_file')

        if not zip_file and not csv_file:
            return Response({'error': 'Provide either a zip_file or csv_file.'}, status=400)

        created_count = 0
        updated_count = 0
        errors = []

        if zip_file:
            try:
                with zipfile.ZipFile(zip_file) as zf:
                    for filename in zf.namelist():
                        name, ext = os.path.splitext(filename)
                        if ext.lower() not in ['.pdf', '.jpg', '.jpeg', '.png']:
                            continue
                        admission_number = name.strip()
                        try:
                            student = Student.objects.get(admission_number=admission_number)
                        except Student.DoesNotExist:
                            errors.append(f'{filename}: admission number not found')
                            continue

                        file_data = zf.read(filename)
                        result, created = ExternalExamResult.objects.get_or_create(
                            exam=exam, student=student
                        )
                        result.result_file.save(filename, ContentFile(file_data), save=True)
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
            except zipfile.BadZipFile:
                return Response({'error': 'Invalid zip file.'}, status=400)

        if csv_file:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            # Group rows by admission_number
            student_grades: dict = {}
            for row in reader:
                adm = row.get('admission_number', '').strip()
                subject = row.get('subject', '').strip()
                grade = row.get('grade', '').strip()
                if not adm or not subject or not grade:
                    continue
                student_grades.setdefault(adm, []).append({'subject': subject, 'grade': grade})

            for admission_number, grades in student_grades.items():
                try:
                    student = Student.objects.get(admission_number=admission_number)
                except Student.DoesNotExist:
                    errors.append(f'{admission_number}: not found')
                    continue
                result, created = ExternalExamResult.objects.get_or_create(
                    exam=exam, student=student
                )
                result.grades = grades
                result.save()
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return Response({
            'created': created_count,
            'updated': updated_count,
            'errors': errors,
        })

    @action(detail=True, methods=['get'], url_path='results')
    def list_results(self, request, pk=None):
        """List all uploaded results for this exam (admin view)."""
        exam = self.get_object()
        results = ExternalExamResult.objects.filter(exam=exam).select_related('student')
        serializer = ExternalExamResultSerializer(results, many=True, context={'request': request})
        return Response(serializer.data)


class StudentExternalExamViewSet(viewsets.ReadOnlyModelViewSet):
    """Student-facing: list exams applicable to their class, with access/result status."""
    serializer_class = StudentExternalExamSerializer
    permission_classes = [IsAdminOrStaffOrStudent]

    def get_queryset(self):
        user = self.request.user
        student = getattr(user, 'student_profile', None)
        if not student:
            return ExternalExam.objects.none()
        return ExternalExam.objects.filter(
            applicable_class=student.class_model
        ).select_related('body', 'applicable_class')

    @action(detail=True, methods=['post'], url_path='request-access')
    def request_access(self, request, pk=None):
        """Initialize payment to unlock an external exam result."""
        exam = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'error': 'Student profile not found.'}, status=400)

        if ExternalExamAccess.objects.filter(student=student, exam=exam).exists():
            return Response({'error': 'You already have access to this exam result.'}, status=400)

        if not ExternalExamResult.objects.filter(student=student, exam=exam).exists():
            return Response({'error': 'Your result has not been uploaded yet.'}, status=404)

        setting = SystemSetting.load()
        fee = setting.external_exam_access_fee

        return Response({
            'exam_id': exam.id,
            'exam': str(exam),
            'amount': float(fee),
            'message': 'Proceed to payment to unlock your result.',
        })

    @action(detail=True, methods=['post'], url_path='grant-access')
    def grant_access(self, request, pk=None):
        """
        Grant access after payment verification.
        Called internally after Paystack callback confirms payment.
        Expects: payment_id
        """
        exam = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'error': 'Student profile not found.'}, status=400)

        payment_id = request.data.get('payment_id')
        payment = None
        if payment_id:
            try:
                payment = FeePayment.objects.get(id=payment_id, student=student)
            except FeePayment.DoesNotExist:
                pass

        access, created = ExternalExamAccess.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={'payment': payment},
        )
        if not created:
            return Response({'error': 'Access already granted.'}, status=400)

        result = ExternalExamResult.objects.filter(student=student, exam=exam).first()
        serializer = ExternalExamResultSerializer(result, context={'request': request})
        return Response({'message': 'Access granted.', 'result': serializer.data})
