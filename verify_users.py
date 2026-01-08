#!/usr/bin/env python
"""Script to verify created sample users"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.user import User
from api.models.staff import Staff
from api.models.student import Student, BioData

print("=" * 70)
print("Sample Users Summary")
print("=" * 70)

# Count users
staff_count = Staff.objects.count()
student_count = Student.objects.count()
user_count = User.objects.exclude(is_superuser=True).count()

print(f"\n📊 Statistics:")
print(f"  Total Users (non-admin): {user_count}")
print(f"  Staff Profiles: {staff_count}")
print(f"  Student/Applicant Profiles: {student_count}")

print(f"\n👥 Staff Members ({staff_count}):")
for staff in Staff.objects.all()[:10]:
    print(f"  - {staff.get_full_name():40} | ID: {staff.staff_id} | {staff.user.email}")

print(f"\n👨‍🎓 Students/Applicants ({student_count}):")
for student in Student.objects.all()[:10]:
    try:
        biodata = student.biodata
        name = f"{biodata.surname} {biodata.first_name}"
    except:
        name = "No biodata"
    user_email = student.user.email if student.user else "No user account"
    print(f"  - {name:40} | {student.status:12} | {user_email}")

print("\n" + "=" * 70)
