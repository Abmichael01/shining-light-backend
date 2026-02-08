from rest_framework import serializers
from ..models import BiometricStation

class BiometricStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricStation
        fields = ['id', 'name', 'api_key', 'location', 'is_active', 'last_seen', 'created_at']
        read_only_fields = ['api_key', 'last_seen', 'created_at']
