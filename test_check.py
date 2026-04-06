import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType, Student
s14 = Student.objects.filter(biodata__first_name__icontains='14').first() or Student.objects.last()
print(f'Checking Student: {s14} (ID: {s14.id})')
pens = FeeType.objects.filter(is_penalty=True)
for p in pens:
    print(f'Penalty: {p.name} (Amount: {p.amount}, School: {p.school.name})')
    print(f'  Applicable students: {list(p.applicable_students.values_list("id", flat=True))}')
    print(f'  Applicable classes: {list(p.applicable_classes.values_list("id", flat=True))}')
    
    ctx = p.get_payment_status_context(s14)
    print(f'  Status for {s14}: {ctx}')
