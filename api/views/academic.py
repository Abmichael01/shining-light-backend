from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject, Topic, Grade, Question
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
    QuestionListSerializer
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
            queryset = queryset.filter(topic__icontains=topic)
        
        # Filter by verified status
        is_verified = self.request.query_params.get('is_verified', None)
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(question_text__icontains=search) |
                models.Q(topic__icontains=search) |
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
        total_topics = Question.objects.values('topic').distinct().count()
        
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

