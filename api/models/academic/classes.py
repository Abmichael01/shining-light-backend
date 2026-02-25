from django.db import models
from django.utils.translation import gettext_lazy as _
from .schools import School

class Class(models.Model):
    """Represents a class level (e.g., Nursery 1, Primary 1, JSS 1, SSS 2)"""
    
    id = models.CharField(_('id'), max_length=10, primary_key=True, editable=False)
    name = models.CharField(_('class name'), max_length=50, help_text=_('e.g., Nursery 1, Primary 1, JSS 1, SSS 2'))
    class_code = models.CharField(
        _('class code'),
        max_length=10,
        unique=True,
        help_text=_('Short code for class, e.g., SS1, JSS2, PRI1, NUR1')
    )
    grade_level = models.CharField(
        _('grade level'),
        max_length=50,
        blank=True,
        help_text=_('Grouping for arms (e.g. "JSS 1" for JSS 1A, JSS 1B)')
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='classes',
        verbose_name=_('school')
    )
    class_staff = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_assigned',
        verbose_name=_('class staff')
    )
    assigned_teachers = models.ManyToManyField(
        'Staff',
        blank=True,
        related_name='assigned_classes',
        verbose_name=_('assigned teachers')
    )
    order = models.PositiveSmallIntegerField(_('display order'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Class')
        verbose_name_plural = _('Classes')
        ordering = ['school', 'order', 'name']
        unique_together = [['school', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.school.school_type})"
    
    def save(self, *args, **kwargs):
        if self.class_code and not self.id:
            self.id = self.class_code
        super().save(*args, **kwargs)
        try:
            if self.class_staff:
                from api.models import Staff as StaffModel, Subject as SubjectModel
                staff = StaffModel.objects.filter(user=self.class_staff).first()
                if staff:
                    for subj in SubjectModel.objects.filter(class_model=self):
                        subj.assigned_teachers.add(staff)
        except Exception:
            pass


class Department(models.Model):
    """Department for Senior School (Science, Arts, Commercial)"""
    
    name = models.CharField(_('department name'), max_length=100)
    code = models.CharField(_('department code'), max_length=10)
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='departments',
        verbose_name=_('school')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['school', 'name']
        unique_together = [['school', 'code']]
    
    def __str__(self):
        return f"{self.name} ({self.school.name})"


class Club(models.Model):
    """Represents school clubs and societies"""
    
    id = models.CharField(_('id'), max_length=15, primary_key=True, editable=False)
    name = models.CharField(_('club name'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Club')
        verbose_name_plural = _('Clubs')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            import random
            import string
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.id = f"CLUB-{random_code}"
            while Club.objects.filter(id=self.id).exists():
                random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                self.id = f"CLUB-{random_code}"
        super().save(*args, **kwargs)


class ExamHall(models.Model):
    """Represents exam halls/rooms where examinations are conducted"""
    
    id = models.CharField(_('id'), max_length=15, primary_key=True, editable=False)
    name = models.CharField(_('hall name'), max_length=100, unique=True)
    number_of_seats = models.PositiveIntegerField(_('number of seats'))
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Exam Hall')
        verbose_name_plural = _('Exam Halls')
        ordering = ['name']
    
    def __str__(self):
        status = 'Active' if self.is_active else 'Inactive'
        return f"{self.name} ({self.number_of_seats} seats) - {status}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            import random
            import string
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.id = f"HALL-{random_code}"
            while ExamHall.objects.filter(id=self.id).exists():
                random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                self.id = f"HALL-{random_code}"
        super().save(*args, **kwargs)
