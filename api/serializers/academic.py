from rest_framework import serializers
from api.models import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject, Topic, Grade, Question, Club, ExamHall, CBTExamCode, Exam, Assignment, Staff, SchemeOfWork
from django.core.files.base import ContentFile
import base64
import uuid


class SchoolSerializer(serializers.ModelSerializer):
    """Serializer for School model"""
    
    class Meta:
        model = School
        fields = ['id', 'name', 'school_type', 'code', 'is_active', 'ca_max_score', 'exam_max_score', 'created_at']
        read_only_fields = ['id', 'code', 'created_at']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    school = serializers.CharField()  # Accepts school code (string)
    assigned_teachers = serializers.PrimaryKeyRelatedField(many=True, queryset=Staff.objects.all(), required=False)
    assigned_teachers_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = ['id', 'name', 'class_code', 'school', 'school_name', 'class_staff', 'assigned_teachers', 'assigned_teachers_details', 'order', 'created_at']
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
        assigned = validated_data.pop('assigned_teachers', [])
        school_code = validated_data.pop('school')
        school = School.objects.get(pk=school_code)
        validated_data['school'] = school
        instance = super().create(validated_data)
        if assigned:
            instance.assigned_teachers.set(assigned)
        return instance
    
    def update(self, instance, validated_data):
        """Handle school code to instance conversion"""
        from api.models import School
        assigned = validated_data.pop('assigned_teachers', None)
        if 'school' in validated_data:
            school_code = validated_data.pop('school')
            validated_data['school'] = School.objects.get(pk=school_code)
        instance = super().update(instance, validated_data)
        if assigned is not None:
            instance.assigned_teachers.set(assigned)
        return instance

    def get_assigned_teachers_details(self, obj):
        details = []
        for teacher in obj.assigned_teachers.all():
            details.append({
                'staff_pk': teacher.pk,
                'staff_id': teacher.staff_id,
                'full_name': teacher.get_full_name(),
                'email': teacher.user.email if teacher.user else None,
            })
        return details


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
    assigned_teachers = serializers.PrimaryKeyRelatedField(many=True, queryset=Staff.objects.all(), required=False)
    assigned_teachers_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'school', 'school_name', 'class_model', 'class_name',
            'department', 'department_name', 'subject_group', 'subject_group_name',
            'order', 'ca_max', 'exam_max', 'assigned_teachers', 'assigned_teachers_details', 'created_at'
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
        
        assigned = validated_data.pop('assigned_teachers', [])
        instance = super().create(validated_data)
        if assigned:
            instance.assigned_teachers.set(assigned)
        return instance
    
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
        assigned = validated_data.pop('assigned_teachers', None)
        instance = super().update(instance, validated_data)
        if assigned is not None:
            instance.assigned_teachers.set(assigned)
        return instance
    
    def get_class_name(self, obj):
        """Get class name"""
        return obj.class_model.name

    def get_assigned_teachers_details(self, obj):
        details = []
        for teacher in obj.assigned_teachers.all():
            details.append({
                'staff_pk': teacher.pk,
                'staff_id': teacher.staff_id,
                'full_name': teacher.get_full_name(),
                'email': teacher.user.email if teacher.user else None,
            })
        return details


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
            'min_score', 'max_score', 'teacher_remark', 'principal_remark', 'ict_remark', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    school_name = serializers.CharField(source='subject.class_model.school.name', read_only=True)
    class_name = serializers.CharField(source='subject.class_model.name', read_only=True)
    class_id = serializers.CharField(source='subject.class_model.id', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    question_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    option_a_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    option_b_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    option_c_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    option_d_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    option_e_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'school_name', 'class_name', 'class_id',
            'topic_model', 'question_text', 'question_image', 'question_type', 'difficulty',
            'option_a', 'option_a_image',
            'option_b', 'option_b_image',
            'option_c', 'option_c_image',
            'option_d', 'option_d_image',
            'option_e', 'option_e_image',
            'correct_answer', 'explanation', 'marks',
            'is_verified', 'usage_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']

    def create(self, validated_data):
        return self._save_with_base64(None, validated_data)

    def update(self, instance, validated_data):
        return self._save_with_base64(instance, validated_data)

    def _save_with_base64(self, instance, validated_data):
        image_fields = [
            'question_image', 'option_a_image', 'option_b_image', 
            'option_c_image', 'option_d_image', 'option_e_image'
        ]
        
        for field in image_fields:
            image_data = validated_data.pop(field, None)
            if image_data:
                if isinstance(image_data, str) and image_data.startswith('data:'):
                    try:
                        format, imgstr = image_data.split(';base64,')
                        ext = format.split('/')[-1]
                        validated_data[field] = ContentFile(base64.b64decode(imgstr), name=f'q_{uuid.uuid4()}.{ext}')
                    except Exception:
                        pass
            elif image_data == "":
                validated_data[field] = None
        
        if instance:
            return super().update(instance, validated_data)
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        image_fields = [
            'question_image', 'option_a_image', 'option_b_image', 
            'option_c_image', 'option_d_image', 'option_e_image'
        ]
        
        for field in image_fields:
            image_obj = getattr(instance, field, None)
            if image_obj and hasattr(image_obj, 'url'):
                request = self.context.get('request')
                if request:
                    data[field] = request.build_absolute_uri(image_obj.url)
                else:
                    data[field] = image_obj.url
            else:
                data[field] = None
        return data
    
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
    class_id = serializers.CharField(source='subject.class_model.id', read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'school_name', 'class_name', 'class_id',
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


class ExamHallSerializer(serializers.ModelSerializer):
    """Serializer for ExamHall model"""
    
    class Meta:
        model = ExamHall
        fields = ['id', 'name', 'number_of_seats', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CBTExamCodeSerializer(serializers.ModelSerializer):
    """Serializer for CBTExamCode model"""
    student_name = serializers.SerializerMethodField()
    student_admission_number = serializers.CharField(source='student.admission_number', read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True, allow_null=True)
    exam_hall_name = serializers.CharField(source='exam_hall.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = CBTExamCode
        fields = [
            'id', 'code', 'exam', 'exam_title', 'student', 'student_name', 'student_admission_number',
            'exam_hall', 'exam_hall_name', 'seat_number', 'is_used', 'used_at', 'expires_at',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'code', 'created_at']
    
    def get_student_name(self, obj):
        """Get student's full name"""
        return obj.student.get_full_name() if hasattr(obj.student, 'get_full_name') else ''


class ExamSerializer(serializers.ModelSerializer):
    """Serializer for Exam model"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    class_name = serializers.CharField(source='subject.class_model.name', read_only=True)
    school_name = serializers.CharField(source='subject.school.name', read_only=True)
    session_term_name = serializers.CharField(source='session_term.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_students = serializers.SerializerMethodField()
    students_taken = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'subject', 'subject_name', 'subject_code', 'class_name', 'school_name',
            'exam_type', 'session_term', 'session_term_name', 'duration_minutes', 'total_marks', 'pass_mark',
            'total_questions', 'shuffle_questions', 'shuffle_options', 'show_results_immediately',
            'allow_review', 'allow_calculator', 'status', 'instructions', 'questions', 'created_by', 'created_by_name',
            'total_students', 'students_taken', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_students', 'students_taken']
    
    def get_total_students(self, obj):
        """Get total number of students eligible for this exam"""
        # This would need to be calculated based on the subject's class
        # For now, return a mock value
        return 0
    
    def get_students_taken(self, obj):
        """Number of students who have started or completed this exam"""
        return obj.student_attempts.filter(
            status__in=['in_progress', 'submitted', 'graded']
        ).count()
    
    def get_questions(self, obj):
        """Format questions with options for CBT"""
        # Check if specific question IDs are provided in context (from randomized selection)
        specific_question_ids = self.context.get('specific_question_ids')
        
        if specific_question_ids:
            # Preserve the order from specific_question_ids
            # Fetch all questions first
            from api.models import Question
            all_questions = {q.id: q for q in Question.objects.filter(id__in=specific_question_ids)}
            
            # Reconstruct list in the correct order
            questions = []
            for q_id in specific_question_ids:
                if q_id in all_questions:
                    questions.append(all_questions[q_id])
        else:
            # Default behavior: return all assigned questions
            questions = obj.questions.all()
            
        formatted_questions = []
        
        for question in questions:
            # Build options array from individual option fields
            options = []
            if question.option_a:
                options.append({'id': 'a', 'text': question.option_a})
            if question.option_b:
                options.append({'id': 'b', 'text': question.option_b})
            if question.option_c:
                options.append({'id': 'c', 'text': question.option_c})
            if question.option_d:
                options.append({'id': 'd', 'text': question.option_d})
            if question.option_e:
                options.append({'id': 'e', 'text': question.option_e})
            
            formatted_question = {
                'id': str(question.id),
                'question_text': question.question_text,
                'question_type': question.question_type,
                'options': options,
                'correct_answer': question.correct_answer,
                'marks': question.marks,
                'difficulty': question.difficulty,
                'explanation': question.explanation
            }
            formatted_questions.append(formatted_question)
        
        return formatted_questions


class AssignmentSerializer(serializers.ModelSerializer):
    """Serializer for Assignment model (simplified vs exams)"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'subject', 'subject_name', 'questions', 'due_date',
            'instructions', 'status', 'question_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'question_count', 'created_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.email
        return None


class SchemeOfWorkSerializer(serializers.ModelSerializer):
    """Serializer for SchemeOfWork"""
    topic_id = serializers.PrimaryKeyRelatedField(
        source='topic_model',
        queryset=Topic.objects.all(),
        required=False,
        allow_null=True
    )
    topic_name = serializers.CharField(source='topic_model.name', read_only=True)
    
    class Meta:
        model = SchemeOfWork
        fields = ['id', 'subject', 'term', 'week_number', 'topic', 'topic_id', 'topic_name', 'learning_objectives', 'resources', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'topic_name']

