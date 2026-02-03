from rest_framework import viewsets, permissions
from api.models.communication import CommunicationTemplate
from api.serializers.communication import CommunicationTemplateSerializer

class CommunicationTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for communication templates
    """
    queryset = CommunicationTemplate.objects.all()
    serializer_class = CommunicationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
