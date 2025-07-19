# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Biodata

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'date_joined']
        read_only_fields = ['id', 'email', 'role', 'date_joined']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='invalid')

        attrs['user'] = user
        return attrs
    

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(min_length=6, write_only=True)
    confirmPassword = serializers.CharField(min_length=6, write_only=True)

    def validate(self, data):
        if data['password'] != data['confirmPassword']:
            raise ValidationError({"confirmPassword": "Passwords do not match."})

        if User.objects.filter(email__iexact=data['email']).exists():
            raise ValidationError({"email": "This email is already in use."})

        return data
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['email'] = instance.email
        return data
    
class BiodataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biodata
        fields = '__all__'
        read_only_fields = ['user']