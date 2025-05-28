# core/apps.py
from django.apps import AppConfig
from django.utils.text import slugify
from django.db.models.signals import post_migrate

def setup_core(sender, **kwargs):
    from core.models import School
    from core.models import Class

    # Create schools
    primary, _ = School.objects.get_or_create(name="Primary")
    secondary, _ = School.objects.get_or_create(name="Secondary")

    # Create classes with slugs
    for i in range(1, 3):
        Class.objects.get_or_create(
            name=f"Nursery {i}",
            school=primary,
            defaults={'slug': slugify(f"nursery-{i}")}
        )

    for i in range(1, 6):
        Class.objects.get_or_create(
            name=f"Primary {i}",
            school=primary,
            defaults={'slug': slugify(f"primary-{i}")}
        )

    for i in range(1, 4):
        Class.objects.get_or_create(
            name=f"JSS {i}",
            school=secondary,
            defaults={'slug': slugify(f"jss-{i}")}
        )
        Class.objects.get_or_create(
            name=f"SSS {i}",
            school=secondary,
            defaults={'slug': slugify(f"sss-{i}")}
        )

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        post_migrate.connect(setup_core, sender=self)