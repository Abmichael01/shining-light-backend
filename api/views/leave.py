from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from api.models.leave import LeaveRequest
from api.models.user import User
from api.serializers.leave import LeaveRequestSerializer

class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for calculating Leave Requests.
    - Students/Staff: See own requests, create requests.
    - Admin: See all, approve/reject.
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return LeaveRequest.objects.all()
        return LeaveRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        target_user = user
        
        # Admin can create on behalf of others
        if user.user_type == 'admin' and 'user_id' in self.request.data:
            try:
                target_user = User.objects.get(id=self.request.data['user_id'])
            except User.DoesNotExist:
                # If target user not found, fallback to admin (or raise error, but fallback safe for now)
                pass
                
        serializer.save(user=target_user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        leave = self.get_object()
        leave.status = 'approved'
        leave.responded_by = request.user
        leave.responded_at = timezone.now()
        leave.response_note = request.data.get('note', '')
        leave.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        leave = self.get_object()
        leave.status = 'rejected'
        leave.responded_by = request.user
        leave.responded_at = timezone.now()
        leave.response_note = request.data.get('note', '')
        leave.save()
        return Response({'status': 'rejected'})
