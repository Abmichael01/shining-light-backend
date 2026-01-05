"""
Serializers for the admission portal
Handles applicant registration, authentication, and application management
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from api.models import (
    Student,
    BioData,
    Guardian,
    Document,
    ApplicationSlip,
    AdmissionSettings,
    PaymentPurpose,
    FeePayment,
    School,
    Class
)
from api.models.user import User
from api.serializers.student import BioDataSerializer, GuardianSerializer, DocumentSerializer


class AdmissionSettingsSerializer(serializers.ModelSerializer):
    """Serializer for AdmissionSettings model"""
    
    school_name = serializers.CharField(source='school.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = AdmissionSettings
        fields = [
            'id', 'school', 'school_name', 'is_admission_open',
            'admission_start_datetime', 'admission_end_datetime',
            'application_fee_amount', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'school_name','created_by_name']
    
    def validate(self, attrs):
        """Validate admission settings"""
        if attrs.get('is_admission_open'):
            if not attrs.get('admission_start_datetime') or not attrs.get('admission_end_datetime'):
                raise serializers.ValidationError(
                    "Start and end datetime are required when admission is open"
                )
            
            if attrs.get('admission_end_datetime') <= attrs.get('admission_start_datetime'):
                raise serializers.ValidationError(
                    "End datetime must be after start datetime"
                )
        
        return attrs


class EmailOtpRequestSerializer(serializers.Serializer):
    """Serializer for requesting OTP"""
    email = serializers.EmailField(required=True)
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), required=True)
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered. Please login instead.")
        return value.lower()


class OtpRegistrationSerializer(serializers.Serializer):
    """Serializer for verifying OTP and Registering"""
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), required=True)
    class_applying_for = serializers.PrimaryKeyRelatedField(queryset=Class.objects.all(), required=True)
    
    def validate(self, attrs):
        # Additional validation (school open etc) can go here
        return attrs


class ApplicantRegistrationSerializer(serializers.Serializer):
    """(Legacy) Serializer for initial applicant registration (email only)"""
    
    email = serializers.EmailField(required=True)
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all(), required=True)
    class_applying_for = serializers.PrimaryKeyRelatedField(queryset=Class.objects.all(), required=True)
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered")
        return value.lower()
    
    def validate(self, attrs):
        """Validate that admission is open for the selected school"""
        school = attrs.get('school')
        
        try:
            settings = AdmissionSettings.objects.filter(school=school).first()
            if not settings:
                raise serializers.ValidationError(
                    "Admission settings not configured for this school"
                )
            
            if not settings.is_admission_open:
                raise serializers.ValidationError(
                    "Admission is currently closed for this school"
                )
        except Exception:
             raise serializers.ValidationError(
                "Admission settings not configured for this school"
            )
        
        return attrs


class ApplicantLoginSerializer(serializers.Serializer):
    """Serializer for applicant login"""
    
    username = serializers.CharField(
        required=True,
        help_text="Email or Application Number"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class ApplicantChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing applicant password"""
    
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    confirm_new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_new_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Validate that new passwords match"""
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({
                'confirm_new_password': "New passwords do not match"
            })
        return attrs


class ApplicationChecklistSerializer(serializers.Serializer):
    """Serializer for application checklist status"""
    
    biodata_complete = serializers.BooleanField(default=False)
    guardians_complete = serializers.BooleanField(default=False)
    documents_complete = serializers.BooleanField(default=False)
    payment_complete = serializers.BooleanField(default=False)
    
    @property
    def is_complete(self):
        """Check if all checklist items are complete"""
        return all([
            self.validated_data.get('biodata_complete', False),
            self.validated_data.get('guardians_complete', False),
            self.validated_data.get('documents_complete', False),
            self.validated_data.get('payment_complete', False)
        ])


class ApplicantDashboardSerializer(serializers.ModelSerializer):
    """Serializer for applicant dashboard data"""
    
    checklist = serializers.SerializerMethodField()
    biodata = BioDataSerializer(read_only=True)
    guardians = GuardianSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'application_number', 'seat_number', 'status',
            'school', 'school_name', 'class_model', 'class_name',
            'application_date', 'application_submitted_at',
            'checklist', 'biodata', 'guardians', 'documents'
        ]
        read_only_fields = fields
    
    def get_checklist(self, obj):
        """Get application checklist status"""
        checklist = obj.application_checklist or {}
        return {
            'biodata_complete': checklist.get('biodata_complete', False),
            'guardians_complete': checklist.get('guardians_complete', False),
            'documents_complete': checklist.get('documents_complete', False),
            'payment_complete': checklist.get('payment_complete', False),
            'is_complete': all([
                checklist.get('biodata_complete', False),
                checklist.get('guardians_complete', False),
                checklist.get('documents_complete', False),
                checklist.get('payment_complete', False)
            ])
        }


class ApplicationSubmissionSerializer(serializers.Serializer):
    """Serializer for final application submission"""
    
    seat_number = serializers.CharField(read_only=True)
    application_number = serializers.CharField(read_only=True)
    application_slip_url = serializers.URLField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)


class ApplicationSlipSerializer(serializers.ModelSerializer):
    """Serializer for ApplicationSlip model"""
    
    student_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='student.school.name', read_only=True)
    class_name = serializers.CharField(source='student.class_model.name', read_only=True)
    
    class Meta:
        model = ApplicationSlip
        fields = [
            'id', 'student', 'student_name', 'school_name', 'class_name',
            'application_number', 'screening_date', 'pdf_file', 'generated_at'
        ]
        read_only_fields = fields
    
    def get_student_name(self, obj):
        """Get student full name from biodata"""
        return obj.student.get_full_name()


class PaymentPurposeSerializer(serializers.ModelSerializer):
    """Serializer for PaymentPurpose model"""
    
    class Meta:
        model = PaymentPurpose
        fields = ['id', 'name', 'code', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for checking payment status"""
    
    has_paid = serializers.BooleanField(read_only=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    required_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    payment_date = serializers.DateTimeField(read_only=True, required=False)
    receipt_number = serializers.CharField(read_only=True, required=False)
