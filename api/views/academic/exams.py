from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import Exam, ExamHall, PastQuestion, Student, StudentExam, StudentAnswer
from api.serializers import ExamSerializer, ExamHallSerializer, PastQuestionSerializer
from api.serializers.exam import StudentExamResultSerializer
from api.permissions import IsSchoolAdmin, IsAdminOrStaff
from api.pagination import StandardResultsSetPagination
from .serializers import StudentExamSerializer, StudentAnswerSerializer, StudentExamDetailSerializer

class ExamHallViewSet(viewsets.ModelViewSet):
    """ViewSet for ExamHall CRUD operations"""
    queryset = ExamHall.objects.all().order_by("name")
    serializer_class = ExamHallSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(models.Q(name__icontains=search))
        return queryset


class ExamViewSet(viewsets.ModelViewSet):
    """ViewSet for Exam CRUD operations"""
    queryset = (
        Exam.objects.select_related(
            "subject", "subject__school", "subject__class_model",
            "session_term", "created_by",
        )
        .all()
        .order_by("-created_at")
    )
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        exam_status = self.request.query_params.get("status", None)
        if exam_status:
            queryset = queryset.filter(status=exam_status)

        exam_type = self.request.query_params.get("exam_type", None)
        if exam_type:
            queryset = queryset.filter(exam_type=exam_type)

        subject = self.request.query_params.get("subject", None)
        if subject:
            queryset = queryset.filter(subject=subject)

        active_only = self.request.query_params.get("active_only", None)
        if active_only and active_only.lower() == "true":
            queryset = queryset.filter(status="active")

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(subject__name__icontains=search)
                | models.Q(instructions__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        questions_data = request.data.get("questions", [])
        exam = serializer.save(created_by=request.user)
        if questions_data:
            exam.questions.set(questions_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        questions_data = request.data.get("questions", [])
        if questions_data:
            instance.questions.set(questions_data)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        exam = self.get_object()
        student_exams = (
            StudentExam.objects.filter(exam=exam)
            .select_related("student__user")
            .order_by("-score")
        )
        serializer = StudentExamResultSerializer(student_exams, many=True)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_student_exams(request, student_id):
    """Get all exams taken by a specific student"""
    try:
        student = get_object_or_404(Student, id=student_id)
        student_exams = StudentExam.objects.filter(student=student).order_by(
            "-submitted_at", "-created_at"
        )
        serializer = StudentExamSerializer(student_exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch student exams: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_student_exam_detail(request, student_exam_id):
    """Get detailed exam results for a specific student exam attempt"""
    try:
        student_exam = get_object_or_404(StudentExam, id=student_exam_id)
        student_answers = StudentAnswer.objects.filter(
            student_exam=student_exam
        ).order_by("question_number")
        exam_data = StudentExamDetailSerializer(student_exam).data
        exam_data["answers"] = StudentAnswerSerializer(student_answers, many=True).data
        return Response(exam_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch exam details: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class PastQuestionViewSet(viewsets.ModelViewSet):
    queryset = (
        PastQuestion.objects.all()
        .select_related("subject", "class_model", "session", "uploaded_by")
        .order_by("-created_at")
    )
    serializer_class = PastQuestionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        subject = self.request.query_params.get("subject")
        if subject:
            queryset = queryset.filter(subject_id=subject)
        class_id = self.request.query_params.get("class") or self.request.query_params.get("class_model")
        if class_id:
            queryset = queryset.filter(class_model_id=class_id)
        term = self.request.query_params.get("term")
        if term:
            queryset = queryset.filter(term=term)
        session = self.request.query_params.get("session")
        if session:
            queryset = queryset.filter(session_id=session)
        question_type = self.request.query_params.get("question_type")
        if question_type:
            queryset = queryset.filter(question_type=question_type)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
