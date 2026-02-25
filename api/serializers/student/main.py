from rest_framework import serializers
from api.models import Student
from django.core.files.base import ContentFile
import base64
import uuid
from .base import BioDataSerializer, GuardianSerializer, DocumentSerializer, BiometricSerializer
from .subjects import StudentSubjectSerializer

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
    passport_photo = serializers.SerializerMethodField()
    all_subjects_cleared = serializers.SerializerMethodField()
    has_staff_parent = serializers.SerializerMethodField()
    staff_parents_details = serializers.SerializerMethodField()
    recipient_emails = serializers.SerializerMethodField()
    
    # Email field for updates
    email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'application_number', 'admission_number', 'user', 'user_email', 'email',
            'school', 'school_name', 'school_type', 'class_model', 'class_name',
            'department', 'department_name', 'former_school_attended', 'club', 'club_name',
            'status', 'source', 'full_name', 'passport_photo',
            'application_date', 'review_date', 'acceptance_date',
            'enrollment_date', 'graduation_date',
            'created_by', 'reviewed_by', 'rejection_reason',
            'created_at', 'updated_at',
            # Nested data
            'biodata', 'guardians', 'documents', 'biometric', 'subject_registrations',
            'all_subjects_cleared', 'has_staff_parent', 'staff_parents_details',
            'recipient_emails'
        ]
        read_only_fields = [
            'id', 'application_number', 'admission_number', 'full_name', 'passport_photo',
            'created_at', 'updated_at', 'created_by', 'reviewed_by',
            'school_name', 'school_type', 'class_name', 'department_name', 'club_name',
            'biodata', 'guardians', 'documents', 'biometric', 'subject_registrations',
            'all_subjects_cleared'
        ]
    
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
        if email:
            if instance.user:
                instance.user.email = email
                instance.user.save()
            else:
                # Create user for student if missing
                from api.models import User
                from api.utils.email import generate_password
                password = generate_password()
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    user_type='student'
                )
                instance.user = user
                instance.save()
        
        # Handle club field separately
        club_data = validated_data.pop('club', None)
        
        if club_data:
            if hasattr(club_data, 'id'):
                validated_data['club'] = club_data
            else:
                from api.models import Club
                try:
                    club_instance = Club.objects.get(pk=club_data)
                    validated_data['club'] = club_instance
                except Club.DoesNotExist:
                    validated_data['club'] = None
        elif club_data is not None:
            validated_data['club'] = None
        
        # Handle biodata updates
        biodata_data = validated_data.pop('biodata', None)
        if biodata_data and instance.biodata:
            for attr, value in biodata_data.items():
                if attr == 'passport_photo':
                    if value == "":
                        if instance.biodata.passport_photo:
                            instance.biodata.passport_photo.delete(save=False)
                        instance.biodata.passport_photo = None
                    elif isinstance(value, str) and value.startswith('data:image'):
                        format, imgstr = value.split(';base64,')
                        ext = format.split('/')[-1]
                        passport_file = ContentFile(base64.b64decode(imgstr), name=f'student_{uuid.uuid4()}.{ext}')
                        instance.biodata.passport_photo = passport_file
                    else:
                        setattr(instance.biodata, attr, value)
                else:
                    setattr(instance.biodata, attr, value)
            instance.biodata.save()
        
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

    def get_has_staff_parent(self, obj):
        return obj.staff_parents.exists()

    def get_recipient_emails(self, obj):
        """Get best email recipients (guardians -> student fallback)"""
        from api.utils.email import get_student_recipient_emails
        return get_student_recipient_emails(obj)
    
    def get_staff_parents_details(self, obj):
        return [
            {
                'id': staff.staff_id,
                'full_name': staff.get_full_name(),
                'staff_type': staff.get_staff_type_display()
            }
            for staff in obj.staff_parents.all()
        ]

class CBTStudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for lightweight CBT student profile"""
    student_id = serializers.CharField(source='id', read_only=True)
    full_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    current_exam_seat = serializers.SerializerMethodField()
    registered_subjects = serializers.SerializerMethodField()
    passport_photo = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'student_id', 'admission_number', 'full_name', 'class_name',
            'school_name', 'passport_photo', 'current_exam_seat', 'registered_subjects'
        ]
        read_only_fields = fields

    def get_passport_photo(self, obj):
        try:
            if obj.biodata and obj.biodata.passport_photo:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.biodata.passport_photo.url)
                return obj.biodata.passport_photo.url
        except:
            pass
        return None

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_current_exam_seat(self, obj):
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

    def get_registered_subjects(self, obj):
        active_registrations = obj.subject_registrations.filter(
            is_active=True
        ).select_related('subject', 'session_term')
        return [
            {
                'id': reg.subject.id,
                'name': reg.subject.name,
                'code': reg.subject.code,
                'session_term': reg.session_term.term_name if reg.session_term else None
            }
            for reg in active_registrations
        ]

class StudentListSerializer(serializers.ModelSerializer):
    """Condensed serializer for student lists"""
    student_id = serializers.CharField(source='id', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    school_type = serializers.CharField(source='school.school_type', read_only=True)
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    full_name = serializers.SerializerMethodField()
    passport_photo = serializers.SerializerMethodField()
    primary_phone = serializers.SerializerMethodField()
    recipient_emails = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'application_number', 'admission_number', 'full_name',
            'school', 'school_name', 'school_type', 'class_model', 'class_name',
            'department', 'department_name', 'status', 'source',
            'passport_photo', 'primary_phone', 'recipient_emails',
            'application_date', 'enrollment_date', 'created_at'
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_primary_phone(self, obj):
        try:
            guardian = obj.guardians.filter(is_primary_contact=True).first()
            if guardian: return guardian.phone_number
            guardian = obj.guardians.first()
            if guardian: return guardian.phone_number
        except:
            pass
        return None
    
    def get_passport_photo(self, obj):
        try:
            if obj.biodata and obj.biodata.passport_photo:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.biodata.passport_photo.url)
                return obj.biodata.passport_photo.url
        except:
            pass
        return None

    def get_recipient_emails(self, obj):
        from api.utils.email import get_student_recipient_emails
        return get_student_recipient_emails(obj)
