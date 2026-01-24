from rest_framework import serializers
from api.models import Period, TimetableEntry, AttendanceRecord, StudentAttendance, Staff, Schedule, ScheduleEntry
from .student import StudentSerializer
from .academic import ClassSerializer, SubjectSerializer

class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ['id', 'school', 'name', 'start_time', 'end_time', 'period_type', 'order']
        read_only_fields = ['id']

class TimetableEntrySerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    teacher_name = serializers.SerializerMethodField()
    period_name = serializers.CharField(source='period.name', read_only=True)
    period_start = serializers.TimeField(source='period.start_time', read_only=True)
    period_end = serializers.TimeField(source='period.end_time', read_only=True)

    class Meta:
        model = TimetableEntry
        fields = [
            'id', 'session_term', 'class_model', 'class_name', 'day_of_week', 
            'period', 'period_name', 'period_start', 'period_end',
            'subject', 'subject_name', 'teacher', 'teacher_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name()
        return None

class StudentAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_admission_number = serializers.CharField(source='student.admission_number', read_only=True)

    class Meta:
        model = StudentAttendance
        fields = ['id', 'student', 'student_name', 'student_admission_number', 'status', 'remark', 'time_marked']
        read_only_fields = ['id', 'time_marked']

class AttendanceRecordSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_model.name', read_only=True)
    taken_by_name = serializers.CharField(source='taken_by.get_full_name', read_only=True, default='')
    entries = StudentAttendanceSerializer(many=True, read_only=True)
    
    # Optional filtering fields for display
    total_present = serializers.SerializerMethodField()
    total_absent = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'session_term', 'class_model', 'class_name', 'date', 
            'timetable_entry', 'taken_by', 'taken_by_name', 
            'marked_at', 'entries', 'total_present', 'total_absent'
        ]
        read_only_fields = ['id', 'marked_at', 'taken_by']

    def get_total_present(self, obj):
        return obj.entries.filter(status='present').count()

    def get_total_absent(self, obj):
        return obj.entries.filter(status='absent').count()


class ScheduleEntrySerializer(serializers.ModelSerializer):
    # schedule_name removed
    linked_exam_title = serializers.CharField(source='linked_exam.title', read_only=True, allow_null=True)
    linked_subject_name = serializers.CharField(source='linked_subject.name', read_only=True, allow_null=True)
    supervisor_name = serializers.SerializerMethodField()
    target_class_names = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleEntry
        fields = [
            'id', 'schedule', 'date', 'start_time', 'end_time', 'title',
            'linked_exam', 'linked_exam_title', 'linked_subject', 'linked_subject_name',
            'target_classes', 'target_class_names', 'supervisor', 'supervisor_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_supervisor_name(self, obj):
        return obj.supervisor.get_full_name() if obj.supervisor else None

    def get_target_class_names(self, obj):
        return [c.name for c in obj.target_classes.all()]


class ScheduleSerializer(serializers.ModelSerializer):
    entries = ScheduleEntrySerializer(many=True, read_only=True)
    entry_count = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            'id', 'schedule_type', 'is_active', 'start_date', 'end_date',
            'entries', 'entry_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_entry_count(self, obj):
        return obj.entries.count()

