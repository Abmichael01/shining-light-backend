from django.db import models
from rest_framework import viewsets
from api.models import Subject, SubjectGroup, Topic
from api.serializers import SubjectSerializer, SubjectGroupSerializer, TopicSerializer
from api.permissions import IsSchoolAdminOrReadOnly, IsAdminOrStaff

class SubjectGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for SubjectGroup CRUD operations"""
    queryset = SubjectGroup.objects.all().order_by("name")
    serializer_class = SubjectGroupSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        """Filter and search subject groups"""
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | models.Q(code__icontains=search)
            )
        return queryset


class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Subject CRUD operations"""
    queryset = (
        Subject.objects.select_related(
            "school", "class_model", "department", "subject_group"
        )
        .all()
        .order_by("school", "class_model", "order", "name")
    )
    serializer_class = SubjectSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        school = self.request.query_params.get("school", None)
        if school:
            queryset = queryset.filter(school=school)

        class_model = self.request.query_params.get("class", None)
        if class_model:
            queryset = queryset.filter(class_model=class_model)

        department = self.request.query_params.get("department", None)
        if department:
            queryset = queryset.filter(department=department)

        teacher_id = self.request.query_params.get("teacher_id", None)
        if teacher_id:
            queryset = queryset.filter(assigned_teachers__user_id=teacher_id)

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | models.Q(code__icontains=search)
            )

        exclude_registered = self.request.query_params.get("exclude_registered", None)
        session_id = self.request.query_params.get("session", None)
        term_id = self.request.query_params.get("term", None)

        if (
            exclude_registered == "true"
            and getattr(self.request.user, "user_type", None) == "student"
        ):
            from api.models.student import Student, StudentSubject
            try:
                student = Student.objects.get(user=self.request.user)
                reg_filter = {"student": student}
                if session_id:
                    reg_filter["session_id"] = session_id
                if term_id:
                    reg_filter["session_term_id"] = term_id

                registered_subject_ids = StudentSubject.objects.filter(
                    **reg_filter
                ).values_list("subject_id", flat=True)
                queryset = queryset.exclude(id__in=registered_subject_ids)
            except Student.DoesNotExist:
                pass
        return queryset


class TopicViewSet(viewsets.ModelViewSet):
    """ViewSet for Topic CRUD operations"""
    queryset = (
        Topic.objects.select_related("subject")
        .prefetch_related("questions")
        .all()
        .order_by("subject", "name")
    )
    serializer_class = TopicSerializer
    permission_classes = [IsAdminOrStaff]

    def get_queryset(self):
        queryset = super().get_queryset()
        subject = self.request.query_params.get("subject", None)
        if subject:
            queryset = queryset.filter(subject=subject)

        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )
        return queryset
