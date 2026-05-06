from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from dj_rest_auth.serializers import PasswordResetSerializer
from api.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - returns user details"""
    full_name = serializers.SerializerMethodField()
    student_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'user_type', 'is_active', 'date_joined', 'full_name', 'student_profile']
        read_only_fields = ['id', 'email', 'user_type', 'date_joined']

    def get_full_name(self, obj):
        if hasattr(obj, 'student_profile') and obj.student_profile:
            return obj.student_profile.get_full_name()
        if obj.is_superuser or obj.user_type == 'admin':
            return "Administrator"
        return obj.email

    def get_student_profile(self, obj):
        if hasattr(obj, 'student_profile') and obj.student_profile:
            return {
                'id': obj.student_profile.id,
                'status': obj.student_profile.status,
                'application_number': obj.student_profile.application_number,
                'admission_number': obj.student_profile.admission_number,
            }
        return None


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


class CustomPasswordResetSerializer(PasswordResetSerializer):
    """
    Custom password reset serializer that uses our frontend URL
    and a custom email template.
    """
    def get_email_options(self):
        """
        Override to provide custom template and context
        """
        return {
            'email_template_name': 'registration/password_reset_email.html',
            'extra_email_context': {
                'frontend_url': settings.FRONTEND_URL
            }
        }
