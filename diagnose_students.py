#!/usr/bin/env python
"""Script to investigate student creation issues"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.user import User
from api.models.student import Student, BioData

print("=" * 70)
print("Investigating Student Creation Issues")
print("=" * 70)

# Check for orphaned user accounts (users without student profiles)
student_emails = [
    'student1@shininglightschools.com',
    'student2@shininglightschools.com',
    'student3@shininglightschools.com',
    'applicant1@example.com',
    'applicant2@example.com'
]

print("\n🔍 Checking user accounts:")
for email in student_emails:
    user = User.objects.filter(email=email).first()
    if user:
        has_profile = hasattr(user, 'student_profile') and user.student_profile is not None
        print(f"  ✓ User exists: {email}")
        print(f"    - User ID: {user.id}, Type: {user.user_type}")
        print(f"    - Has student profile: {has_profile}")
        if has_profile:
            student = user.student_profile
            print(f"    - Student ID: {student.id}")
            print(f"    - Application #: {student.application_number}")
            print(f"    - Admission #: {student.admission_number or 'Not generated'}")
            print(f"    - Status: {student.status}")
            try:
                biodata = student.biodata
                print(f"    - Has biodata: Yes ({biodata.surname} {biodata.first_name})")
            except:
                print(f"    - Has biodata: No")
    else:
        print(f"  ✗ User does not exist: {email}")
    print()

print("\n📋 All Student records in database:")
all_students = Student.objects.all()
print(f"Total: {all_students.count()}")
for student in all_students:
    print(f"\n  Student: {student.id}")
    print(f"  - Application #: {student.application_number}")
    print(f"  - Admission #: {student.admission_number or 'None'}")
    print(f"  - Status: {student.status}")
    print(f"  - User: {student.user.email if student.user else 'No user'}")
    try:
        biodata = student.biodata
        print(f"  - Biodata: {biodata.surname} {biodata.first_name}")
    except:
        print(f"  - Biodata: None")

print("\n" + "=" * 70)
print("\n💡 DIAGNOSIS:")
print("-" * 70)

# Count orphaned users
orphaned_users = []
for email in student_emails:
    user = User.objects.filter(email=email).first()
    if user and not (hasattr(user, 'student_profile') and user.student_profile):
        orphaned_users.append(email)

if orphaned_users:
    print(f"\n⚠️  Found {len(orphaned_users)} orphaned user account(s) (user exists but no student profile):")
    for email in orphaned_users:
        print(f"  - {email}")
    print("\n📝 Solution: These user accounts need to be deleted before re-running the script,")
    print("   OR the script needs to handle existing user accounts properly.")
else:
    print("\n✓ No orphaned user accounts found.")

# Check for students with blank admission numbers
blank_admission = Student.objects.filter(admission_number='')
if blank_admission.exists():
    print(f"\n⚠️  Found {blank_admission.count()} student(s) with blank admission numbers:")
    for student in blank_admission:
        print(f"  - {student.application_number} (Status: {student.status})")
    print("\n📝 This causes UNIQUE constraint violations when trying to create new students.")
else:
    print("\n✓ No students with blank admission numbers.")

print("\n" + "=" * 70)
