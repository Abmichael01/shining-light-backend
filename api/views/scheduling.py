from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models import Period, TimetableEntry, AttendanceRecord, StudentAttendance, Session, Student
from api.serializers.scheduling import (
    PeriodSerializer, TimetableEntrySerializer, 
    AttendanceRecordSerializer, StudentAttendanceSerializer
)
from django.utils import timezone
from api.permissions import IsAdminOrStaff, IsSchoolAdminOrReadOnly

class PeriodViewSet(viewsets.ModelViewSet):
    """
    Manage Bell Schedule/Periods
    """
    queryset = Period.objects.all()
    serializer_class = PeriodSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdminOrReadOnly]
    
    def get_queryset(self):
        # Filter by school if possible/needed
        return Period.objects.all().order_by('order')

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """
        Bulk update order of periods.
        Expected payload: { "items": [{ "id": 1, "order": 1 }, { "id": 2, "order": 2 }] }
        """
        items = request.data.get('items', [])
        
        # 1. Update Order
        for item in items:
            period_id = item.get('id')
            new_order = item.get('order')
            if period_id is not None and new_order is not None:
                Period.objects.filter(id=period_id).update(order=new_order)
        
        # 2. Auto-Rename based on new order (Smart Naming)
        # We need to process periods per school to ensure correct numbering
        affected_ids = [item.get('id') for item in items if item.get('id')]
        affected_schools = Period.objects.filter(id__in=affected_ids).values_list('school', flat=True).distinct()

        for school_id in affected_schools:
            periods = Period.objects.filter(school_id=school_id).order_by('order')
            lesson_count = 1
            
            for p in periods:
                old_name = p.name
                new_name = old_name
                
                if p.period_type == 'lesson':
                    new_name = f"Period {lesson_count}"
                    lesson_count += 1
                elif p.period_type == 'break':
                    new_name = "Long Break" if "Long" in old_name else ("Short Break" if "Short" in old_name else "Break")
                    # If simple "Break" or default, keep as Break
                elif p.period_type == 'assembly':
                    new_name = "Assembly"
                
                # Update if changed
                if new_name != old_name:
                    p.name = new_name
                    p.save(update_fields=['name'])

        return Response({'status': 'reordered'})

class TimetableViewSet(viewsets.ModelViewSet):
    """
    Manage Timetable Entries
    """
    queryset = TimetableEntry.objects.all()
    serializer_class = TimetableEntrySerializer
    permission_classes = [IsAuthenticated, IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        queryset = TimetableEntry.objects.all()
        
        # Filter by class
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(class_model_id=class_id)
            
        # Filter by teacher (My Schedule)
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        # Filter by school (via class)
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(class_model__school_id=school_id)
            
        # Filter by session_term
        session_term_id = self.request.query_params.get('session_term')
        
        if session_term_id:
             queryset = queryset.filter(session_term_id=session_term_id)
        else:
             # Default to current term if no term specified
             current_term = Session.get_current_session_term()
             if current_term:
                 queryset = queryset.filter(session_term=current_term)
            
        return queryset

class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Manage Attendance Records
    """
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(taken_by=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_bulk(self, request):
        """
        Mark attendance for a whole class at once.
        Payload:
        {
            "class_id": 1,
            "date": "2024-01-20",
            "timetable_entry_id": 5 (optional),
            "students": [
                {"student_id": "STU1", "status": "present"},
                {"student_id": "STU2", "status": "absent", "remark": "Sick"}
            ]
        }
        """
        class_id = request.data.get('class_id')
        date_str = request.data.get('date') or timezone.now().date()
        timetable_entry_id = request.data.get('timetable_entry_id')
        students_data = request.data.get('students', [])
        
        current_term = Session.get_current_session_term()
        if not current_term:
             return Response({"error": "No active session term found"}, status=status.HTTP_400_BAD_REQUEST)

        # Get or Create Attendance Record Header
        record, created = AttendanceRecord.objects.get_or_create(
            class_model_id=class_id,
            date=date_str,
            timetable_entry_id=timetable_entry_id,
            session_term=current_term,
            defaults={'taken_by': request.user}
        )
        
        # Process individual student entries
        created_count = 0
        updated_count = 0
        
        for item in students_data:
            student_id = item.get('student_id')
            attend_status = item.get('status', 'present')
            remark = item.get('remark', '')
            
            # Using update_or_create to handle re-marking/corrections
            status_obj, created_entry = StudentAttendance.objects.update_or_create(
                attendance_record=record,
                student_id=student_id,
                defaults={
                    'status': attend_status,
                    'remark': remark
                }
            )
            if created_entry:
                created_count += 1
            else:
                updated_count += 1
                
        return Response({
            "message": "Attendance marked successfully",
            "record_id": record.id,
            "created": created_count,
            "updated": updated_count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def student_history(self, request):
        """
        Get attendance history for a specific student
        """
        student_id = request.query_params.get('student_id')
        if not student_id:
             # If student is logged in, use their ID
            if hasattr(request.user, 'student_profile'):
                student_id = request.user.student_profile.id
            else:
                return Response({"error": "Student ID required"}, status=status.HTTP_400_BAD_REQUEST)
            
        history = StudentAttendance.objects.filter(
            student_id=student_id
        ).select_related('attendance_record').order_by('-attendance_record__date')
        
        data = []
        for entry in history:
            data.append({
                "date": entry.attendance_record.date,
                "status": entry.status,
                "type": "Period" if entry.attendance_record.timetable_entry else "Daily",
                "period": entry.attendance_record.timetable_entry.period.name if entry.attendance_record.timetable_entry else None,
                "remark": entry.remark
            })
            
        return Response(data)
