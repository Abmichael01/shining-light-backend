from rest_framework import serializers
from api.models import Question, Subject, Topic
import re


def make_absolute_media_urls(html, request):
    """
    Helper to convert relative /media/ paths in HTML strings to absolute URLs.
    Uses re.sub with a callback for robust replacements.
    """
    if not html or not isinstance(html, str) or '/media/' not in html:
        return html

    # Build base URL from request (e.g., http://localhost:8007)
    base_url = request.build_absolute_uri('/')[:-1]
    
    def replacer(match):
        prefix = match.group(1) # src="
        path = match.group(2)   # /media/path/to/img.jpg
        suffix = match.group(3) # "
        
        if path.startswith('/media/'):
            return f'{prefix}{base_url}{path}{suffix}'
        return match.group(0)

    # Match src="..." or src='...'
    pattern = r'(src=["\'])([^"\']+)(["\'])'
    return re.sub(pattern, replacer, html)


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
            'question_image',
            'option_a',
            'option_a_image',
            'option_b',
            'option_b_image',
            'option_c',
            'option_c_image',
            'option_d',
            'option_d_image',
            'option_e',
            'option_e_image',
            'correct_answer',
            'explanation',
            'created_by',
            'created_by_name',
            'usage_count',
            'is_verified',
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
    
    def to_representation(self, instance):
        """Absoluteify media URLs in HTML fields"""
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request:
            html_fields = [
                'question_text', 'explanation', 
                'option_a', 'option_b', 'option_c', 'option_d', 'option_e'
            ]
            for field in html_fields:
                if data.get(field):
                    data[field] = make_absolute_media_urls(data[field], request)
        
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
            'is_verified',
            'question_image',
            'created_at',
        ]

    def to_representation(self, instance):
        """Absoluteify media URLs in question_text and image fields"""
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request:
            if data.get('question_text'):
                data['question_text'] = make_absolute_media_urls(data['question_text'], request)
            
        return data


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions"""
    
    class Meta:
        model = Question
        fields = [
            'question_text',
            'question_image',
            'question_type',
            'difficulty',
            'marks',
            'subject',
            'topic_model',
            'option_a',
            'option_a_image',
            'option_b',
            'option_b_image',
            'option_c',
            'option_c_image',
            'option_d',
            'option_d_image',
            'option_e',
            'option_e_image',
            'correct_answer',
            'explanation',
            'is_verified',
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
