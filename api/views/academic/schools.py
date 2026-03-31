from django.db import models
from rest_framework import viewsets
from api.models import School, Club
from api.serializers import SchoolSerializer, ClubSerializer
from api.permissions import IsSchoolAdminOrReadOnly
from rest_framework.permissions import IsAuthenticated

class SchoolViewSet(viewsets.ModelViewSet):
    """
    ViewSet for School CRUD operations
    Only admin users can manage schools
    """
    queryset = School.objects.all().order_by("school_type", "name")
    serializer_class = SchoolSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        """Filter schools - can add filters here if needed"""
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | models.Q(code__icontains=search)
            )
        return queryset


class ClubViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Club CRUD operations
    Only admin users can manage clubs
    """
    queryset = Club.objects.all().order_by("name")
    serializer_class = ClubSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        """Filter clubs by search parameter"""
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", None)

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )
        return queryset
