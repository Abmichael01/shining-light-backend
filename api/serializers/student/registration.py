from rest_framework import serializers
from django.core.files.base import ContentFile
import base64
import uuid
from api.models import Student, BioData, Guardian

class StudentRegistrationSerializer(serializers.Serializer):
    """Serializer for complete student registration (admin creates student)"""
    
    admission_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    school = serializers.CharField()  
    class_model = serializers.CharField()  
    department = serializers.IntegerField(required=False, allow_null=True)
    former_school_attended = serializers.CharField(required=False, allow_blank=True)
    club = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source = serializers.ChoiceField(choices=['online_application', 'admin_registration'], default='admin_registration')
    
    surname = serializers.CharField()
    first_name = serializers.CharField()
    other_names = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=['male', 'female'])
    date_of_birth = serializers.DateField()
    passport_photo = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField()
    state_of_origin = serializers.CharField()
    permanent_address = serializers.CharField()
    lin = serializers.CharField(required=False, allow_blank=True)
    has_medical_condition = serializers.BooleanField(default=False)
    medical_condition_details = serializers.CharField(required=False, allow_blank=True)
    blood_group = serializers.CharField(required=False, allow_blank=True)
    
    guardians = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        from api.models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value
    
    def validate(self, data):
        guardians = data.get('guardians', [])
        if not guardians:
            raise serializers.ValidationError({'guardians': 'At least one parent/guardian is required'})
        return data
    
    def create(self, validated_data):
        from django.db import transaction
        from api.models import User, School, Class, Department, Club
        from api.utils.email import generate_password, send_student_registration_email
        
        with transaction.atomic():
            guardians_data = validated_data.pop('guardians', [])
            email = validated_data.pop('email')
            password = generate_password()
            
            biodata_fields = [
                'surname', 'first_name', 'other_names', 'gender', 'date_of_birth',
                'passport_photo', 'nationality', 'state_of_origin', 'permanent_address', 'lin',
                'has_medical_condition', 'medical_condition_details', 'blood_group'
            ]
            biodata_data = {key: validated_data.pop(key, '') for key in biodata_fields if key in validated_data}
            
            club_id = validated_data.pop('club', None)
            club_instance = None
            if club_id:
                try:
                    club_instance = Club.objects.get(pk=club_id)
                except Club.DoesNotExist:
                    club_instance = None
            
            passport_photo_data = biodata_data.get('passport_photo', None)
            if passport_photo_data and isinstance(passport_photo_data, str) and passport_photo_data.startswith('data:image'):
                format, imgstr = passport_photo_data.split(';base64,')
                ext = format.split('/')[-1]
                biodata_data['passport_photo'] = ContentFile(base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}')
            
            request_user = self.context.get('request').user if self.context.get('request') else None
            
            school_code = validated_data.pop('school')
            class_code = validated_data.pop('class_model')
            department_id = validated_data.pop('department', None)
            
            school = School.objects.get(pk=school_code)
            class_model = Class.objects.get(pk=class_code)
            department = Department.objects.get(pk=department_id) if department_id else None
            
            user = User.objects.create_user(email=email, password=password, user_type='student')
            
            student = Student.objects.create(
                user=user, school=school, class_model=class_model,
                department=department, club=club_instance, created_by=request_user,
                status='applicant', **validated_data
            )
            
            BioData.objects.create(student=student, **biodata_data)
            
            if student.source == 'admin_registration':
                student.status = 'enrolled'
                student.enrollment_date = student.application_date
                student.acceptance_date = student.application_date
                student.save()
            
            for g_data in guardians_data:
                Guardian.objects.create(student=student, **g_data)
            
            request = self.context.get('request')
            send_student_registration_email(student, password, request)
            
            return student
