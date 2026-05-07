from rest_framework import serializers
from api.models import AdmissionExamResult, AdmissionExamSubjectResult

class AdmissionExamSubjectResultSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    
    class Meta:
        model = AdmissionExamSubjectResult
        fields = ['id', 'subject', 'subject_name', 'score', 'total_marks']

class AdmissionExamResultSerializer(serializers.ModelSerializer):
    subject_results = AdmissionExamSubjectResultSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    
    class Meta:
        model = AdmissionExamResult
        fields = [
            'id', 'student', 'student_name', 'exam', 'exam_title', 
            'total_score', 'total_marks', 'percentage', 'passed', 
            'subject_results', 'submitted_at'
        ]
        read_only_fields = ['id', 'submitted_at']
