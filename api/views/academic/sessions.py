from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import Session, SessionTerm
from api.serializers import SessionSerializer, SessionTermSerializer
from api.permissions import IsSchoolAdminOrReadOnly

class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Session CRUD operations
    """
    queryset = Session.objects.all().order_by("-start_date")
    serializer_class = SessionSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        """Filter and search sessions"""
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    @action(detail=True, methods=["post"])
    def set_current(self, request, pk=None):
        """Set this session as the current session"""
        session = self.get_object()
        Session.objects.all().update(is_current=False)
        session.is_current = True
        session.save()
        return Response({"detail": f"Session {session.name} is now current"})

    @action(detail=True, methods=["post"])
    def start_next_term(self, request, pk=None):
        """Start the next term for this session"""
        from rest_framework import status
        session = self.get_object()
        term_name = request.data.get("term_name")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        registration_deadline = request.data.get("registration_deadline")

        if not all([term_name, start_date, end_date]):
            return Response(
                {"detail": "term_name, start_date, and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session_term = session.create_next_term(term_name, start_date, end_date, registration_deadline)
            return Response(
                {
                    "detail": f"{term_name} started successfully",
                    "session_term": SessionTermSerializer(session_term).data,
                }
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SessionTermViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SessionTerm operations
    """
    queryset = SessionTerm.objects.all().order_by("-session__start_date", "term_name")
    serializer_class = SessionTermSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        """Filter by session if provided"""
        queryset = super().get_queryset()
        session_id = self.request.query_params.get("session", None)
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset

    @action(detail=True, methods=["post"])
    def set_current(self, request, pk=None):
        """Set this session term as current"""
        session_term = self.get_object()
        SessionTerm.objects.filter(session=session_term.session).update(
            is_current=False
        )
        session_term.is_current = True
        session_term.save()
        return Response(
            {
                "detail": f"{session_term.term_name} is now current for {session_term.session.name}"
            }
        )
