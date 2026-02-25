from rest_framework import serializers
from api.models import BioData, Guardian, Document, Biometric, TermReport
from django.core.files.base import ContentFile
import base64
import uuid

class BioDataSerializer(serializers.ModelSerializer):
    """Serializer for BioData model"""
    age = serializers.SerializerMethodField()
    passport_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = BioData
        fields = [
            'id', 'student', 'surname', 'first_name', 'other_names', 'gender',
            'date_of_birth', 'age', 'passport_photo', 'nationality', 'state_of_origin', 'permanent_address',
            'lin', 'has_medical_condition', 'medical_condition_details', 'blood_group',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'age', 'student']
    
    def get_age(self, obj):
        """Calculate and return age"""
        return obj.get_age()
    
    def to_representation(self, instance):
        """Convert passport_photo FileField to full URL"""
        data = super().to_representation(instance)
        passport_field = getattr(instance, 'passport_photo', None)
        if passport_field:
            if hasattr(passport_field, 'url'):
                request = self.context.get('request')
                if request:
                    data['passport_photo'] = request.build_absolute_uri(passport_field.url)
                else:
                    data['passport_photo'] = passport_field.url
            else:
                data['passport_photo'] = str(passport_field) if passport_field else None
        else:
            data['passport_photo'] = None
        return data

class GuardianSerializer(serializers.ModelSerializer):
    """Serializer for Guardian model"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Guardian
        fields = [
            'id', 'student', 'guardian_type', 'relationship_to_student',
            'surname', 'first_name', 'full_name', 'state_of_origin',
            'phone_number', 'email', 'occupation', 'place_of_employment',
            'is_primary_contact', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name', 'student']
    
    def get_full_name(self, obj):
        """Return full name"""
        return f"{obj.surname} {obj.first_name}"

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    verified_by_name = serializers.CharField(source='verified_by.email', read_only=True, allow_null=True)
    document_file = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'student', 'document_type', 'document_file', 'document_number',
            'verified', 'verified_by', 'verified_by_name', 'verified_at', 'notes',
            'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'updated_at', 'verified_by', 'verified_at', 'verified_by_name', 'student']

    def create(self, validated_data):
        return self._save_with_base64(None, validated_data)

    def update(self, instance, validated_data):
        return self._save_with_base64(instance, validated_data)

    def _save_with_base64(self, instance, validated_data):
        file_data = validated_data.pop('document_file', None)
        
        if file_data:
            if isinstance(file_data, str) and file_data.startswith('data:'):
                try:
                    format, filestr = file_data.split(';base64,')
                    ext = format.split('/')[-1]
                    if ext == 'plain': # Fix for some data URLs
                        ext = 'txt'
                    validated_data['document_file'] = ContentFile(base64.b64decode(filestr), name=f'doc_{uuid.uuid4()}.{ext}')
                except Exception:
                    pass
        elif file_data == "":
            validated_data['document_file'] = None
        
        if instance:
            return super().update(instance, validated_data)
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        file_field = getattr(instance, 'document_file', None)
        if file_field and hasattr(file_field, 'url'):
            request = self.context.get('request')
            if request:
                data['document_file'] = request.build_absolute_uri(file_field.url)
            else:
                data['document_file'] = file_field.url
        return data

class BiometricSerializer(serializers.ModelSerializer):
    """Serializer for Biometric model"""
    captured_by_name = serializers.CharField(source='captured_by.email', read_only=True, allow_null=True)
    left_thumb = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    left_index = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    right_thumb = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    right_index = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Biometric
        fields = [
            'id', 'student', 
            'left_thumb', 'left_index', 'right_thumb', 'right_index',
            'left_thumb_template', 'left_index_template', 'right_thumb_template', 'right_index_template',
            'captured_at', 'captured_by', 'captured_by_name', 'notes', 'updated_at'
        ]
        read_only_fields = [
            'id', 'captured_at', 'updated_at', 'captured_by', 'captured_by_name',
            'left_thumb_template', 'left_index_template', 'right_thumb_template', 'right_index_template'
        ]

    def create(self, validated_data):
        return self._save_with_base64(None, validated_data)

    def update(self, instance, validated_data):
        return self._save_with_base64(instance, validated_data)

    def _save_with_base64(self, instance, validated_data):
        for field in ['left_thumb', 'left_index', 'right_thumb', 'right_index']:
            file_data = validated_data.pop(field, None)
            if file_data:
                if isinstance(file_data, str) and file_data.startswith('data:'):
                    try:
                        format, filestr = file_data.split(';base64,')
                        ext = format.split('/')[-1]
                        validated_data[field] = ContentFile(base64.b64decode(filestr), name=f'thumb_{uuid.uuid4()}.{ext}')
                    except Exception:
                        pass
            elif file_data == "":
                validated_data[field] = None
        
        if instance:
            return super().update(instance, validated_data)
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['left_thumb', 'left_index', 'right_thumb', 'right_index']:
            file_obj = getattr(instance, field, None)
            if file_obj and hasattr(file_obj, 'url'):
                request = self.context.get('request')
                if request:
                    data[field] = request.build_absolute_uri(file_obj.url)
                else:
                    data[field] = file_obj.url
        return data

class TermReportSerializer(serializers.ModelSerializer):
    """Serializer for TermReport model"""
    class Meta:
        model = TermReport
        fields = '__all__'
