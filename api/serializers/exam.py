from rest_framework import serializers
from api.models import StudentExam
from api.serializers.student import StudentListSerializer


class StudentExamResultSerializer(serializers.ModelSerializer):
    """Serializer for StudentExam model for results"""
    student = StudentListSerializer()

    class Meta:
        model = StudentExam
        fields = [
            'id', 'student', 'exam', 'status', 'score', 'percentage', 'passed',
            'started_at', 'submitted_at'
        ]
