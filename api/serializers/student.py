from rest_framework import serializers
from api.models import Student, BioData, Guardian, Document, Biometric, StudentSubject
from django.core.files.base import ContentFile
import base64
import uuid


class BioDataSerializer(serializers.ModelSerializer):
    """Serializer for BioData model"""
    age = serializers.SerializerMethodField()
    passport_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = BioData
        fields = [
            'id', 'student', 'surname', 'first_name', 'other_names', 'gender',
            'date_of_birth', 'age', 'passport_photo', 'nationality', 'state_of_origin', 'permanent_address',
            'lin', 'has_medical_condition', 'medical_condition_details', 'blood_group',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'age']
    
    def get_age(self, obj):
        """Calculate and return age"""
        return obj.get_age()
    
    def get_passport_photo(self, obj):
        """Return full URL for passport photo"""
        if obj.passport_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.passport_photo.url)
            return obj.passport_photo.url
        return None
    


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
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name']
    
    def get_full_name(self, obj):
        """Return full name"""
        return f"{obj.surname} {obj.first_name}"


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    verified_by_name = serializers.CharField(source='verified_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'student', 'document_type', 'document_file', 'document_number',
            'verified', 'verified_by', 'verified_by_name', 'verified_at', 'notes',
            'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'updated_at', 'verified_by', 'verified_at', 'verified_by_name']


class BiometricSerializer(serializers.ModelSerializer):
    """Serializer for Biometric model"""
    captured_by_name = serializers.CharField(source='captured_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Biometric
        fields = [
            'id', 'student', 'left_thumb', 'right_thumb',
            'captured_at', 'captured_by', 'captured_by_name', 'notes', 'updated_at'
        ]
        read_only_fields = ['id', 'captured_at', 'updated_at', 'captured_by', 'captured_by_name']


class StudentSubjectSerializer(serializers.ModelSerializer):
    """Serializer for StudentSubject model with results"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    subject_class_id = serializers.CharField(source='subject.class_model_id', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    term_name = serializers.CharField(source='session_term.term_name', read_only=True, allow_null=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True, allow_null=True)
    grade_description = serializers.CharField(source='grade.grade_description', read_only=True, allow_null=True)
    cleared_by_name = serializers.CharField(source='cleared_by.email', read_only=True, allow_null=True)
    openday_cleared_by_name = serializers.CharField(source='openday_cleared_by.email', read_only=True, allow_null=True)
    can_open_day_clear = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentSubject
        fields = [
            'id', 'student', 'subject', 'subject_name', 'subject_code', 'subject_class_id',
            'session', 'session_name', 'session_term', 'term_name',
            'is_active',
            'cleared', 'cleared_at', 'cleared_by', 'cleared_by_name',
            'openday_cleared', 'openday_cleared_at', 'openday_cleared_by',
            'openday_cleared_by_name', 'openday_clearance_notes', 'openday_clearance_checklist', 'can_open_day_clear',
            # Result fields
            'ca_score', 'exam_score', 'total_score', 
            'grade', 'grade_name', 'grade_description',
            'position', 'teacher_comment',
            'result_entered_by', 'result_entered_at',
            'registered_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'registered_at', 'updated_at', 'total_score',
            'subject_name', 'subject_code', 'session_name', 'term_name',
            'grade', 'grade_name', 'grade_description',
            'cleared_at', 'cleared_by', 'cleared_by_name',
            'openday_cleared_at', 'openday_cleared_by', 'openday_cleared_by_name', 'can_open_day_clear', 'subject_class_id'
        ]

    def get_can_open_day_clear(self, obj):
        """UI helper: whether current user can clear for Open Day for this subject."""
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return False
        user = request.user
        # Admins/superusers allowed
        if getattr(user, 'is_superuser', False) or getattr(user, 'user_type', '') == 'admin':
            return True
        # Staff must be assigned
        staff = getattr(user, 'staff_profile', None)
        if not staff:
            return False
        subject = obj.subject
        assigned_to_subject = subject.assigned_teachers.filter(pk=staff.pk).exists()
        assigned_class_match = bool(staff.assigned_class_id) and (staff.assigned_class_id == subject.class_model_id)
        in_class_assigned_teachers = subject.class_model.assigned_teachers.filter(pk=staff.pk).exists()
        return assigned_to_subject or assigned_class_match or in_class_assigned_teachers


class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student model with nested related data"""
    student_id = serializers.CharField(source='id', read_only=True)
    biodata = BioDataSerializer(required=False)
    guardians = GuardianSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    biometric = BiometricSerializer(read_only=True)
    subject_registrations = StudentSubjectSerializer(many=True, read_only=True)
    
    # Related names for display
    school_name = serializers.CharField(source='school.name', read_only=True)
    school_type = serializers.CharField(source='school.school_type', read_only=True)
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    club_name = serializers.CharField(source='club.name', read_only=True, allow_null=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    all_subjects_cleared = serializers.SerializerMethodField()
    
    # Email field for updates
    email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'application_number', 'admission_number', 'user', 'user_email', 'email',
            'school', 'school_name', 'school_type', 'class_model', 'class_name',
            'department', 'department_name', 'former_school_attended', 'club', 'club_name',
            'status', 'source', 'full_name',
            'application_date', 'review_date', 'acceptance_date',
            'enrollment_date', 'graduation_date',
            'created_by', 'reviewed_by', 'rejection_reason',
            'created_at', 'updated_at',
            # Nested data
            'biodata', 'guardians', 'documents', 'biometric', 'subject_registrations',
            'all_subjects_cleared'
        ]
        read_only_fields = [
            'id', 'application_number', 'admission_number', 'full_name',
            'created_at', 'updated_at', 'created_by', 'reviewed_by',
            'school_name', 'school_type', 'class_name', 'department_name', 'club_name',
            'biodata', 'guardians', 'documents', 'biometric', 'subject_registrations',
            'all_subjects_cleared'
        ]
    
    def get_full_name(self, obj):
        """Get student's full name"""
        return obj.get_full_name()
    
    def to_representation(self, instance):
        """Custom representation to ensure club field returns ID"""
        data = super().to_representation(instance)
        # Ensure club field returns the ID, not the name
        if instance.club:
            data['club'] = instance.club.id
        return data
    
    def update(self, instance, validated_data):
        """Update student instance with email and club handling"""
        # Handle email update
        email = validated_data.pop('email', None)
        if email and instance.user:
            instance.user.email = email
            instance.user.save()
        
        # Handle club field separately
        club_data = validated_data.pop('club', None)
        
        if club_data:
            # If it's already a Club instance, use it directly
            if hasattr(club_data, 'id'):
                validated_data['club'] = club_data
            else:
                # If it's a string ID, look up the club
                from api.models import Club
                try:
                    club_instance = Club.objects.get(pk=club_data)
                    validated_data['club'] = club_instance
                except Club.DoesNotExist:
                    validated_data['club'] = None
        elif club_data is not None:  # Explicitly set to None/empty
            validated_data['club'] = None
        
        # Handle biodata updates (without club field)
        biodata_data = validated_data.pop('biodata', None)
        if biodata_data and instance.biodata:
            # Update biodata fields
            for attr, value in biodata_data.items():
                setattr(instance.biodata, attr, value)
            instance.biodata.save()
        
        # Update other fields
        return super().update(instance, validated_data)
    
    def get_all_subjects_cleared(self, obj):
        prefetched = getattr(obj, '_prefetched_objects_cache', {})
        registrations = prefetched.get('subject_registrations')
        if registrations is None:
            registrations = list(obj.subject_registrations.all())
        else:
            registrations = list(registrations)
        if not registrations:
            return False
        return all(getattr(reg, 'cleared', False) for reg in registrations)


class CBTStudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for lightweight CBT student profile"""
    student_id = serializers.CharField(source='id', read_only=True)
    full_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    current_exam_seat = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'student_id',
            'admission_number',
            'full_name',
            'class_name',
            'school_name',
            'current_exam_seat'
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        """Return student's full name"""
        return obj.get_full_name()

    def get_current_exam_seat(self, obj):
        """Return latest CBT seat assignment if available"""
        latest_code = obj.cbt_exam_codes.filter(is_used=True).order_by('-used_at').first()
        if not latest_code:
            return None
        return {
            'exam_id': latest_code.exam.id if latest_code.exam else None,
            'exam_title': latest_code.exam.title if latest_code.exam else None,
            'exam_hall_id': latest_code.exam_hall.id if latest_code.exam_hall else None,
            'exam_hall_name': latest_code.exam_hall.name if latest_code.exam_hall else None,
            'seat_number': latest_code.seat_number,
            'used_at': latest_code.used_at.isoformat() if latest_code.used_at else None,
        }


class StudentListSerializer(serializers.ModelSerializer):
    """Condensed serializer for student lists"""
    student_id = serializers.CharField(source='id', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    full_name = serializers.SerializerMethodField()
    passport_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'application_number', 'admission_number', 'full_name',
            'school', 'school_name', 'class_model', 'class_name',
            'department', 'department_name', 'status', 'source',
            'passport_photo',
            'application_date', 'enrollment_date', 'created_at'
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        """Get student's full name"""
        return obj.get_full_name()
    
    def get_passport_photo(self, obj):
        """Return full URL for passport photo if available"""
        try:
            if obj.biodata and obj.biodata.passport_photo:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.biodata.passport_photo.url)
                return obj.biodata.passport_photo.url
        except:
            pass
        return None


class StudentRegistrationSerializer(serializers.Serializer):
    """Serializer for complete student registration (admin creates student)"""
    
    # Student basic info (now uses codes instead of IDs)
    admission_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    school = serializers.CharField()  # School code (e.g., "NUR-001")
    class_model = serializers.CharField()  # Class code (e.g., "SS1")
    department = serializers.IntegerField(required=False, allow_null=True)
    former_school_attended = serializers.CharField(required=False, allow_blank=True)
    club = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # Club ID
    source = serializers.ChoiceField(choices=['online_application', 'admin_registration'], default='admin_registration')
    
    # BioData
    surname = serializers.CharField()
    first_name = serializers.CharField()
    other_names = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=['male', 'female'])
    date_of_birth = serializers.DateField()
    passport_photo = serializers.CharField(required=False, allow_blank=True)  # Base64 or file URL
    nationality = serializers.CharField()
    state_of_origin = serializers.CharField()
    permanent_address = serializers.CharField()
    lin = serializers.CharField(required=False, allow_blank=True)
    has_medical_condition = serializers.BooleanField(default=False)
    medical_condition_details = serializers.CharField(required=False, allow_blank=True)
    blood_group = serializers.CharField(required=False, allow_blank=True)
    
    # Guardians (list of guardian objects)
    guardians = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    
    # Account creation (password will be auto-generated)
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate that email is unique"""
        from api.models import User
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists. Please use a different email address.')
        
        return value
    
    def validate(self, data):
        """Validate the complete registration data"""
        # Validate that at least one guardian is provided
        guardians = data.get('guardians', [])
        if not guardians:
            raise serializers.ValidationError({'guardians': 'At least one parent/guardian is required'})
        
        return data
    
    def create(self, validated_data):
        """Create student with all related data"""
        from django.db import transaction
        from api.models import User, School, Class, Department
        
        with transaction.atomic():
            # Debug logging for admission number
            print('=== STUDENT REGISTRATION DEBUG ===')
            print('Received admission_number:', validated_data.get('admission_number'))
            print('All validated_data keys:', list(validated_data.keys()))
            
            # Extract nested data
            guardians_data = validated_data.pop('guardians', [])
            email = validated_data.pop('email')
            
            # Auto-generate password
            from api.utils.email import generate_password
            password = generate_password()
            
            # Extract biodata fields
            biodata_fields = [
                'surname', 'first_name', 'other_names', 'gender', 'date_of_birth',
                'passport_photo', 'nationality', 'state_of_origin', 'permanent_address', 'lin',
                'has_medical_condition', 'medical_condition_details', 'blood_group'
            ]
            biodata_data = {key: validated_data.pop(key, '') for key in biodata_fields if key in validated_data}
            
            # Handle club field separately (convert string ID to Club instance)
            club_id = validated_data.pop('club', None)
            club_instance = None
            if club_id:
                from api.models import Club
                try:
                    club_instance = Club.objects.get(pk=club_id)
                except Club.DoesNotExist:
                    # If club doesn't exist, set to None
                    club_instance = None
            
            # Handle passport photo (base64 to file conversion)
            passport_photo_data = biodata_data.get('passport_photo', None)
            if passport_photo_data:
                if isinstance(passport_photo_data, str) and passport_photo_data.startswith('data:image'):
                    # Extract base64 data
                    format, imgstr = passport_photo_data.split(';base64,')
                    ext = format.split('/')[-1]
                    # Create file from base64
                    passport_file = ContentFile(base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}')
                    biodata_data['passport_photo'] = passport_file
                # If it's already a file URL, keep it as is
            
            # Get request user (for created_by)
            request_user = self.context.get('request').user if self.context.get('request') else None
            
            # Get model instances from codes (school and class now use codes as PKs)
            school_code = validated_data.pop('school')
            class_code = validated_data.pop('class_model')
            department_id = validated_data.pop('department', None)
            
            # Fetch actual model instances
            school = School.objects.get(pk=school_code)  # PK is now the school code
            class_model = Class.objects.get(pk=class_code)  # PK is now the class code
            department = Department.objects.get(pk=department_id) if department_id else None
            
            # Create User account
            user = User.objects.create_user(
                email=email,
                password=password,
                user_type='student'
            )
            
            # Create Student with model instances (initially as applicant to avoid admission number generation)
            student = Student.objects.create(
                user=user,
                school=school,
                class_model=class_model,
                department=department,
                club=club_instance,
                created_by=request_user,
                status='applicant',  # Start as applicant to avoid admission number generation
                **validated_data
            )
            
            # Create BioData
            BioData.objects.create(
                student=student,
                **biodata_data
            )
            
            # For admin registration, automatically enroll the student
            if student.source == 'admin_registration':
                student.status = 'enrolled'
                student.enrollment_date = student.application_date
                student.acceptance_date = student.application_date
                student.save()  # This will now generate admission number since biodata exists
            
            # Create Guardians
            for guardian_data in guardians_data:
                Guardian.objects.create(
                    student=student,
                    **guardian_data
                )
            
            # Send registration email with credentials
            from api.utils.email import send_student_registration_email
            request = self.context.get('request')
            email_sent = send_student_registration_email(student, password, request)
            
            if not email_sent:
                # Log the password to console in development if email fails
                print(f"⚠️  EMAIL FAILED - Student: {student.admission_number}, Email: {email}, Password: {password}")
            
            return student


