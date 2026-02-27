from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db import transaction

class Session(models.Model):
    """Academic session/year (e.g., 2024/2025)"""
    
    name = models.CharField(_('session name'), max_length=20, unique=True)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_current = models.BooleanField(_('current session'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Session')
        verbose_name_plural = _('Sessions')
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name}{'*' if self.is_current else ''}"
    
    def save(self, *args, **kwargs):
        if self.is_current:
            with transaction.atomic():
                Session.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self._create_first_session_term()
    
    def _create_first_session_term(self):
        SessionTerm.objects.get_or_create(
            session=self,
            term_name='1st Term',
            defaults={
                'start_date': self.start_date,
                'end_date': self.end_date,
                'is_current': True
            }
        )
    
    def create_next_term(self, term_name, start_date, end_date, registration_deadline=None):
        SessionTerm.objects.filter(session=self, is_current=True).update(is_current=False)
        session_term, created = SessionTerm.objects.get_or_create(
            session=self,
            term_name=term_name,
            defaults={
                'start_date': start_date,
                'end_date': end_date,
                'registration_deadline': registration_deadline,
                'is_current': True
            }
        )
        if not created:
            session_term.start_date = start_date
            session_term.end_date = end_date
            if registration_deadline is not None:
                session_term.registration_deadline = registration_deadline
            session_term.is_current = True
            session_term.save()
        return session_term
    
    @classmethod
    def get_current_session_term(cls):
        current_session = cls.objects.filter(is_current=True).first()
        if current_session:
            return current_session.session_terms.filter(is_current=True).first()
        return None
    
    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(_('End date must be after start date'))
        
        from django.db.models import Q
        overlapping = Session.objects.filter(
            Q(start_date__range=(self.start_date, self.end_date)) |
            Q(end_date__range=(self.start_date, self.end_date)) |
            Q(start_date__lte=self.start_date, end_date__gte=self.end_date)
        ).exclude(pk=self.pk)
        
        if overlapping.exists():
            raise ValidationError(_('Session dates overlap with existing session'))


class SessionTerm(models.Model):
    """Academic term within a session (e.g., 1st Term 2024/2025)"""
    
    TERM_CHOICES = [
        ('1st Term', '1st Term'),
        ('2nd Term', '2nd Term'),
        ('3rd Term', '3rd Term'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='session_terms', verbose_name=_('session'))
    term_name = models.CharField(_('term name'), max_length=20, choices=TERM_CHOICES)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    is_current = models.BooleanField(_('current term'), default=False)
    registration_deadline = models.DateField(_('registration deadline'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Session Term')
        verbose_name_plural = _('Session Terms')
        ordering = ['session', 'term_name']
        unique_together = [['session', 'term_name']]
    
    def __str__(self):
        return f"{self.term_name} - {self.session.name}{'*' if self.is_current else ''}"
    
    @property
    def term_order(self):
        order_map = {'1st Term': 1, '2nd Term': 2, '3rd Term': 3}
        return order_map.get(self.term_name, 0)
    
    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(_('End date must be after start date'))
        if self.session and self.start_date and self.end_date:
            if self.start_date < self.session.start_date:
                raise ValidationError(_('Term start date cannot be before session start date'))
            if self.end_date > self.session.end_date:
                raise ValidationError(_('Term end date cannot be after session end date'))
    
    def save(self, *args, **kwargs):
        if self.is_current:
            with transaction.atomic():
                SessionTerm.objects.filter(session=self.session, is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)
