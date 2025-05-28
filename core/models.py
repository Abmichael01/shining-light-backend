from django.db import models
from django.utils.text import slugify
from django.db.models import UniqueConstraint

class School(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        

class Class(models.Model):
    name = models.CharField(max_length=50)  # "Nursery 1", "JSS 3"
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes')
    slug = models.SlugField(editable=False, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['school', 'slug'],
                name='unique_class_slug_per_school'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.school.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.school.name}-{self.name}")
        super().save(*args, **kwargs)