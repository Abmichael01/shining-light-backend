from rest_framework import serializers
from api.models import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject, Topic, Grade, Question, Club, Exam


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
    
    def to_representation(self, instance):
        """Return school code instead of school object when reading"""
        data = super().to_representation(instance)
        # Ensure school field returns the code (which is now the ID)
        data['school'] = instance.school.id if instance.school else None
        return data


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
            'order', 'ca_max', 'exam_max', 'created_at'
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


class TopicSerializer(serializers.ModelSerializer):
    """Serializer for Topic model"""
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = ['id', 'subject', 'name', 'description', 'is_active', 'question_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'question_count', 'created_at', 'updated_at']
    
    def get_question_count(self, obj):
        """Get question count - either from annotation or direct count"""
        if hasattr(obj, 'question_count'):
            return obj.question_count
        return obj.questions.count()


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


class GradeSerializer(serializers.ModelSerializer):
    """Serializer for Grade model"""
    
    class Meta:
        model = Grade
        fields = [
            'id', 'grade_letter', 'grade_name', 'grade_description',
            'min_score', 'max_score', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    school_name = serializers.CharField(source='subject.class_model.school.name', read_only=True)
    class_name = serializers.CharField(source='subject.class_model.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'school_name', 'class_name',
            'topic_model', 'question_text', 'question_type', 'difficulty',
            'option_a', 'option_b', 'option_c', 'option_d', 'option_e',
            'correct_answer', 'explanation', 'marks',
            'is_verified', 'usage_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        """Get creator's email (custom User model only has email field)"""
        if obj.created_by:
            return obj.created_by.email
        return None
    
    def validate(self, data):
        """Additional validation based on question type"""
        question_type = data.get('question_type', self.instance.question_type if self.instance else None)
        
        if question_type == 'multiple_choice':
            # Ensure required options are provided
            required_options = ['option_a', 'option_b', 'option_c', 'option_d']
            for option in required_options:
                if not data.get(option):
                    raise serializers.ValidationError({
                        option: 'Multiple choice questions must have at least 4 options (A-D)'
                    })
            
            # Validate correct answer
            correct = data.get('correct_answer', '').upper()
            if correct not in ['A', 'B', 'C', 'D', 'E']:
                raise serializers.ValidationError({
                    'correct_answer': 'Correct answer for multiple choice must be A, B, C, D, or E'
                })
        
        elif question_type == 'true_false':
            correct = data.get('correct_answer', '').lower()
            if correct not in ['true', 'false']:
                raise serializers.ValidationError({
                    'correct_answer': 'Correct answer for true/false must be True or False'
                })
        
        return data


class QuestionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing questions"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    school_name = serializers.CharField(source='subject.class_model.school.name', read_only=True)
    class_name = serializers.CharField(source='subject.class_model.name', read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'school_name', 'class_name',
            'topic_model', 'question_text', 'question_type', 'difficulty',
            'is_verified', 'usage_count', 'created_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at']


class ClubSerializer(serializers.ModelSerializer):
    """Serializer for Club model"""
    
    class Meta:
        model = Club
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExamSerializer(serializers.ModelSerializer):
    """Serializer for Exam model"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    class_name = serializers.CharField(source='subject.class_model.name', read_only=True)
    school_name = serializers.CharField(source='subject.school.name', read_only=True)
    session_term_name = serializers.CharField(source='session_term.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_students = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'subject', 'subject_name', 'subject_code', 'class_name', 'school_name',
            'exam_type', 'session_term', 'session_term_name', 'start_date', 'start_time',
            'end_date', 'end_time', 'duration_minutes', 'total_marks', 'pass_mark',
            'total_questions', 'shuffle_questions', 'shuffle_options', 'show_results_immediately',
            'allow_review', 'status', 'instructions', 'created_by', 'created_by_name',
            'total_students', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_students']
    
    def get_total_students(self, obj):
        """Get total number of students eligible for this exam"""
        # This would need to be calculated based on the subject's class
        # For now, return a mock value
        return 0

