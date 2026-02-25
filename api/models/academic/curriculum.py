from django.db import models
import re
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .schools import School
from .classes import Class, Department

class SubjectGroup(models.Model):
    """Groups subjects together (e.g., Science Subjects, Arts Subjects, Trade Subjects)"""
    
    SELECTION_TYPE_CHOICES = [
        ('single', 'Single Selection'),
        ('multiple', 'Multiple Selection'),
    ]
    
    name = models.CharField(_('group name'), max_length=100, unique=True)
    code = models.CharField(_('group code'), max_length=10, blank=True)
    selection_type = models.CharField(
        _('selection type'),
        max_length=10,
        choices=SELECTION_TYPE_CHOICES,
        default='multiple',
        help_text=_('Single: student selects one, Multiple: student can select multiple')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Subject Group')
        verbose_name_plural = _('Subject Groups')
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.code:
            words = self.name.upper().split()
            if len(words) == 1:
                self.code = words[0][:6]
            else:
                self.code = ''.join([word[:3] for word in words[:2]])
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Subject(models.Model):
    """Individual subject with all details"""
    
    id = models.CharField(_('id'), max_length=50, primary_key=True, editable=False)
    name = models.CharField(_('subject name'), max_length=200)
    code = models.CharField(_('subject code'), max_length=50, unique=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='subjects', verbose_name=_('school'))
    class_model = models.ForeignKey(Class, on_delete=models.PROTECT, related_name='subjects', verbose_name=_('class'))
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True, related_name='subjects', verbose_name=_('department'))
    subject_group = models.ForeignKey(SubjectGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects', verbose_name=_('subject group'))
    order = models.PositiveSmallIntegerField(_('display order'), default=0)
    assigned_teachers = models.ManyToManyField('Staff', blank=True, related_name='assigned_subjects', verbose_name=_('assigned teachers'))
    
    ca_max = models.DecimalField(_('CA maximum score'), max_digits=5, decimal_places=2, default=40)
    exam_max = models.DecimalField(_('Exam maximum score'), max_digits=5, decimal_places=2, default=60)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
        ordering = ['school', 'class_model', 'order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def _generate_subject_code(self):
        subject_part = self.name.upper().replace(' ', '-')
        class_code = self.class_model.class_code.upper()
        return f"{subject_part}-{class_code}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_subject_code()
        self.code = re.sub(r"\s+", "-", self.code.strip()).upper()
        
        counter = 1
        base_code = self.code
        while Subject.objects.filter(code=self.code).exclude(pk=self.pk).exists():
            self.code = f"{base_code}-{counter}"
            counter += 1
        
        if not self.id:
            self.id = self.code
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.code and (" " in self.code):
            raise ValidationError(_('Subject code cannot contain spaces'))
        if self.department and self.school.school_type != 'Senior Secondary':
            raise ValidationError(_('Department can only be set for Senior Secondary School subjects'))
        if self.department and self.department.school != self.school:
            raise ValidationError(_('Department must belong to the same school as the subject'))
        if self.subject_group and hasattr(self.subject_group, 'class_model') and self.subject_group.class_model != self.class_model:
             raise ValidationError(_('Subject group must belong to the same class'))


@receiver(m2m_changed, sender=Class.assigned_teachers.through)
def propagate_class_assigned_teachers(sender, instance, action, pk_set, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        from api.models import Staff as StaffModel
        subjects = Subject.objects.filter(class_model=instance)
        if action == 'post_clear':
            for subj in subjects:
                subj.assigned_teachers.clear()
        elif action in ['post_add', 'post_remove'] and pk_set is not None:
            staff_qs = StaffModel.objects.filter(id__in=list(pk_set))
            for subj in subjects:
                if action == 'post_add':
                    subj.assigned_teachers.add(*staff_qs)
                elif action == 'post_remove':
                    subj.assigned_teachers.remove(*staff_qs)


class Topic(models.Model):
    """Topics within a subject for better question organization"""
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics', verbose_name=_('subject'))
    name = models.CharField(_('topic name'), max_length=200)
    description = models.TextField(_('description'), blank=True, null=True)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')
        ordering = ['subject', 'name']
        unique_together = [['subject', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.subject.name})"
    
    @property
    def question_count(self):
        return self.questions.count()


class Grade(models.Model):
    """Configurable grading system - Admin can define grade ranges"""
    
    GRADE_LETTER_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F')]
    
    grade_letter = models.CharField(_('grade letter'), max_length=1, choices=GRADE_LETTER_CHOICES, unique=True)
    grade_name = models.CharField(_('grade name'), max_length=20)
    grade_description = models.CharField(_('grade description'), max_length=100)
    min_score = models.DecimalField(_('minimum score'), max_digits=5, decimal_places=2)
    max_score = models.DecimalField(_('maximum score'), max_digits=5, decimal_places=2)
    order = models.PositiveSmallIntegerField(_('display order'), editable=False)
    
    teacher_remark = models.CharField(_('teacher remark'), max_length=255, blank=True)
    principal_remark = models.CharField(_('principal remark'), max_length=255, blank=True)
    ict_remark = models.CharField(_('ICT remark'), max_length=255, blank=True)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Grade')
        verbose_name_plural = _('Grades')
        ordering = ['order', '-min_score']
    
    def __str__(self):
        return f"{self.grade_name} ({self.min_score}-{self.max_score})"
    
    def save(self, *args, **kwargs):
        grade_order_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6}
        self.order = grade_order_map.get(self.grade_letter, 99)
        super().save(*args, **kwargs)
    
    def clean(self):
        super().clean()
        if self.min_score >= self.max_score:
            raise ValidationError(_('Minimum score must be less than maximum score'))
        if self.min_score < 0 or self.max_score > 100:
            raise ValidationError(_('Scores must be between 0 and 100'))
        
        overlapping_grades = Grade.objects.exclude(pk=self.pk).filter(
            models.Q(min_score__lte=self.max_score, max_score__gte=self.min_score)
        )
        if overlapping_grades.exists():
            raise ValidationError(_('This grade range overlaps with existing grades'))
    
    @classmethod
    def get_grade_for_score(cls, score):
        try:
            return cls.objects.get(min_score__lte=score, max_score__gte=score)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(min_score__lte=score, max_score__gte=score).first()


class SchemeOfWork(models.Model):
    """Weekly Scheme of Work for subjects"""
    
    TERM_CHOICES = [('1st Term', '1st Term'), ('2nd Term', '2nd Term'), ('3rd Term', '3rd Term')]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schemes_of_work', verbose_name=_('subject'))
    term = models.CharField(_('term'), max_length=20, choices=TERM_CHOICES)
    week_number = models.PositiveIntegerField(_('week number'))
    topic = models.CharField(_('topic'), max_length=200, blank=True)
    topic_model = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='schemes_of_work', verbose_name=_('topic reference'))
    learning_objectives = models.TextField(_('learning objectives'), blank=True)
    resources = models.TextField(_('resources'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Scheme of Work')
        verbose_name_plural = _('Schemes of Work')
        ordering = ['subject', 'term', 'week_number']
        unique_together = [['subject', 'term', 'week_number']]
    
    def __str__(self):
        return f"{self.subject.name} - {self.term} Week {self.week_number}: {self.topic}"
