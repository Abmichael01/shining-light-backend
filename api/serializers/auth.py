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
    Allows authentication using email, application number, or admission number
    """
    
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True, 
        write_only=True, 
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # The custom MultiFieldModelBackend will handle looking up the user
            # by email, application_number, or admission_number
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
            
            if not user.is_active:
                msg = _('User account is disabled.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')
        
        # This is required by dj-rest-auth
        attrs['user'] = user
        return attrs

