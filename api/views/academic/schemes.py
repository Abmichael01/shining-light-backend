from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import SchemeOfWork
from api.serializers import SchemeOfWorkSerializer

class SchemeOfWorkViewSet(viewsets.ModelViewSet):
    """ViewSet for Scheme of Work"""
    queryset = SchemeOfWork.objects.all().select_related("subject")
    serializer_class = SchemeOfWorkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        subject_id = self.request.query_params.get("subject")
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        term = self.request.query_params.get("term")
        if term:
            queryset = queryset.filter(term=term)
        return queryset.order_by("week_number")

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Bulk create topics for a subject"""
        subject_id = request.data.get("subject_id")
        term = request.data.get("term")
        topics = request.data.get("topics", [])

        if not all([subject_id, term, topics]):
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        SchemeOfWork.objects.filter(subject_id=subject_id, term=term).delete()

        created = []
        for item in topics:
            scheme = SchemeOfWork.objects.create(
                subject_id=subject_id,
                term=term,
                week_number=item.get("week_number"),
                topic=item.get("topic"),
                learning_objectives=item.get("learning_objectives", ""),
                resources=item.get("resources", ""),
            )
            created.append(scheme)

        return Response(
            SchemeOfWorkSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )
