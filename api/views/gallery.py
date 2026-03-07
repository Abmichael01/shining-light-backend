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
        queryset = super().get_queryset()
        school_id = self.request.query_params.get('school', None)
        
        user = self.request.user
        # If not superuser, strictly scope to the staff's school
        if not getattr(user, 'is_superuser', False) and hasattr(user, 'staff_profile') and user.staff_profile.school:
            queryset = queryset.filter(school=user.staff_profile.school)
        elif school_id:
            queryset = queryset.filter(school_id=school_id)
            
        return queryset

    def perform_create(self, serializer):
        # Automatically set school if not provided and user is staff
        user = self.request.user
        if not serializer.validated_data.get('school') and hasattr(user, 'staff_profile') and user.staff_profile.school:
            serializer.save(school=user.staff_profile.school)
        else:
            serializer.save()

class GalleryImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing gallery images with group and school scoping"""
    queryset = GalleryImage.objects.all()
    serializer_class = GalleryImageSerializer
    permission_classes = [IsAdminOrStaff]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        group_id = self.request.query_params.get('group', None)
        
        user = self.request.user
        # Scoping logic
        if not getattr(user, 'is_superuser', False) and hasattr(user, 'staff_profile') and user.staff_profile.school:
            queryset = queryset.filter(group__school=user.staff_profile.school)
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
            
        return queryset
