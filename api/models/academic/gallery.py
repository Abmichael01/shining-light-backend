from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from .schools import School

class GalleryGroup(models.Model):
    """Groups for school gallery images"""
    name = models.CharField(_('group name'), max_length=100)
    description = models.TextField(_('description'), blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='gallery_groups', verbose_name=_('school'))
    is_system = models.BooleanField(_('system group'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Gallery Group')
        verbose_name_plural = _('Gallery Groups')
        unique_together = [['name', 'school']]
        ordering = ['-is_system', 'name']

    def __str__(self):
        return f"{self.name} ({self.school.name})"

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

@receiver(post_save, sender=School)
def create_default_gallery_groups(sender, instance, created, **kwargs):
    """Ensure the 'Question Bank Photos' group exists for every school"""
    GalleryGroup.objects.get_or_create(
        name='Question Bank Photos',
        school=instance,
        defaults={
            'description': 'Automatically created group for storing question-related images.',
            'is_system': True
        }
    )
