from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from .academic import School, SessionTerm, Class, Subject, Exam
from .student import Student
from .staff import Staff

class Period(models.Model):
    """
    Defines bell schedule/time slots for a school section
    e.g., "1st Period (08:00 - 08:40)", "Break (10:00-10:20)"
    """
    PERIOD_TYPE_CHOICES = [
        ('lesson', 'Lesson'),
        ('break', 'Break'),
        ('assembly', 'Assembly'),
        ('other', 'Other'),
    ]

    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE, 
        related_name='periods',
        verbose_name=_('school')
    )
    name = models.CharField(
        _('period name'), 
        max_length=50,
        help_text=_('e.g., 1st Period, Long Break')
    )
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    period_type = models.CharField(
        _('period type'), 
        max_length=20, 
        choices=PERIOD_TYPE_CHOICES, 
        default='lesson'
    )
    order = models.PositiveSmallIntegerField(
        _('order'), 
        default=0,
        help_text=_('Ordering for display (1, 2, 3...)')
    )
    
    class Meta:
        ordering = ['school', 'order', 'start_time']
        verbose_name = _('Period')
        verbose_name_plural = _('Periods')
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
    
    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_('End time must be after start time'))


class TimetableEntry(models.Model):
    """
    A single slot on the timetable.
    Maps a Class + Period + Day to a Subject and Teacher.
    """
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    session_term = models.ForeignKey(
        SessionTerm, 
        on_delete=models.CASCADE, 
        related_name='timetable_entries',
        verbose_name=_('session term')
    )
    class_model = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name='timetable_entries',
        verbose_name=_('class')
    )
    day_of_week = models.PositiveSmallIntegerField(
        _('day of week'), 
        choices=DAY_CHOICES
    )
    period = models.ForeignKey(
        Period, 
        on_delete=models.CASCADE,
        related_name='scheduled_entries'
    )
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='timetable_occurrences',
        null=True, # Nullable for things like 'Library Hour' or 'Assembly' tracked on timetable
        blank=True
    )
    teacher = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        related_name='timetabled_lessons',
        null=True,
        blank=True,
        help_text=_('Teacher for this specific lesson. Defaults to subject teacher if blank.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_of_week', 'period__order']
        verbose_name = _('Timetable Entry')
        verbose_name_plural = _('Timetable Entries')
        # Ensure a class doesn't have two things at the same time
        unique_together = ['session_term', 'class_model', 'day_of_week', 'period']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, '')
        subject_name = self.subject.name if self.subject else 'Activity'
        return f"{self.class_model.name} - {day_name} [{self.period.name}]: {subject_name}"

    def clean(self):
        super().clean()
        
        # 1. Ensure Period belongs to the same School as the Class
        if self.period.school != self.class_model.school:
             raise ValidationError(_('Period must belong to the same school as the class'))
        
        # 2. Teacher Conflict Check
        # If a teacher is assigned, check if they are already booked in another class at this same time (Term + Day + Period)
        teacher_to_check = self.teacher
        if not teacher_to_check and self.subject:
            # If no specific teacher assigned, assume the subject's assigned teacher(s) might be implied
            # But since subjects can have multiple teachers, we only enforce strict conflict checks if a specific teacher is picked
            pass 

        if teacher_to_check:
            conflicts = TimetableEntry.objects.filter(
                session_term=self.session_term,
                day_of_week=self.day_of_week,
                period=self.period,
                teacher=teacher_to_check
            ).exclude(pk=self.pk)

            if conflicts.exists():
                raise ValidationError({
                    'teacher': _(f'Teacher is already scheduled for {conflicts.first().class_model.name} at this time.')
                })

    def save(self, *args, **kwargs):
        # Auto-assign teacher from subject if not set (optional logic, keeping it simple for now)
        super().save(*args, **kwargs)


class AttendanceRecord(models.Model):
    """
    Header for an attendance sheet.
    Can be 'Daily' (Period=Null) or 'Per Period'.
    """
    session_term = models.ForeignKey(SessionTerm, on_delete=models.CASCADE)
    class_model = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(_('date'))
    
    # Optional link to a specific timetable period
    timetable_entry = models.ForeignKey(
        TimetableEntry, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='attendance_taken'
    )
    
    taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='attendance_taken'
    )
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-marked_at']
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        # Prevent duplicate headers for same class/date/period
        unique_together = ['class_model', 'date', 'timetable_entry']

    def __str__(self):
        type_str = f"Period: {self.timetable_entry.period.name}" if self.timetable_entry else "Daily Register"
        return f"{self.class_model.name} - {self.date} ({type_str})"


class StudentAttendance(models.Model):
    """
    Individual status for a student in an Attendance Record.
    """
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    attendance_record = models.ForeignKey(
        AttendanceRecord, 
        on_delete=models.CASCADE, 
        related_name='entries'
    )
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE,
        related_name='attendance_entries'
    )
    status = models.CharField(
        _('status'), 
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='present'
    )
    remark = models.CharField(_('remark'), max_length=100, blank=True)
    time_marked = models.TimeField(_('time marked'), auto_now_add=True)

    class Meta:
        verbose_name = _('Student Attendance')
        verbose_name_plural = _('Student Attendance')
        unique_together = ['attendance_record', 'student']

    def __str__(self):
        return f"{self.student.admission_number} - {self.get_status_display()}"


class Schedule(models.Model):
    """
    Groups scheduled events together (e.g., 'First Term Examination 2025', 'Sports Week')
    Allows creating date-based timetables separate from the recurring weekly timetable.
    """
    TYPE_CHOICES = [
        ('exam', 'Examination'),
        ('test', 'Test/Quiz'),
        ('event', 'School Event'),
        ('general', 'General Schedule'),
    ]

    schedule_type = models.CharField(
        _('schedule type'),
        max_length=20,
        choices=TYPE_CHOICES,
        default='general'
    )
    is_active = models.BooleanField(_('active'), default=True)
    
    start_date = models.DateField(_('start date'), null=True, blank=True)
    end_date = models.DateField(_('end date'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Schedule')
        verbose_name_plural = _('Schedules')

    def __str__(self):
        return f"{self.get_schedule_type_display()}"
    


class ScheduleEntry(models.Model):
    """
    A specific slot/event on a specific date within a Schedule.
    """
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name=_('schedule')
    )
    date = models.DateField(_('date'))
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text=_('e.g., Mathematics Exam, Morning Assembly')
    )
    
    # Linking optional content
    linked_exam = models.ForeignKey(
        Exam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_entries',
        verbose_name=_('linked exam'),
        help_text=_('Link to a specific CBT Exam configuration if applicable')
    )
    linked_subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_entries',
        verbose_name=_('linked subject'),
        help_text=_('Link to a subject for display purposes (e.g. Revision)')
    )
    
    # Targets
    target_classes = models.ManyToManyField(
        Class,
        related_name='schedule_entries',
        verbose_name=_('target classes'),
        help_text=_('Classes this entry applies to')
    )
    
    supervisor = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_schedules',
        verbose_name=_('supervisor/invigilator')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = _('Schedule Entry')
        verbose_name_plural = _('Schedule Entries')
        indexes = [
            models.Index(fields=['date', 'start_time']),
        ]

    def __str__(self):
        return f"{self.title} on {self.date}"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_('End time must be after start time'))
        

