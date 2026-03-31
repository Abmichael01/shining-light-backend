from rest_framework import viewsets
from api.models import Grade
from api.serializers import GradeSerializer
from api.permissions import IsSchoolAdminOrReadOnly

class GradeViewSet(viewsets.ModelViewSet):
    """ViewSet for Grade CRUD operations"""
    queryset = Grade.objects.all().order_by("order")
    serializer_class = GradeSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
