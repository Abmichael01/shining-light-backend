from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import Question
from api.serializers import QuestionListSerializer, QuestionSerializer
from api.permissions import IsAdminOrStaff
from api.pagination import StandardResultsSetPagination

class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for Question CRUD operations"""
    queryset = Question.objects.all().select_related(
        "subject", "subject__class_model", "subject__class_model__school", "created_by"
    )
    permission_classes = [IsAdminOrStaff]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """Use different serializer for list vs detail"""
        if self.action == "list":
            return QuestionListSerializer
        return QuestionSerializer

    def get_queryset(self):
        """Filter questions based on query params"""
        queryset = super().get_queryset()

        subject = self.request.query_params.get("subject", None)
        if subject:
            queryset = queryset.filter(subject_id=subject)

        school = self.request.query_params.get("school", None)
        if school:
            queryset = queryset.filter(subject__class_model__school_id=school)

        class_id = self.request.query_params.get("class", None)
        if class_id:
            queryset = queryset.filter(subject__class_model_id=class_id)

        difficulty = self.request.query_params.get("difficulty", None)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        question_type = self.request.query_params.get("question_type", None)
        if question_type:
            queryset = queryset.filter(question_type=question_type)

        topic = self.request.query_params.get("topic", None)
        if topic:
            queryset = queryset.filter(topic_model__name__icontains=topic)

        is_verified = self.request.query_params.get("is_verified", None)
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == "true")

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(question_text__icontains=search)
                | models.Q(topic_model__name__icontains=search)
                | models.Q(subject__name__icontains=search)
            )
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        """Set the created_by field to current user"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get question bank statistics with filters"""
        queryset = self.get_queryset()
        total_questions = queryset.count()
        verified_questions = queryset.filter(is_verified=True).count()
        difficulty_counts = queryset.values("difficulty").annotate(count=models.Count("id"))
        type_counts = queryset.values("question_type").annotate(count=models.Count("id"))
        total_topics = queryset.values("topic_model").distinct().count()
        total_subjects = queryset.values("subject").distinct().count()

        return Response({
            "total_questions": total_questions,
            "verified_questions": verified_questions,
            "unverified_questions": total_questions - verified_questions,
            "total_topics": total_topics,
            "total_subjects": total_subjects,
            "difficulty_breakdown": {item["difficulty"]: item["count"] for item in difficulty_counts},
            "type_breakdown": {item["question_type"]: item["count"] for item in type_counts},
        })

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """Verify a question"""
        question = self.get_object()
        question.is_verified = True
        question.save(update_fields=["is_verified"])
        return Response({"status": "Question verified successfully"})

    @action(detail=True, methods=["post"])
    def unverify(self, request, pk=None):
        """Unverify a question"""
        question = self.get_object()
        question.is_verified = False
        question.save(update_fields=["is_verified"])
        return Response({"status": "Question unverified successfully"})
