from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from api.models import AdmissionExamResult, SystemSetting, Student
from api.serializers.student import AdmissionExamResultSerializer
from api.permissions import IsApplicant


@api_view(['GET'])
@permission_classes([IsApplicant])
def get_my_admission_result(request):
    """Applicant views their own admission result from the admission portal."""
    settings = SystemSetting.load()
    if not settings.show_admission_exam_results:
        return Response(
            {'error': 'Admission results are not yet published.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        student_obj = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student profile not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    result = (
        AdmissionExamResult.objects
        .filter(student=student_obj)
        .select_related('exam', 'student')
        .prefetch_related('subject_results__subject')
        .first()
    )

    if not result:
        return Response(
            {'error': 'No admission result found for your account.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        AdmissionExamResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )
