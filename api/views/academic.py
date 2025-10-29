from django.db import models
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSchoolAdmin
from api.models import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject, Topic, Grade, Question, Club, Exam, Student, StudentExam, StudentAnswer
from api.serializers import (
    SchoolSerializer, 
    SessionSerializer, 
    SessionTermSerializer,
    ClassSerializer,
    DepartmentSerializer,
    SubjectGroupSerializer,
    SubjectSerializer,
    TopicSerializer,
    GradeSerializer,
    QuestionSerializer,
    QuestionListSerializer,
    ClubSerializer,
    ExamSerializer
)
from api.permissions import IsSchoolAdmin
from datetime import date


class SchoolViewSet(viewsets.ModelViewSet):
    """
    ViewSet for School CRUD operations
    Only admin users can manage schools
    """
    queryset = School.objects.all().order_by('school_type', 'name')
    serializer_class = SchoolSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter schools - can add filters here if needed"""
        queryset = super().get_queryset()
        
        # Optional: Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )
        
        return queryset


class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Session CRUD operations
    """
    queryset = Session.objects.all().order_by('-start_date')
    serializer_class = SessionSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter and search sessions"""
        queryset = super().get_queryset()
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        """Set this session as the current session"""
        session = self.get_object()
        
        # Deactivate all sessions
        Session.objects.all().update(is_current=False)
        
        # Activate this session
        session.is_current = True
        session.save()
        
        return Response({
            'detail': f'Session {session.name} is now current'
        })
    
    @action(detail=True, methods=['post'])
    def start_next_term(self, request, pk=None):
        """Start the next term for this session"""
        session = self.get_object()
        
        term_name = request.data.get('term_name')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not all([term_name, start_date, end_date]):
            return Response(
                {'detail': 'term_name, start_date, and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session_term = session.create_next_term(term_name, start_date, end_date)
            return Response({
                'detail': f'{term_name} started successfully',
                'session_term': SessionTermSerializer(session_term).data
            })
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SessionTermViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SessionTerm operations
    """
    queryset = SessionTerm.objects.all().order_by('-session__start_date', 'term_name')
    serializer_class = SessionTermSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter by session if provided"""
        queryset = super().get_queryset()
        
        session_id = self.request.query_params.get('session', None)
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        """Set this session term as current"""
        session_term = self.get_object()
        
        # Deactivate all terms in this session
        SessionTerm.objects.filter(session=session_term.session).update(is_current=False)
        
        # Activate this term
        session_term.is_current = True
        session_term.save()
        
        return Response({
            'detail': f'{session_term.term_name} is now current for {session_term.session.name}'
        })


class ClassViewSet(viewsets.ModelViewSet):
    """ViewSet for Class CRUD operations"""
    queryset = Class.objects.all().order_by('school', 'order', 'name')
    serializer_class = ClassSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        school = self.request.query_params.get('school', None)
        if school:
            queryset = queryset.filter(school=school)
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(class_code__icontains=search)
            )
        
        return queryset


class DepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Department CRUD operations"""
    queryset = Department.objects.all().order_by('school', 'name')
    serializer_class = DepartmentSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        school = self.request.query_params.get('school', None)
        if school:
            queryset = queryset.filter(school=school)
        return queryset


class SubjectGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for SubjectGroup CRUD operations"""
    queryset = SubjectGroup.objects.all().order_by('name')
    serializer_class = SubjectGroupSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter and search subject groups"""
        queryset = super().get_queryset()
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )
        
        return queryset


class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Subject CRUD operations"""
    queryset = Subject.objects.select_related(
        'school', 'class_model', 'department', 'subject_group'
    ).all().order_by('school', 'class_model', 'order', 'name')
    serializer_class = SubjectSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by school
        school = self.request.query_params.get('school', None)
        if school:
            queryset = queryset.filter(school=school)
        
        # Filter by class
        class_model = self.request.query_params.get('class', None)
        if class_model:
            queryset = queryset.filter(class_model=class_model)
        
        # Filter by department
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department=department)
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )
        
        return queryset


class TopicViewSet(viewsets.ModelViewSet):
    """ViewSet for Topic CRUD operations"""
    queryset = Topic.objects.select_related('subject').prefetch_related('questions').all().order_by('subject', 'name')
    serializer_class = TopicSerializer
    permission_classes = [IsSchoolAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by subject
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(subject=subject)
        
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search)
            )
        
        return queryset


class GradeViewSet(viewsets.ModelViewSet):
    """ViewSet for Grade CRUD operations"""
    queryset = Grade.objects.all().order_by('order')
    serializer_class = GradeSerializer
    permission_classes = [IsSchoolAdmin]


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for Question CRUD operations"""
    queryset = Question.objects.all().select_related('subject', 'subject__class_model', 'subject__class_model__school', 'created_by')
    permission_classes = [IsSchoolAdmin]
    
    def get_serializer_class(self):
        """Use different serializer for list vs detail"""
        if self.action == 'list':
            return QuestionListSerializer
        return QuestionSerializer
    
    def get_queryset(self):
        """Filter questions based on query params"""
        queryset = super().get_queryset()
        
        # Filter by subject
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(subject_id=subject)
        
        # Filter by school (via subject's class's school)
        school = self.request.query_params.get('school', None)
        if school:
            queryset = queryset.filter(subject__class_model__school_id=school)
        
        # Filter by class
        class_id = self.request.query_params.get('class', None)
        if class_id:
            queryset = queryset.filter(subject__class_model_id=class_id)
        
        # Filter by difficulty
        difficulty = self.request.query_params.get('difficulty', None)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Filter by question type
        question_type = self.request.query_params.get('question_type', None)
        if question_type:
            queryset = queryset.filter(question_type=question_type)
        
        # Filter by topic
        topic = self.request.query_params.get('topic', None)
        if topic:
            queryset = queryset.filter(topic_model__name__icontains=topic)
        
        # Filter by verified status
        is_verified = self.request.query_params.get('is_verified', None)
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(question_text__icontains=search) |
                models.Q(topic_model__name__icontains=search) |
                models.Q(subject__name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set the created_by field to current user"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get question bank statistics"""
        total_questions = Question.objects.count()
        verified_questions = Question.objects.filter(is_verified=True).count()
        
        # Count by difficulty
        difficulty_counts = Question.objects.values('difficulty').annotate(count=models.Count('id'))
        
        # Count by type
        type_counts = Question.objects.values('question_type').annotate(count=models.Count('id'))
        
        # Count topics
        total_topics = Question.objects.values('topic_model').distinct().count()
        
        # Count subjects with questions
        total_subjects = Question.objects.values('subject').distinct().count()
        
        return Response({
            'total_questions': total_questions,
            'verified_questions': verified_questions,
            'unverified_questions': total_questions - verified_questions,
            'total_topics': total_topics,
            'total_subjects': total_subjects,
            'difficulty_breakdown': {item['difficulty']: item['count'] for item in difficulty_counts},
            'type_breakdown': {item['question_type']: item['count'] for item in type_counts},
        })
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a question"""
        question = self.get_object()
        question.is_verified = True
        question.save(update_fields=['is_verified'])
        return Response({'status': 'Question verified successfully'})
    
    @action(detail=True, methods=['post'])
    def unverify(self, request, pk=None):
        """Unverify a question"""
        question = self.get_object()
        question.is_verified = False
        question.save(update_fields=['is_verified'])
        return Response({'status': 'Question unverified successfully'})


class ClubViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Club CRUD operations
    Only admin users can manage clubs
    """
    queryset = Club.objects.all().order_by('name')
    serializer_class = ClubSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter clubs by search parameter"""
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search)
            )
        
        return queryset


class ExamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Exam CRUD operations
    Only school admin users can manage exams
    """
    queryset = Exam.objects.select_related(
        'subject', 'subject__school', 'subject__class_model', 'session_term', 'created_by'
    ).all().order_by('-created_at')
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdmin]
    
    def get_queryset(self):
        """Filter exams with search and status filtering"""
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by exam type
        exam_type = self.request.query_params.get('exam_type', None)
        if exam_type:
            queryset = queryset.filter(exam_type=exam_type)
        
        # Filter by subject
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(subject=subject)
        
        # Filter by active exams only
        active_only = self.request.query_params.get('active_only', None)
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status='active')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(subject__name__icontains=search) |
                models.Q(instructions__icontains=search)
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Custom create to handle questions ManyToMany field"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Handle questions separately
        questions_data = request.data.get('questions', [])
        
        # Create the exam instance
        exam = serializer.save(created_by=request.user)
        
        # Set questions if provided
        if questions_data:
            exam.questions.set(questions_data)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    def update(self, request, *args, **kwargs):
        """Custom update to handle questions ManyToMany field"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        
        # Handle questions separately
        questions_data = request.data.get('questions', [])
        if questions_data:
            instance.questions.set(questions_data)
        
        # Update other fields
        self.perform_update(serializer)
        
        return Response(serializer.data)


# Student Exam Serializers

class StudentAnswerSerializer(serializers.ModelSerializer):
    """Serializer for StudentAnswer model"""
    
    class Meta:
        model = StudentAnswer
        fields = [
            'id', 'question', 'question_number', 'answer_text', 
            'is_correct', 'marks_obtained', 'answered_at', 'updated_at'
        ]
        read_only_fields = ['id', 'answered_at', 'updated_at']


class StudentExamSerializer(serializers.ModelSerializer):
    """Serializer for StudentExam model"""
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    exam_subject = serializers.CharField(source='exam.subject.name', read_only=True)
    
    class Meta:
        model = StudentExam
        fields = [
            'id', 'student', 'exam', 'exam_title', 'exam_subject',
            'status', 'score', 'percentage', 'passed', 'started_at', 
            'submitted_at', 'time_remaining_seconds', 'question_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'score', 'percentage', 'passed', 'created_at', 'updated_at'
        ]


class StudentExamDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for StudentExam with answers"""
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    exam_subject = serializers.CharField(source='exam.subject.name', read_only=True)
    exam_details = ExamSerializer(source='exam', read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = StudentExam
        fields = [
            'id', 'student', 'exam', 'exam_title', 'exam_subject',
            'status', 'score', 'percentage', 'passed', 'started_at', 
            'submitted_at', 'time_remaining_seconds', 'question_order',
            'created_at', 'updated_at', 'exam_details', 'answers'
        ]


# Student Exam API Views
from django.shortcuts import get_object_or_404

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_exams(request, student_id):
    """Get all exams taken by a specific student"""
    try:
        student = get_object_or_404(Student, id=student_id)
        student_exams = StudentExam.objects.filter(student=student).order_by('-submitted_at', '-created_at')
        
        serializer = StudentExamSerializer(student_exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch student exams: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_exam_detail(request, student_exam_id):
    """Get detailed exam results for a specific student exam attempt"""
    try:
        student_exam = get_object_or_404(StudentExam, id=student_exam_id)
        student_answers = StudentAnswer.objects.filter(student_exam=student_exam).order_by('question_number')
        
        # Create the detailed response
        exam_data = StudentExamDetailSerializer(student_exam).data
        exam_data['answers'] = StudentAnswerSerializer(student_answers, many=True).data
        
        return Response(exam_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch exam details: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

