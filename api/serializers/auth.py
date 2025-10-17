from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from api.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - returns user details"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'user_type', 'is_active', 'date_joined']
        read_only_fields = ['id', 'email', 'user_type', 'date_joined']


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login requests - compatible with dj-rest-auth
    Uses email instead of username for authentication
    """
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, 
        write_only=True, 
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Authenticate using email as username (our User model uses email)
            user = authenticate(
                request=self.context.get('request'),
                username=email,  # Django expects 'username' but our model uses email
                password=password
            )
            
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
            
            if not user.is_active:
                msg = _('User account is disabled.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')
        
        # This is required by dj-rest-auth
        attrs['user'] = user
        return attrs

