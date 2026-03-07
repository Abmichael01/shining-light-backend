import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import FeeType, Class, Student
from django.db.models import Q, Count

student = Student.objects.first()
term_id = student.current_term.id if student.current_term else None

print(f"Testing for student in Class: {student.class_model.name}")

# Create a brand new fee to replicate exactly the user's report
fee, created = FeeType.objects.get_or_create(
    school=student.school,
    name="Test Classless Fee",
    amount=5000,
)
if created:
    fee.applicable_classes.clear()
    fee.active_terms.clear()
    
# Replicate the exact ORM query
fees_qs = FeeType.objects.filter(
    school=student.school,
    is_active=True
).annotate(
    class_count=Count('applicable_classes')
).filter(
    Q(class_count=0) | 
    Q(applicable_classes=student.class_model)
)

print("\n--- After Class Filter ---")
print("SQL:", fees_qs.query)
print("Count:", fees_qs.count())
print("Test Fee in results:", fees_qs.filter(id=fee.id).exists())

if term_id:
    fees_qs = fees_qs.filter(
        Q(active_terms__id=term_id) |
        Q(is_recurring_per_term=True) |
        Q(active_terms__isnull=True)
    )

print("\n--- After Term Filter ---")
print("SQL:", fees_qs.query)
print("Count:", fees_qs.count())
print("Test Fee in results:", fees_qs.filter(id=fee.id).exists())


fees_qs_debug = fees_qs.distinct()
print("\n--- After Distinct ---")
print("SQL:", fees_qs_debug.query)
print("Count:", fees_qs_debug.count())
print("Test Fee in results:", fees_qs_debug.filter(id=fee.id).exists())
