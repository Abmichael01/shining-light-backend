from .auth import LoginView
from .academic import (
    SchoolViewSet, 
    SessionViewSet, 
    SessionTermViewSet,
    ClassViewSet,
    DepartmentViewSet,
    SubjectGroupViewSet,
    SubjectViewSet,
    TopicViewSet,
    GradeViewSet,
    QuestionViewSet
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
    'TopicViewSet',
    'GradeViewSet',
    'QuestionViewSet',
    'StudentViewSet',
    'BioDataViewSet',
    'GuardianViewSet',
    'DocumentViewSet',
    'BiometricViewSet',
    'StudentSubjectViewSet'
]
