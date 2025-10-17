from rest_framework import serializers
from api.models import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject


class SchoolSerializer(serializers.ModelSerializer):
    """Serializer for School model"""
    
    class Meta:
        model = School
        fields = ['id', 'name', 'school_type', 'code', 'is_active', 'created_at']
        read_only_fields = ['id', 'code', 'created_at']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    school = serializers.CharField()  # Accepts school code (string)
    
    class Meta:
        model = Class
        fields = ['id', 'name', 'class_code', 'school', 'school_name', 'class_staff', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        """Return school code instead of school object when reading"""
        data = super().to_representation(instance)
        # Ensure school field returns the code (which is now the ID)
        data['school'] = instance.school.id if instance.school else None
        return data
    
    def create(self, validated_data):
        """Handle school code to instance conversion"""
        from api.models import School
        school_code = validated_data.pop('school')
        school = School.objects.get(pk=school_code)
        validated_data['school'] = school
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Handle school code to instance conversion"""
        from api.models import School
        if 'school' in validated_data:
            school_code = validated_data.pop('school')
            validated_data['school'] = School.objects.get(pk=school_code)
        return super().update(instance, validated_data)


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'school', 'school_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubjectGroupSerializer(serializers.ModelSerializer):
    """Serializer for SubjectGroup model"""
    
    class Meta:
        model = SubjectGroup
        fields = ['id', 'name', 'code', 'selection_type', 'created_at']
        read_only_fields = ['id', 'code', 'created_at']


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    class_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    subject_group_name = serializers.CharField(source='subject_group.name', read_only=True, allow_null=True)
    school = serializers.CharField()  # Accepts school code (string)
    class_model = serializers.CharField()  # Accepts class code (string)
    
    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'school', 'school_name', 'class_model', 'class_name',
            'department', 'department_name', 'subject_group', 'subject_group_name',
            'is_core', 'is_trade', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'code', 'created_at']
    
    def to_representation(self, instance):
        """Return school and class codes instead of objects when reading"""
        data = super().to_representation(instance)
        # Ensure school and class_model fields return codes (which are now the IDs)
        data['school'] = instance.school.id if instance.school else None
        data['class_model'] = instance.class_model.id if instance.class_model else None
        return data
    
    def create(self, validated_data):
        """Handle code to instance conversions"""
        from api.models import Class
        
        # Remove school if sent (we'll get it from class)
        validated_data.pop('school', None)
        
        # Get class instance
        class_code = validated_data.pop('class_model')
        class_instance = Class.objects.get(pk=class_code)
        
        # Set class and derive school from it
        validated_data['class_model'] = class_instance
        validated_data['school'] = class_instance.school
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Handle code to instance conversions"""
        from api.models import Class
        
        # Remove school if sent (we'll get it from class)
        validated_data.pop('school', None)
        
        # Update class if provided and derive school from it
        if 'class_model' in validated_data:
            class_code = validated_data.pop('class_model')
            class_instance = Class.objects.get(pk=class_code)
            validated_data['class_model'] = class_instance
            validated_data['school'] = class_instance.school
        
        return super().update(instance, validated_data)
    
    def get_class_name(self, obj):
        """Get class name"""
        return obj.class_model.name


class SessionTermSerializer(serializers.ModelSerializer):
    """Serializer for SessionTerm model"""
    term_order = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SessionTerm
        fields = ['id', 'session', 'term_name', 'term_order', 'start_date', 'end_date', 'is_current', 'created_at']
        read_only_fields = ['id', 'term_order', 'created_at']


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model"""
    session_terms = SessionTermSerializer(many=True, read_only=True)
    current_term = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current', 'created_at', 'session_terms', 'current_term']
        read_only_fields = ['id', 'created_at']
    
    def get_current_term(self, obj):
        """Get the current active term for this session"""
        current_term = obj.session_terms.filter(is_current=True).first()
        if current_term:
            return SessionTermSerializer(current_term).data
        return None  # Code is auto-generated

