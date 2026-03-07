from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from .schools import School

class GalleryGroup(models.Model):
    """Groups for global gallery images"""
    name = models.CharField(_('group name'), max_length=100)
    description = models.TextField(_('description'), blank=True, null=True)
    is_system = models.BooleanField(_('system group'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Gallery Group')
        verbose_name_plural = _('Gallery Groups')
        ordering = ['-is_system', 'name']

    def __str__(self):
        return self.name

class GalleryImage(models.Model):
    """Individual images in the school gallery"""
    image = models.ImageField(_('image'), upload_to='gallery/')
    group = models.ForeignKey(GalleryGroup, on_delete=models.CASCADE, related_name='images', verbose_name=_('group'))
    title = models.CharField(_('title'), max_length=200, blank=True, null=True)
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Gallery Image')
        verbose_name_plural = _('Gallery Images')
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title or f"Image {self.id}"

# System will ensure initial groups via management commands or manual entry
