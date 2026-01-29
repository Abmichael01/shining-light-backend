import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Student, Staff

# Check if there are any students linked to staff
print("Checking student-staff relationships...")
total_students = Student.objects.count()
print(f"Total students: {total_students}")

# Check if children relationship exists
students_with_staff_parents = Student.objects.filter(parent_staff__isnull=False).count()
print(f"Students with staff parents (via parent_staff): {students_with_staff_parents}")

# Check from staff side
staff_with_children = Staff.objects.filter(children__isnull=False).distinct()
print(f"Staff with children: {staff_with_children.count()}")

for staff in staff_with_children:
    children = staff.children.all()
    print(f"\n{staff.get_full_name()} has {children.count()} children:")
    for child in children:
        print(f"  - {child.get_full_name()} (Admission: {child.admission_number})")

# Try to get one student to test
if total_students > 0:
    student = Student.objects.first()
    print(f"\nTesting with student: {student.get_full_name()}")
    print(f"Student admission number: {student.admission_number}")
    
    # Check if this student has staff parents
    parent_staff = Staff.objects.filter(children=student)
    if parent_staff.exists():
        print(f"This student is child of: {', '.join([s.get_full_name() for s in parent_staff])}")
