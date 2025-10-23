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
    ExamViewSet
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
router.register(r'exams', ExamViewSet, basename='exam')
 
urlpatterns = router.urls

