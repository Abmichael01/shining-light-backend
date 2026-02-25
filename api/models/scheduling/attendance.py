from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from api.models.academic import SessionTerm, Class
from api.models.student import Student
from .timetable import TimetableEntry

class AttendanceRecord(models.Model):
    """Header for an attendance sheet (Daily or Per Period)."""
    session_term = models.ForeignKey(SessionTerm, on_delete=models.CASCADE)
    class_model = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(_('date'))
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_taken')
    taken_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='attendance_taken')
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-marked_at']
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        unique_together = ['class_model', 'date', 'timetable_entry']

    def __str__(self):
        type_str = f"Period: {self.timetable_entry.period.name}" if self.timetable_entry else "Daily Register"
        return f"{self.class_model.name} - {self.date} ({type_str})"


class StudentAttendance(models.Model):
    """Individual status for a student in an Attendance Record."""
    STATUS_CHOICES = [('present', 'Present'), ('absent', 'Absent'), ('late', 'Late'), ('excused', 'Excused')]
    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_entries')
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='present')
    remark = models.CharField(_('remark'), max_length=100, blank=True)
    time_marked = models.TimeField(_('time marked'), auto_now_add=True)

    class Meta:
        verbose_name = _('Student Attendance')
        verbose_name_plural = _('Student Attendance')
        unique_together = ['attendance_record', 'student']

    def __str__(self):
        return f"{self.student.admission_number} - {self.get_status_display()}"
