import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.academic import School, GalleryGroup

def ensure_system_groups():
    schools = School.objects.all()
    created_count = 0
    for school in schools:
        group, created = GalleryGroup.objects.get_or_create(
            name='Question Bank Photos',
            school=school,
            defaults={
                'description': 'Automatically created group for storing question-related images.',
                'is_system': True
            }
        )
        if created:
            created_count += 1
            print(f"Created system group for {school.name}")
        else:
            print(f"System group already exists for {school.name}")
    print(f"Done. Created {created_count} groups.")

if __name__ == '__main__':
    ensure_system_groups()
