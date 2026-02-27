from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings

class School(models.Model):
    """Represents school divisions: Nursery, Primary, Junior Secondary, Senior Secondary"""
    
    SCHOOL_TYPE_CHOICES = [
        ('Nursery', 'Nursery School'),
        ('Primary', 'Primary School'),
        ('Junior Secondary', 'Junior Secondary School'),
        ('Senior Secondary', 'Senior Secondary School'),
    ]
    
    id = models.CharField(_('id'), max_length=10, primary_key=True, editable=False)
    name = models.CharField(_('school name'), max_length=100)
    school_type = models.CharField(_('school type'), max_length=20, choices=SCHOOL_TYPE_CHOICES, unique=True)
    code = models.CharField(_('school code'), max_length=10, unique=True, editable=False)
    is_active = models.BooleanField(_('active'), default=True)
    
    ca_max_score = models.PositiveIntegerField(
        _('CA max score'),
        default=40,
        help_text=_('Maximum score for Continuous Assessment (e.g., 40)')
    )
    exam_max_score = models.PositiveIntegerField(
        _('Exam max score'),
        default=60,
        help_text=_('Maximum score for Examination (e.g., 60)')
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('School')
        verbose_name_plural = _('Schools')
        ordering = ['school_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.school_type})"
    
    def save(self, *args, **kwargs):
        if not self.code:
            code_map = {
                'Nursery': 'NUR',
                'Primary': 'PRM',
                'Junior Secondary': 'JNR',
                'Senior Secondary': 'SNR',
            }
            base_code = code_map.get(self.school_type, 'SCH')
            existing_schools = School.objects.filter(code__startswith=base_code).exclude(pk=self.pk).count()
            counter = existing_schools + 1
            self.code = f"{base_code}-{counter:03d}"
            while School.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                counter += 1
                self.code = f"{base_code}-{counter:03d}"
        
        if not self.id:
            self.id = self.code
        super().save(*args, **kwargs)


class AdmissionSettings(models.Model):
    """Controls admission portal availability and configuration"""
    
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='admission_settings',
        verbose_name=_('school')
    )
    is_admission_open = models.BooleanField(_('admission open'), default=False)
    admission_start_datetime = models.DateTimeField(_('admission start datetime'), null=True, blank=True)
    admission_end_datetime = models.DateTimeField(_('admission end datetime'), null=True, blank=True)
    application_fee_amount = models.DecimalField(_('application fee amount'), max_digits=10, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admission_settings_created',
        verbose_name=_('created by')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Admission Settings')
        verbose_name_plural = _('Admission Settings')
        ordering = ['-updated_at']
        unique_together = [['school']]
    
    def __str__(self):
        status = "Open" if self.is_admission_open else "Closed"
        return f"{self.school.name} - Admission {status}"
    
    def clean(self):
        super().clean()
        if self.is_admission_open:
            if not self.admission_start_datetime or not self.admission_end_datetime:
                raise ValidationError(_('Start and end datetime required when admission is open'))
            if self.admission_end_datetime <= self.admission_start_datetime:
                raise ValidationError(_('End datetime must be after start datetime'))
        if self.application_fee_amount < 0:
            raise ValidationError(_('Application fee cannot be negative'))


class SystemSetting(models.Model):
    """Global system settings"""
    result_download_fee = models.DecimalField(_('result download fee'), max_digits=10, decimal_places=2, default=1000.00)
    late_subject_registration_fee = models.DecimalField(_('late subject registration fee'), max_digits=10, decimal_places=2, default=500.00)
    show_announcement = models.BooleanField(_('show announcement'), default=False)
    announcement_title = models.CharField(_('announcement title'), max_length=200, blank=True)
    announcement_message = models.TextField(_('announcement message'), blank=True)
    is_maintenance_mode = models.BooleanField(_('maintenance mode'), default=False)
    maintenance_message = models.TextField(_('maintenance message'), default='System is under maintenance.')
    disable_staff_login = models.BooleanField(_('disable staff login'), default=False)
    staff_maintenance_message = models.TextField(_('staff maintenance message'), default='Staff portal is temporarily unavailable.')
    disable_student_login = models.BooleanField(_('disable student login'), default=False)
    student_maintenance_message = models.TextField(_('student maintenance message'), default='Student portal is temporarily unavailable.')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        
    def save(self, *args, **kwargs):
        self.pk = 1
        super(SystemSetting, self).save(*args, **kwargs)
        
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
