from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import models
from api.models import Student
from api.serializers import (
    StudentSerializer,
    StudentListSerializer,
    StudentRegistrationSerializer
)
from api.permissions import IsAdminOrStaff
from api.pagination import StandardResultsSetPagination

from .actions import StudentActionsMixin

class StudentViewSet(StudentActionsMixin, viewsets.ModelViewSet):
    """
    ViewSet for Student CRUD operations
    Handles both applications and enrolled students
    """
    pagination_class = StandardResultsSetPagination
    queryset = Student.objects.select_related(
        'school', 'class_model', 'department', 'club', 'user', 'biodata', 'biometric'
    ).prefetch_related(
        'guardians', 'documents', 'subject_registrations'
    ).all().order_by('-created_at')
    permission_classes = [IsAdminOrStaff]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=False, methods=['GET'], permission_classes=[IsAdminOrStaff])
    def summary(self, request):
        """Get summary statistics for filtered students"""
        base_qs = self.get_queryset()
        
        total_students = base_qs.count()
        
        from django.db.models import Count
        status_counts = dict(
            base_qs.values('status').annotate(count=Count('status')).values_list('status', 'count')
        )
        
        primary_count = base_qs.filter(
            school__school_type__in=['Nursery', 'Primary']
        ).count()
        
        secondary_count = base_qs.filter(
            school__school_type__in=['Junior Secondary', 'Senior Secondary']
        ).count()
        
        return Response({
            'total': total_students,
            'status_counts': status_counts,
            'primary': primary_count,
            'secondary': secondary_count
        })
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return StudentListSerializer
        elif self.action == 'register':
            return StudentRegistrationSerializer
        return StudentSerializer
    
    def get_queryset(self):
        """Filter students by various parameters"""
        queryset = super().get_queryset()

        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            status_list = status_filter.split(',')
            queryset = queryset.filter(status__in=status_list)

        exclude_status = self.request.query_params.get('exclude_status', None)
        if exclude_status:
            exclude_list = exclude_status.split(',')
            queryset = queryset.exclude(status__in=exclude_list)

        school = self.request.query_params.get('school', None)
        if school:
            queryset = queryset.filter(school=school)

        class_model = self.request.query_params.get('class', None)
        if class_model:
            queryset = queryset.filter(class_model=class_model)

        source = self.request.query_params.get('source', None)
        if source:
            queryset = queryset.filter(source=source)

        search = self.request.query_params.get('search', None)
        if search:
            search_terms = search.split()
            if len(search_terms) > 1:
                name_q = models.Q()
                for term in search_terms:
                    name_q &= (
                        models.Q(biodata__surname__icontains=term) |
                        models.Q(biodata__first_name__icontains=term) |
                        models.Q(biodata__other_names__icontains=term)
                    )
                queryset = queryset.filter(
                    name_q |
                    models.Q(admission_number__icontains=search) |
                    models.Q(application_number__icontains=search) |
                    models.Q(user__email__icontains=search)
                )
            else:
                queryset = queryset.filter(
                    models.Q(biodata__surname__icontains=search) |
                    models.Q(biodata__first_name__icontains=search) |
                    models.Q(biodata__other_names__icontains=search) |
                    models.Q(admission_number__icontains=search) |
                    models.Q(application_number__icontains=search) |
                    models.Q(user__email__icontains=search)
                )
        return queryset
