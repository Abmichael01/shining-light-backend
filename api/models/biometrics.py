from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class BiometricStation(models.Model):
    """
    Represents a physical biometric scanning station (laptop/PC).
    Used for API Key authentication for the Desktop App.
    """
    name = models.CharField(_('station name'), max_length=100, unique=True)
    api_key = models.UUIDField(_('API key'), default=uuid.uuid4, unique=True, editable=False)
    location = models.CharField(_('location'), max_length=100, blank=True)
    is_active = models.BooleanField(_('is active'), default=True)
    last_seen = models.DateTimeField(_('last seen'), auto_now=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Biometric Station')
        verbose_name_plural = _('Biometric Stations')

    def __str__(self):
        return f"{self.name} ({self.api_key})"
