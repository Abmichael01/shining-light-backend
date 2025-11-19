from rest_framework.routers import DefaultRouter
from api.views.academic import (
    SchoolViewSet, 
    SessionViewSet, 
    SessionTermViewSet,
    ClassViewSet,
    DepartmentViewSet,
    SubjectGroupViewSet,
    SubjectViewSet,
    TopicViewSet,
    GradeViewSet,
    QuestionViewSet,
    ClubViewSet,
    ExamHallViewSet,
    ExamViewSet,
    AssignmentViewSet,
    get_student_exams,
    get_student_exam_detail
)

router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'session-terms', SessionTermViewSet, basename='session-term')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'grades', GradeViewSet, basename='grade')
router.register(r'subject-groups', SubjectGroupViewSet, basename='subject-group')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'clubs', ClubViewSet, basename='club')
router.register(r'exam-halls', ExamHallViewSet, basename='exam-hall')
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'assignments', AssignmentViewSet, basename='assignment')

# Add custom URL patterns for student exams
from django.urls import path

urlpatterns = router.urls + [
    path('students/<str:student_id>/exams/', get_student_exams, name='student-exams'),
    path('student-exams/<int:student_exam_id>/', get_student_exam_detail, name='student-exam-detail'),
]

