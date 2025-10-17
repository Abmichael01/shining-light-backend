from .auth import LoginView
from .academic import (
    SchoolViewSet, 
    SessionViewSet, 
    SessionTermViewSet,
    ClassViewSet,
    DepartmentViewSet,
    SubjectGroupViewSet,
    SubjectViewSet
)
from .student import (
    StudentViewSet,
    BioDataViewSet,
    GuardianViewSet,
    DocumentViewSet,
    BiometricViewSet,
    StudentSubjectViewSet
)

__all__ = [
    'LoginView', 
    'SchoolViewSet', 
    'SessionViewSet', 
    'SessionTermViewSet',
    'ClassViewSet',
    'DepartmentViewSet',
    'SubjectGroupViewSet',
    'SubjectViewSet',
    'StudentViewSet',
    'BioDataViewSet',
    'GuardianViewSet',
    'DocumentViewSet',
    'BiometricViewSet',
    'StudentSubjectViewSet'
]
