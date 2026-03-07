from rest_framework import viewsets, status
from rest_framework.response import Response
from api.models.academic.gallery import GalleryGroup, GalleryImage
from api.serializers.gallery import GalleryGroupSerializer, GalleryGroupDetailSerializer, GalleryImageSerializer
from api.permissions import IsAdminOrStaff

class GalleryGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for managing gallery groups with school-based scoping"""
    queryset = GalleryGroup.objects.all().prefetch_related('images')
    permission_classes = [IsAdminOrStaff]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GalleryGroupDetailSerializer
        return GalleryGroupSerializer

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save()

class GalleryImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing gallery images with group and school scoping"""
    queryset = GalleryImage.objects.all()
    serializer_class = GalleryImageSerializer
    permission_classes = [IsAdminOrStaff]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        group_id = self.request.query_params.get('group', None)
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
            
        return queryset
