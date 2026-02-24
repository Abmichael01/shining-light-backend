from rest_framework import viewsets, permissions
from rest_framework.response import Response
from api.models import SystemSetting
from api.serializers import SystemSettingSerializer
from api.permissions import IsAdminOrStaff

class SystemSettingViewSet(viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAdminOrStaff()]

    def list(self, request, *args, **kwargs):
        settings = SystemSetting.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        settings = SystemSetting.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        settings = SystemSetting.load()
        serializer = self.get_serializer(settings, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        settings = SystemSetting.load()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_object(self):
        return SystemSetting.load()
