"""
Configuration API Views
Provides centralized endpoints for commonly used reference data
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import School, Class, Subject, Department, Session, SessionTerm, SalaryGrade
from api.serializers import (
    SchoolSerializer,
    ClassSerializer,
    SubjectSerializer,
    DepartmentSerializer,
    SessionSerializer,
    SessionTermSerializer,
    SalaryGradeSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def school_configs(request):
    """
    Get all school configuration data in one request for caching.
    This includes schools, classes, subjects, departments, sessions, terms, salary grades.
    React Query will cache this data to avoid repeated API calls.
    """
    # Get all configuration data
    schools = School.objects.all()
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    departments = Department.objects.all()
    sessions = Session.objects.all()
    terms = SessionTerm.objects.all()
    salary_grades = SalaryGrade.objects.all()
    
    # Serialize all data
    data = {
        'schools': SchoolSerializer(schools, many=True).data,
        'classes': ClassSerializer(classes, many=True).data,
        'subjects': SubjectSerializer(subjects, many=True).data,
        'departments': DepartmentSerializer(departments, many=True).data,
        'sessions': SessionSerializer(sessions, many=True).data,
        'terms': SessionTermSerializer(terms, many=True).data,
        'salary_grades': SalaryGradeSerializer(salary_grades, many=True).data,
    }
    
    return Response(data)

