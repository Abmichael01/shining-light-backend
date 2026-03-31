import logging
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import Class, Department, Session, SessionTerm, Student, StudentSubject, Subject
from api.serializers import ClassSerializer, DepartmentSerializer
from api.permissions import IsSchoolAdminOrReadOnly

logger = logging.getLogger(__name__)

class ClassViewSet(viewsets.ModelViewSet):
    """ViewSet for Class CRUD operations"""
    queryset = Class.objects.all().order_by("school", "order", "name")
    serializer_class = ClassSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        school = self.request.query_params.get("school", None)
        if school:
            queryset = queryset.filter(school=school)

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(class_code__icontains=search)
            )
        return queryset

    @action(detail=True, methods=["get"])
    def broadsheet(self, request, pk=None):
        """Get the broadsheet for a specific class, session, and term"""
        klass = self.get_object()
        session_id = request.query_params.get("session_id")
        term_id = request.query_params.get("term_id")

        if not session_id:
            current_session = Session.objects.filter(is_current=True).first()
            session_id = current_session.id if current_session else None
        
        if not term_id and session_id:
            current_term = SessionTerm.objects.filter(session_id=session_id, is_current=True).first()
            term_id = current_term.id if current_term else None

        if not term_id and session_id:
             current_term = SessionTerm.objects.filter(session_id=session_id).order_by('-is_current', '-start_date').first()
             term_id = current_term.id if current_term else None

        if not all([session_id, term_id]):
            return Response({"error": "session_id and term_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        subjects = Subject.objects.filter(class_model=klass).order_by("order", "name")
        subject_data = [{"id": s.id, "name": s.name, "code": s.code} for s in subjects]
        students = Student.objects.filter(class_model=klass, status='enrolled').select_related("biodata").order_by("biodata__surname", "biodata__first_name")
        
        registrations = StudentSubject.objects.filter(
            student__in=students, subject__in=subjects,
            session_id=session_id, session_term_id=term_id
        ).select_related("student", "subject", "grade")

        result_map = {}
        for reg in registrations:
            if reg.student_id not in result_map:
                result_map[reg.student_id] = {}
            result_map[reg.student_id][reg.subject_id] = {
                "total": float(reg.total_score) if reg.total_score is not None else None,
                "grade": reg.grade.grade_letter if reg.grade else None
            }

        student_results = []
        for student in students:
            scores = {}
            total_earned = 0
            subject_count = 0
            for subject in subjects:
                res = result_map.get(student.id, {}).get(subject.id)
                if res:
                    scores[subject.id] = res
                    if res["total"] is not None:
                        total_earned += res["total"]
                        subject_count += 1
                else:
                    scores[subject.id] = {"total": None, "grade": None}
            
            average = total_earned / subject_count if subject_count > 0 else 0
            student_results.append({
                "id": student.id,
                "full_name": student.get_full_name(),
                "admission_number": student.admission_number,
                "scores": scores,
                "average": round(float(average), 2),
                "total_earned": round(float(total_earned), 2),
                "subject_count": subject_count
            })

        student_results.sort(key=lambda x: x["average"], reverse=True)
        current_rank = 0
        current_avg = -1
        for i, res in enumerate(student_results):
            if res["average"] != current_avg:
                current_rank = i + 1
                current_avg = res["average"]
            res["position_number"] = current_rank
            pos = current_rank
            if 10 <= pos % 100 <= 20: suffix = 'th'
            else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(pos % 10, 'th')
            res["position"] = f"{pos}{suffix}"

        try:
            curr_session_name = Session.objects.get(id=session_id).name
            curr_term_name = SessionTerm.objects.get(id=term_id).term_name
        except:
            curr_session_name = "N/A"
            curr_term_name = "N/A"

        return Response({
            "class_metadata": {
                "name": klass.name, "school": klass.school.name,
                "session": curr_session_name, "term": curr_term_name
            },
            "subjects": subject_data,
            "students": student_results,
            "stats": {
                "total_students": len(student_results),
                "class_average": round(sum(s["average"] for s in student_results) / len(student_results), 2) if student_results else 0
            }
        })


class DepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Department CRUD operations"""
    queryset = Department.objects.all().order_by("school", "name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        school = self.request.query_params.get("school", None)
        if school:
            queryset = queryset.filter(school=school)
        return queryset
