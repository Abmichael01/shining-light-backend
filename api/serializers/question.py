from rest_framework import serializers
from api.models import Question, Subject, Topic


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model"""
    
    # Related field names for better API response
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    topic_name = serializers.CharField(source='topic_model.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Computed fields
    usage_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id',
            'question_text',
            'question_type',
            'difficulty',
            'marks',
            'subject',
            'subject_name',
            'subject_code',
            'topic_model',
            'topic_name',
            'option_a',
            'option_b',
            'option_c',
            'option_d',
            'option_e',
            'correct_answer',
            'explanation',
            'created_by',
            'created_by_name',
            'usage_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'usage_count']
    
    def validate(self, data):
        """Validate question data"""
        question_type = data.get('question_type')
        
        # Validate multiple choice questions
        if question_type == 'multiple_choice':
            required_options = ['option_a', 'option_b', 'option_c', 'option_d']
            for option in required_options:
                if not data.get(option):
                    raise serializers.ValidationError(f"{option.replace('_', ' ').title()} is required for multiple choice questions")
            
            # Validate correct answer
            correct_answer = data.get('correct_answer')
            if correct_answer and correct_answer not in ['A', 'B', 'C', 'D', 'E']:
                raise serializers.ValidationError("Correct answer must be A, B, C, D, or E")
        
        # Validate marks
        marks = data.get('marks', 0)
        if marks <= 0:
            raise serializers.ValidationError("Marks must be greater than 0")
        
        return data
    
    def create(self, validated_data):
        """Create question with proper validation"""
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update question with proper validation"""
        return super().update(instance, validated_data)


class QuestionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for question lists"""
    
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    topic_name = serializers.CharField(source='topic_model.name', read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id',
            'question_text',
            'question_type',
            'difficulty',
            'marks',
            'subject',
            'subject_name',
            'topic_model',
            'topic_name',
            'usage_count',
            'created_at',
        ]


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions"""
    
    class Meta:
        model = Question
        fields = [
            'question_text',
            'question_type',
            'difficulty',
            'marks',
            'subject',
            'topic_model',
            'option_a',
            'option_b',
            'option_c',
            'option_d',
            'option_e',
            'correct_answer',
            'explanation',
        ]
    
    def validate(self, data):
        """Validate question creation data"""
        question_type = data.get('question_type')
        
        # Validate multiple choice questions
        if question_type == 'multiple_choice':
            required_options = ['option_a', 'option_b', 'option_c', 'option_d']
            for option in required_options:
                if not data.get(option):
                    raise serializers.ValidationError(f"{option.replace('_', ' ').title()} is required for multiple choice questions")
        
        return data
