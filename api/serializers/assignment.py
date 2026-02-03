from rest_framework import serializers
from api.models import Assignment, AssignmentSubmission, Question
from .academic import ClassSerializer, SubjectSerializer
from .question import QuestionSerializer

class AssignmentSerializer(serializers.ModelSerializer):
    class_name = serializers.ReadOnlyField(source='class_model.name')
    subject_name = serializers.ReadOnlyField(source='subject.name')
    staff_name = serializers.ReadOnlyField(source='staff.get_full_name')
    question_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'description', 'staff', 'staff_name', 
            'class_model', 'class_name', 'subject', 'subject_name', 
            'questions', 'due_date', 'is_published', 'question_count', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AssignmentDetailSerializer(AssignmentSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    assignment_title = serializers.ReadOnlyField(source='assignment.title')
    
    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title', 'student', 'student_name', 
            'answers', 'marks', 'score', 'status', 'feedback', 'submitted_at', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'student', 'score', 'submitted_at', 'created_at', 'updated_at']
