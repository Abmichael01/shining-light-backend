from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject
from api.serializers import (
    SchoolSerializer, 
    SessionSerializer, 
    SessionTermSerializer,
    ClassSerializer,
    DepartmentSerializer,
    SubjectGroupSerializer,
    SubjectSerializer
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
        
        # Filter by core/trade
        is_core = self.request.query_params.get('is_core', None)
        if is_core is not None:
            queryset = queryset.filter(is_core=is_core.lower() == 'true')
        
        is_trade = self.request.query_params.get('is_trade', None)
        if is_trade is not None:
            queryset = queryset.filter(is_trade=is_trade.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )
        
        return queryset

