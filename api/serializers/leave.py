from rest_framework import serializers
from api.models.leave import LeaveRequest
from api.serializers.auth import UserSerializer

class LeaveRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for Leave Requests
    Includes computed fields for user identification (who requested)
    """
    requester_name = serializers.SerializerMethodField()
    requester_role = serializers.SerializerMethodField()
    responder_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user', 'start_date', 'end_date', 'reason',
            'status', 'response_note', 'responded_by', 'responded_at',
            'created_at', 'updated_at',
            'requester_name', 'requester_role', 'responder_name'
        ]
        read_only_fields = ['status', 'response_note', 'responded_by', 'responded_at', 'created_at', 'updated_at', 'user']

    def get_requester_name(self, obj):
        user = obj.user
        # Try staff profile first
        if hasattr(user, 'staff_profile'):
            return user.staff_profile.get_full_name()
        # Then student profile
        if hasattr(user, 'student_profile'):
            s = user.student_profile
            # Handle student name construction
            if hasattr(s, 'biodata') and s.biodata:
                return f"{s.biodata.surname} {s.biodata.first_name}"
            # Or direct fields if flattened
            fullname = getattr(s, 'full_name', None)
            if fullname: return fullname
        # Fallback to email
        return user.email

    def get_requester_role(self, obj):
        return obj.user.user_type # 'staff', 'student'

    def get_responder_name(self, obj):
        if obj.responded_by:
            return obj.responded_by.email # OR fetch staff profile if admin is staff
        return None

    def create(self, validated_data):
        # Auto-set user from context
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)
