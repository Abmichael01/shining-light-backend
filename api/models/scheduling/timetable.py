from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from api.models.academic import School, SessionTerm, Class, Subject
from api.models.staff import Staff

class Period(models.Model):
    """Defines bell schedule/time slots for a school section"""
    PERIOD_TYPE_CHOICES = [('lesson', 'Lesson'), ('break', 'Break'), ('assembly', 'Assembly'), ('other', 'Other')]
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='periods', verbose_name=_('school'))
    name = models.CharField(_('period name'), max_length=50)
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    period_type = models.CharField(_('period type'), max_length=20, choices=PERIOD_TYPE_CHOICES, default='lesson')
    order = models.PositiveSmallIntegerField(_('order'), default=0)
    
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
    """Maps a Class + Period + Day to a Subject and Teacher."""
    DAY_CHOICES = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]
    session_term = models.ForeignKey(SessionTerm, on_delete=models.CASCADE, related_name='timetable_entries', verbose_name=_('session term'))
    class_model = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='timetable_entries', verbose_name=_('class'))
    day_of_week = models.PositiveSmallIntegerField(_('day of week'), choices=DAY_CHOICES)
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name='scheduled_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_occurrences', null=True, blank=True)
    teacher = models.ForeignKey(Staff, on_delete=models.SET_NULL, related_name='timetabled_lessons', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_of_week', 'period__order']
        verbose_name = _('Timetable Entry')
        verbose_name_plural = _('Timetable Entries')
        unique_together = ['session_term', 'class_model', 'day_of_week', 'period']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, '')
        subject_name = self.subject.name if self.subject else 'Activity'
        return f"{self.class_model.name} - {day_name} [{self.period.name}]: {subject_name}"

    def clean(self):
        super().clean()
        if self.period.school != self.class_model.school:
             raise ValidationError(_('Period must belong to the same school as the class'))
        if self.teacher:
            conflicts = TimetableEntry.objects.filter(
                session_term=self.session_term, day_of_week=self.day_of_week, period=self.period, teacher=self.teacher
            ).exclude(pk=self.pk)
            if conflicts.exists():
                raise ValidationError({'teacher': _(f'Teacher is already scheduled for {conflicts.first().class_model.name} at this time.')})
