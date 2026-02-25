from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from api.models.academic import Class, Subject, Exam
from api.models.staff import Staff

class Schedule(models.Model):
    """Groups scheduled events together (Examination, Sports Week, etc.)"""
    TYPE_CHOICES = [
        ('exam', 'Examination'), ('test', 'Test/Quiz'), ('cbt_exam', 'CBT Examination'),
        ('event', 'School Event'), ('general', 'General Schedule'),
    ]
    schedule_type = models.CharField(_('schedule type'), max_length=20, choices=TYPE_CHOICES, default='general')
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
    """A specific slot/event on a specific date within a Schedule."""
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='entries', verbose_name=_('schedule'))
    date = models.DateField(_('date'))
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    title = models.CharField(_('title'), max_length=200)
    linked_exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True, related_name='schedule_entries', verbose_name=_('linked exam'))
    linked_subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='schedule_entries', verbose_name=_('linked subject'))
    target_classes = models.ManyToManyField(Class, related_name='schedule_entries', verbose_name=_('target classes'))
    supervisor = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_schedules', verbose_name=_('supervisor/invigilator'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = _('Schedule Entry')
        verbose_name_plural = _('Schedule Entries')
        indexes = [models.Index(fields=['date', 'start_time'])]

    def __str__(self):
        return f"{self.title} on {self.date}"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_('End time must be after start time'))
