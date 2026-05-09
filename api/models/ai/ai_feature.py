from django.db import models
from django.utils.translation import gettext_lazy as _


class AIFeature(models.Model):
    """Catalog of AI-powered features available in the platform.

    Drives the AI hub page on each portal. Toggle `is_active` to launch or
    pause a feature without redeploying.
    """

    AUDIENCE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('student', 'Student'),
        ('all', 'All Users'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('coming_soon', 'Coming Soon'),
        ('beta', 'Beta'),
    ]

    slug = models.SlugField(_('slug'), max_length=64, unique=True)
    name = models.CharField(_('name'), max_length=120)
    description = models.TextField(_('description'))
    audience = models.CharField(_('audience'), max_length=20, choices=AUDIENCE_CHOICES, default='admin')
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='available')

    icon = models.CharField(_('icon name'), max_length=50, blank=True, default='Sparkles',
                            help_text=_('lucide-react icon component name, e.g. "Sparkles", "Bot"'))
    route = models.CharField(_('route'), max_length=200, blank=True,
                             help_text=_('Frontend route this feature opens, or empty if it lives inside another page'))

    is_active = models.BooleanField(_('active'), default=True)
    order = models.PositiveSmallIntegerField(_('order'), default=0)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('AI Feature')
        verbose_name_plural = _('AI Features')
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['audience', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_audience_display()})"
