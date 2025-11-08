"""
Serializers for staff-related models
"""
from rest_framework import serializers
from api.models import (
    Staff,
    StaffEducation,
    SalaryGrade,
    StaffSalary,
    SalaryPayment,
    LoanApplication,
    LoanPayment,
    User
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
import base64
import uuid


class StaffEducationSerializer(serializers.ModelSerializer):
    """Serializer for StaffEducation model"""
    
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    degree_display = serializers.CharField(source='get_degree_display', read_only=True)
    
    class Meta:
        model = StaffEducation
        fields = [
            'id',
            'staff',
            'level',
            'level_display',
            'institution_name',
            'year_of_graduation',
            'degree',
            'degree_display',
            'certificate',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'staff', 'created_at', 'updated_at']


class StaffListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing staff"""
    
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    assigned_class_name = serializers.CharField(source='assigned_class.name', read_only=True, allow_null=True)
    staff_type_display = serializers.CharField(source='get_staff_type_display', read_only=True)
    zone_display = serializers.CharField(source='get_zone_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    id = serializers.CharField(source='staff_id', read_only=True)
    
    class Meta:
        model = Staff
        fields = [
            'id',
            'staff_id',
            'full_name',
            'email',
            'phone_number',
            'staff_type',
            'staff_type_display',
            'assigned_class_name',
            'zone_display',
            'status_display',
            'entry_date',
            'created_at'
        ]
    
    def get_full_name(self, obj):
        """Return staff member's full name"""
        return obj.get_full_name()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        passport_field = getattr(instance, 'passport_photo', None)
        if passport_field:
            if hasattr(passport_field, 'url'):
                request = self.context.get('request') if hasattr(self, 'context') else None
                url = passport_field.url
                if request:
                    url = request.build_absolute_uri(url)
                data['passport_photo'] = url
            else:
                data['passport_photo'] = passport_field
        else:
            data['passport_photo'] = None
        return data


class StaffSerializer(serializers.ModelSerializer):
    """Full serializer for Staff model"""
    
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    assigned_class_name = serializers.CharField(source='assigned_class.name', read_only=True, allow_null=True)
    title_display = serializers.CharField(source='get_title_display', read_only=True)
    staff_type_display = serializers.CharField(source='get_staff_type_display', read_only=True)
    zone_display = serializers.CharField(source='get_zone_display', read_only=True)
    marital_status_display = serializers.CharField(source='get_marital_status_display', read_only=True)
    religion_display = serializers.CharField(source='get_religion_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    education_records = StaffEducationSerializer(many=True, read_only=True)
    id = serializers.CharField(source='staff_id', read_only=True)
    passport_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Staff
        fields = [
            'id',
            'staff_id',
            'user',
            'title',
            'title_display',
            'surname',
            'first_name',
            'other_names',
            'full_name',
            'email',
            'nationality',
            'state_of_origin',
            'date_of_birth',
            'permanent_address',
            'phone_number',
            'marital_status',
            'marital_status_display',
            'religion',
            'religion_display',
            'entry_date',
            'staff_type',
            'staff_type_display',
            'zone',
            'zone_display',
            'assigned_class',
            'assigned_class_name',
            'number_of_children_in_school',
            'account_name',
            'account_number',
            'bank_name',
            'passport_photo',
            'status',
            'status_display',
            'education_records',
            'created_at',
            'updated_at',
            'created_by'
        ]
        read_only_fields = ['id', 'staff_id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        """Return staff member's full name"""
        return obj.get_full_name()

    def update(self, instance, validated_data):
        passport_photo_data = validated_data.pop('passport_photo', None)

        if passport_photo_data is not None:
            if passport_photo_data == "":
                if instance.passport_photo:
                    instance.passport_photo.delete(save=False)
                instance.passport_photo = None
            elif isinstance(passport_photo_data, str) and passport_photo_data.startswith('data:image'):
                format, imgstr = passport_photo_data.split(';base64,')
                ext = format.split('/')[-1]
                passport_file = ContentFile(base64.b64decode(imgstr), name=f'staff_{uuid.uuid4()}.{ext}')
                instance.passport_photo = passport_file
            else:
                # For actual InMemoryUploadedFile or similar, assign directly
                instance.passport_photo = passport_photo_data

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        passport_field = getattr(instance, 'passport_photo', None)
        if passport_field:
            if hasattr(passport_field, 'url'):
                request = self.context.get('request') if hasattr(self, 'context') else None
                url = passport_field.url
                if request:
                    url = request.build_absolute_uri(url)
                data['passport_photo'] = url
            else:
                data['passport_photo'] = passport_field
        else:
            data['passport_photo'] = None
        return data


class StaffPortalUpdateSerializer(serializers.ModelSerializer):
    """Serializer for staff self-service updates"""

    passport_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Staff
        fields = [
            'title',
            'surname',
            'first_name',
            'other_names',
            'phone_number',
            'permanent_address',
            'marital_status',
            'religion',
            'number_of_children_in_school',
            'account_name',
            'account_number',
            'bank_name',
            'passport_photo'
        ]

    def update(self, instance, validated_data):
        passport_photo_data = validated_data.pop('passport_photo', None)

        if passport_photo_data is not None:
            # Handle clearing
            if passport_photo_data == "":
                if instance.passport_photo:
                    instance.passport_photo.delete(save=False)
                instance.passport_photo = None
            elif isinstance(passport_photo_data, str) and passport_photo_data.startswith('data:image'):
                format, imgstr = passport_photo_data.split(';base64,')
                ext = format.split('/')[-1]
                passport_file = ContentFile(base64.b64decode(imgstr), name=f'staff_{uuid.uuid4()}.{ext}')
                instance.passport_photo = passport_file

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class StaffRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for staff registration with user creation"""
    
    # User credentials
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    
    # Override passport_photo to accept string (base64) instead of file
    passport_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Education records (nested)
    education_records = StaffEducationSerializer(many=True, required=False)
    id = serializers.CharField(source='staff_id', read_only=True)
    id = serializers.CharField(source='staff_id', read_only=True)
    
    class Meta:
        model = Staff
        fields = [
            'id',
            'staff_id',
            'email',
            'password',
            'title',
            'surname',
            'first_name',
            'other_names',
            'nationality',
            'state_of_origin',
            'date_of_birth',
            'permanent_address',
            'phone_number',
            'marital_status',
            'religion',
            'entry_date',
            'staff_type',
            'zone',
            'assigned_class',
            'number_of_children_in_school',
            'account_name',
            'account_number',
            'bank_name',
            'passport_photo',
            'status',
            'education_records',
            'created_at'
        ]
        read_only_fields = ['id', 'staff_id', 'created_at']
        extra_kwargs = {
            'passport_photo': {'required': False, 'allow_null': True}
        }
    
    def validate(self, data):
        """Validate staff registration data"""
        # Check if user with email already exists
        email = data.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'A user with this email already exists.'
            })
        return data
    
    def create(self, validated_data):
        """Create staff with user account and education records"""
        # Print filtered data without base64
        filtered_data = {}
        for key, value in validated_data.items():
            if key in ['passport_photo'] or (isinstance(value, str) and value.startswith('data:')):
                filtered_data[key] = f"[BASE64_DATA_{len(str(value))}_chars]"
            else:
                filtered_data[key] = value
        print(f"StaffRegistrationSerializer.create called with data: {filtered_data}")
        
        # Extract user data
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        education_records_data = validated_data.pop('education_records', [])
        
        print(f"Education records count: {len(education_records_data)}")
        
        # Handle base64 passport photo
        passport_photo_data = validated_data.pop('passport_photo', None)
        print(f"Passport photo data type: {type(passport_photo_data)}")
        
        if passport_photo_data and isinstance(passport_photo_data, str) and passport_photo_data.startswith('data:image'):
            # Extract base64 data
            format, imgstr = passport_photo_data.split(';base64,')
            ext = format.split('/')[-1]
            # Create file from base64
            passport_file = ContentFile(base64.b64decode(imgstr), name=f'staff_{uuid.uuid4()}.{ext}')
            validated_data['passport_photo'] = passport_file
            print(f"Created passport file: {passport_file}")
        elif passport_photo_data and isinstance(passport_photo_data, str):
            # If it's a string but not base64, skip it
            print(f"Skipping non-base64 passport photo data")
        else:
            # If it's None or empty, skip it
            print(f"No passport photo data provided")
        
        # Get the requesting user for created_by
        request = self.context.get('request')
        created_by = request.user if request else None
        
        # Create user account
        user = User.objects.create_user(
            email=email,
            password=password,
            user_type='staff'
        )
        print(f"Created user: {user}")
        
        # Create staff profile
        staff = Staff.objects.create(
            user=user,
            created_by=created_by,
            **validated_data
        )
        print(f"Created staff: {staff}")
        
        # Create education records
        for i, edu_data in enumerate(education_records_data):
            print(f"Processing education record {i+1}: {edu_data.get('level', 'unknown')} - {edu_data.get('institution_name', 'unknown')}")
            
            # Handle base64 certificate if present
            certificate_data = edu_data.pop('certificate', None)
            if certificate_data and isinstance(certificate_data, str) and certificate_data.startswith('data:'):
                # Extract base64 data
                format, filestr = certificate_data.split(';base64,')
                ext = format.split('/')[-1]
                # Create file from base64
                certificate_file = ContentFile(base64.b64decode(filestr), name=f'cert_{uuid.uuid4()}.{ext}')
                edu_data['certificate'] = certificate_file
                print(f"Created certificate file: {certificate_file}")
            
            StaffEducation.objects.create(staff=staff, **edu_data)
            print(f"Created education record {i+1} for staff {staff.id}")
        
        return staff


class SalaryGradeSerializer(serializers.ModelSerializer):
    """Serializer for SalaryGrade model (Global salary grades)"""
    
    grade_display = serializers.CharField(source='get_grade_number_display', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = SalaryGrade
        fields = [
            'id',
            'grade_number',
            'grade_display',
            'monthly_amount',
            'description',
            'is_active',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_email'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StaffSalarySerializer(serializers.ModelSerializer):
    """Serializer for StaffSalary model"""
    
    staff_name = serializers.SerializerMethodField()
    staff_registration_number = serializers.CharField(source='staff.registration_number', read_only=True)
    grade_number = serializers.IntegerField(source='salary_grade.grade_number', read_only=True)
    monthly_amount = serializers.DecimalField(
        source='salary_grade.monthly_amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = StaffSalary
        fields = [
            'id',
            'staff',
            'staff_name',
            'staff_id',
            'salary_grade',
            'grade_number',
            'monthly_amount',
            'effective_date',
            'notes',
            'created_at',
            'updated_at',
            'assigned_by',
            'assigned_by_email'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_staff_name(self, obj):
        """Return staff member's full name"""
        return obj.staff.get_full_name()


class SalaryPaymentSerializer(serializers.ModelSerializer):
    """Serializer for SalaryPayment model"""
    
    staff_name = serializers.SerializerMethodField()
    staff_id = serializers.CharField(source='staff.staff_id', read_only=True)
    grade_number = serializers.IntegerField(source='salary_grade.grade_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processed_by_email = serializers.EmailField(source='processed_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = SalaryPayment
        fields = [
            'id',
            'staff',
            'staff_name',
            'staff_id',
            'salary_grade',
            'grade_number',
            'month',
            'year',
            'amount',
            'deductions',
            'net_amount',
            'status',
            'status_display',
            'payment_date',
            'reference_number',
            'notes',
            'created_at',
            'updated_at',
            'processed_by',
            'processed_by_email'
        ]
        read_only_fields = ['id', 'net_amount', 'created_at', 'updated_at']
    
    def get_staff_name(self, obj):
        """Return staff member's full name"""
        return obj.staff.get_full_name()


class LoanPaymentSerializer(serializers.ModelSerializer):
    """Serializer for LoanPayment model"""
    
    application_number = serializers.CharField(source='loan_application.application_number', read_only=True)
    processed_by_email = serializers.EmailField(source='processed_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = LoanPayment
        fields = [
            'id',
            'loan_application',
            'application_number',
            'amount',
            'payment_date',
            'month',
            'year',
            'reference_number',
            'notes',
            'created_at',
            'processed_by',
            'processed_by_email'
        ]
        read_only_fields = ['id', 'created_at']


class LoanApplicationSerializer(serializers.ModelSerializer):
    """Serializer for LoanApplication model"""
    
    staff_name = serializers.SerializerMethodField()
    staff_id = serializers.CharField(source='staff.staff_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()
    loan_payments = LoanPaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = LoanApplication
        fields = [
            'id',
            'application_number',
            'staff',
            'staff_name',
            'staff_id',
            'loan_amount',
            'interest_rate',
            'total_amount',
            'repayment_period_months',
            'monthly_deduction',
            'purpose',
            'status',
            'status_display',
            'application_date',
            'approval_date',
            'disbursement_date',
            'reviewed_by',
            'reviewed_by_email',
            'review_notes',
            'rejection_reason',
            'amount_paid',
            'amount_remaining',
            'loan_payments',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'application_number',
            'total_amount',
            'monthly_deduction',
            'application_date',
            'created_at',
            'updated_at'
        ]
    
    def get_staff_name(self, obj):
        """Return staff member's full name"""
        return obj.staff.get_full_name()
    
    def get_amount_paid(self, obj):
        """Return total amount paid"""
        return obj.get_amount_paid()
    
    def get_amount_remaining(self, obj):
        """Return remaining loan balance"""
        return obj.get_amount_remaining()


