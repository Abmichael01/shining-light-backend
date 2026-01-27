from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models import Period, TimetableEntry, AttendanceRecord, StudentAttendance, Session, Student, Schedule, ScheduleEntry
from api.serializers.scheduling import (
    PeriodSerializer, TimetableEntrySerializer, 
    AttendanceRecordSerializer, StudentAttendanceSerializer,
    ScheduleSerializer, ScheduleEntrySerializer
)
from django.utils import timezone
from django.db import models
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
    
    def get_queryset(self):
        queryset = AttendanceRecord.objects.all()
        
        # Filter by class
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(class_model_id=class_id)
            
        # Filter by date
        date_str = self.request.query_params.get('date')
        if date_str:
            queryset = queryset.filter(date=date_str)
            
        # Filter by teacher/staff
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            # Join with timetable_entry to filter by teacher
            queryset = queryset.filter(timetable_entry__teacher_id=teacher_id)
            
        # Filter by user who marked it
        taken_by_id = self.request.query_params.get('taken_by')
        if taken_by_id:
            queryset = queryset.filter(taken_by_id=taken_by_id)
            
        return queryset.order_by('-date', '-marked_at')

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
        
        # Ensure taken_by is set if record already existed (from auto-generation)
        if not created and not record.taken_by:
            record.taken_by = request.user
            record.save(update_fields=['taken_by'])
        
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
            
    @action(detail=False, methods=['get'])
    def pending_marking(self, request):
        """
        Get list of past lessons that haven't been marked by the teacher.
        Logic:
        1. Get current term and teacher profile.
        2. Get all timetable entries for this teacher.
        3. Iterate date range (Term Start -> Today).
        4. For each day, check if lessons were scheduled but not marked.
        """
        try:
            # 1. Identify Teacher
            from api.models import Staff
            teacher = Staff.objects.filter(user=request.user).first()
            if not teacher:
                return Response({"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND)

            # 2. Get Current Term
            current_term = Session.get_current_session_term()
            if not current_term:
                return Response([], status=status.HTTP_200_OK)

            # 3. Get Teacher's Timetable
            # This part is no longer strictly needed for the direct query, but keeping the comment for context.
            # entries = TimetableEntry.objects.filter(
            #     session_term=current_term,
            #     teacher=teacher
            # ).select_related('period', 'class_model', 'subject')

            # 4. Get Pending Records (Auto-generated but not taken)
            today = timezone.localdate() # Use timezone.localdate() for consistency
            
            # Find AttendanceRecords that:
            # - Are for this term
            # - Are on/before today
            # - Have NOT been taken (taken_by is Null)
            # - Belong to this teacher's classes/subjects
            
            pending_records = AttendanceRecord.objects.filter(
                session_term=current_term,
                date__lte=today,
                taken_by__isnull=True
            ).filter(
                models.Q(timetable_entry__teacher=teacher) | # Changed 'staff' to 'teacher'
                models.Q(timetable_entry__subject__assigned_teachers=teacher) # Changed 'staff' to 'teacher'
            ).select_related(
                'timetable_entry', 
                'class_model', 
                'timetable_entry__period', 
                'timetable_entry__subject'
            ).order_by('-date', 'timetable_entry__period__start_time').distinct()

            pending = []
            for record in pending_records:
                lesson = record.timetable_entry
                if not lesson: continue
                
                pending.append({
                    "date": record.date,
                    "timetable_entry_id": lesson.id,
                    "class_id": lesson.class_model_id,
                    "class_name": lesson.class_model.name,
                    "subject_name": lesson.subject.name if lesson.subject else "No Subject",
                    "period_name": lesson.period.name,
                    "start_time": lesson.period.start_time,
                    "end_time": lesson.period.end_time
                })
            
            return Response(pending)

        except Exception as e:
            print(f"Error fetching pending attendance: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def mark_all_present(self, request):
        """
        Quickly mark all students in a class as Present for a specific lesson.
        """
        try:
            class_id = request.data.get('class_id')
            date_str = request.data.get('date')
            timetable_entry_id = request.data.get('timetable_entry_id')
            
            if not class_id or not date_str:
                 return Response({"error": "Class ID and Date are required"}, status=status.HTTP_400_BAD_REQUEST)

            current_term = Session.get_current_session_term()
            if not current_term:
                 return Response({"error": "No active session term found"}, status=status.HTTP_400_BAD_REQUEST)
                 
            # 1. Get/Create Header
            record, created = AttendanceRecord.objects.get_or_create(
                class_model_id=class_id,
                date=date_str,
                timetable_entry_id=timetable_entry_id,
                session_term=current_term,
                defaults={'taken_by': request.user}
            )
            
            # Ensure taken_by is set if record already existed (from auto-generation)
            if not created and not record.taken_by:
                record.taken_by = request.user
                record.save(update_fields=['taken_by'])

            # 2. Get Students
            # Only enrolled/active students
            # 2. Get Students
            # Only enrolled students
            students = Student.objects.filter(
                class_model_id=class_id,
                status='enrolled'
            )
            
            if not students.exists():
                 return Response({"message": "No active students found in this class"}, status=status.HTTP_404_NOT_FOUND)

            # 3. Bulk Create Entries
            entries_to_create = []
            
            # Check existing to avoid duplication errors
            existing_student_ids = set(StudentAttendance.objects.filter(attendance_record=record).values_list('student_id', flat=True))
            
            for student in students:
                if student.id not in existing_student_ids:
                    entries_to_create.append(StudentAttendance(
                        attendance_record=record,
                        student=student,
                        status='present',
                        remark=''
                    ))
            
            if entries_to_create:
                StudentAttendance.objects.bulk_create(entries_to_create)
                
            return Response({
                "message": "All students marked as Present",
                "record_id": record.id,
                "added": len(entries_to_create)
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScheduleViewSet(viewsets.ModelViewSet):
    """
    Manage Schedules (Exam Timetables, Event Schedules)
    """
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [IsAuthenticated, IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        queryset = Schedule.objects.all().prefetch_related('entries')
        
        # Filter by type
        schedule_type = self.request.query_params.get('type')
        if schedule_type:
            queryset = queryset.filter(schedule_type=schedule_type)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Enforce active filtering for non-admins
        user = self.request.user
        is_admin = user.is_superuser or user.is_staff or getattr(user, 'user_type', None) == 'admin'
        
        if not is_admin:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get or create the singleton schedule for a given type.
        Usage: /api/scheduling/schedules/current/?type=exam
        """
        schedule_type = request.query_params.get('type', 'general')
        
        # For non-admins, must be active. For admins, we typically show the latest configuration.
        user = request.user
        is_admin = user.is_superuser or user.is_staff or getattr(user, 'user_type', None) == 'admin'
        
        query = Schedule.objects.filter(schedule_type=schedule_type)
        if not is_admin:
            query = query.filter(is_active=True)
            
        schedule = query.order_by('-created_at').first()
        
        if not schedule:
            if is_admin:
                # Admins can create a new one if none exists
                schedule = Schedule.objects.create(
                    schedule_type=schedule_type,
                    is_active=True
                )
            else:
                # If no active schedule for student/teacher, return 404
                return Response({"detail": "No active schedule found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)


class ScheduleEntryViewSet(viewsets.ModelViewSet):
    """
    Manage Schedule Entries (individual slots)
    """
    queryset = ScheduleEntry.objects.all()
    serializer_class = ScheduleEntrySerializer
    permission_classes = [IsAuthenticated, IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        queryset = ScheduleEntry.objects.all().select_related(
            'schedule', 'linked_exam', 'linked_subject', 'supervisor'
        ).prefetch_related('target_classes')
        
        # Filter by schedule
        schedule_id = self.request.query_params.get('schedule')
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        
        # Filter by date
        date_str = self.request.query_params.get('date')
        if date_str:
            queryset = queryset.filter(date=date_str)
        
        # Filter by class
        class_id = self.request.query_params.get('class_id')
        if class_id:
            queryset = queryset.filter(target_classes__id=class_id)
        
        # Enforce active schedule filtering for non-admins
        user = self.request.user
        is_admin = user.is_superuser or user.is_staff or getattr(user, 'user_type', None) == 'admin'
        
        if not is_admin:
            queryset = queryset.filter(schedule__is_active=True)
            
        return queryset.order_by('date', 'start_time')

