from rest_framework import serializers
from api.models import StudentAnswer, StudentExam
from api.serializers import ExamSerializer

class StudentAnswerSerializer(serializers.ModelSerializer):
    """Serializer for StudentAnswer model"""
    class Meta:
        model = StudentAnswer
        fields = [
            "id", "question", "question_number", "answer_text",
            "is_correct", "marks_obtained", "answered_at", "updated_at",
        ]
        read_only_fields = ["id", "answered_at", "updated_at"]


class StudentExamSerializer(serializers.ModelSerializer):
    """Serializer for StudentExam model"""
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    exam_subject = serializers.CharField(source="exam.subject.name", read_only=True)

    class Meta:
        model = StudentExam
        fields = [
            "id", "student", "exam", "exam_title", "exam_subject",
            "status", "score", "percentage", "passed", "started_at",
            "submitted_at", "time_remaining_seconds", "question_order",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "score", "percentage", "passed", "created_at", "updated_at",
        ]


class StudentExamDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for StudentExam with answers"""
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    exam_subject = serializers.CharField(source="exam.subject.name", read_only=True)
    exam_details = ExamSerializer(source="exam", read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = StudentExam
        fields = [
            "id", "student", "exam", "exam_title", "exam_subject", "status",
            "score", "percentage", "passed", "started_at", "submitted_at",
            "time_remaining_seconds", "question_order", "created_at", "updated_at",
            "exam_details", "answers",
        ]
