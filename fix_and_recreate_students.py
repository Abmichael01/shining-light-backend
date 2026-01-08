#!/usr/bin/env python
"""Script to cleanup and recreate sample students/applicants"""
import os
import django
from datetime import date
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.user import User
from api.models.student import Student, BioData, Guardian
from api.models.academic import Class

print("=" * 70)
print("Cleaning up and Recreating Sample Students")
print("=" * 70)

# Emails to clean up
student_emails = [
    'student1@shininglightschools.com',
    'student2@shininglightschools.com',
    'student3@shininglightschools.com',
    'applicant1@example.com',
    'applicant2@example.com'
]

print("\n🧹 Cleaning up existing records...")
for email in student_emails:
    user = User.objects.filter(email=email).first()
    if user:
        # If there's a student profile, it will be deleted by CASCADE
        print(f"  - Deleting user and related profile: {email}")
        user.delete()
    else:
        print(f"  - User {email} already gone.")

# Final check for any students left with these emails just in case
Student.objects.filter(user__email__in=student_emails).delete()

print("\n✅ Cleanup complete. Now recreating students...")

# Re-run the student creation logic (copying from fixed part of create_sample_users.py)
admin_user = User.objects.filter(is_superuser=True).first()

primary_class = Class.objects.filter(name__icontains='Primary 3').first()
jss_class = Class.objects.filter(name__icontains='JSS 2').first()
sss_class = Class.objects.filter(name__icontains='SSS 1').first()

# Using the same data structure as before
student_data = [
    {
        'email': 'student1@shininglightschools.com',
        'password': 'student123',
        'class': primary_class,
        'status': 'enrolled',
        'biodata': {
            'surname': 'Ajayi', 'first_name': 'Emmanuel', 'other_names': 'Oluwafemi',
            'gender': 'male', 'date_of_birth': date(2014, 5, 12),
            'nationality': 'Nigerian', 'state_of_origin': 'Oyo',
            'permanent_address': '23 Bodija Estate, Ibadan, Oyo State',
            'blood_group': 'O+', 'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'father', 'surname': 'Ajayi', 'first_name': 'Babatunde',
            'state_of_origin': 'Oyo', 'phone_number': '+234 808 456 7890',
            'email': 'b.ajayi@example.com', 'occupation': 'Civil Engineer',
            'place_of_employment': 'Oyo State Ministry of Works', 'is_primary_contact': True
        }
    },
    {
        'email': 'student2@shininglightschools.com',
        'password': 'student123',
        'class': jss_class,
        'status': 'enrolled',
        'biodata': {
            'surname': 'Musa', 'first_name': 'Aisha', 'other_names': 'Hauwa',
            'gender': 'female', 'date_of_birth': date(2011, 9, 18),
            'nationality': 'Nigerian', 'state_of_origin': 'Kaduna',
            'permanent_address': '56 Kachia Road, Kaduna State',
            'blood_group': 'A+', 'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'mother', 'surname': 'Musa', 'first_name': 'Zainab',
            'state_of_origin': 'Kaduna', 'phone_number': '+234 809 567 8901',
            'email': 'z.musa@example.com', 'occupation': 'Teacher',
            'place_of_employment': 'Government Secondary School', 'is_primary_contact': True
        }
    },
    {
        'email': 'student3@shininglightschools.com',
        'password': 'student123',
        'class': sss_class,
        'status': 'enrolled',
        'biodata': {
            'surname': 'Okonkwo', 'first_name': 'Chinedu', 'other_names': 'Ikenna',
            'gender': 'male', 'date_of_birth': date(2009, 2, 25),
            'nationality': 'Nigerian', 'state_of_origin': 'Anambra',
            'permanent_address': '102 Ogbaru Street, Onitsha, Anambra State',
            'blood_group': 'B+', 'has_medical_condition': False
        },
        'status': 'enrolled',
        'guardian': {
            'guardian_type': 'father', 'surname': 'Okonkwo', 'first_name': 'Emeka',
            'state_of_origin': 'Anambra', 'phone_number': '+234 806 678 9012',
            'email': 'e.okonkwo@example.com', 'occupation': 'Business Owner',
            'place_of_employment': 'Okonkwo Trading Company', 'is_primary_contact': True
        }
    }
]

applicant_data = [
    {
        'email': 'applicant1@example.com',
        'password': 'applicant123',
        'class': primary_class,
        'biodata': {
            'surname': 'Yusuf', 'first_name': 'Maryam', 'other_names': 'Khadija',
            'gender': 'female', 'date_of_birth': date(2015, 1, 30),
            'nationality': 'Nigerian', 'state_of_origin': 'Kano',
            'permanent_address': '34 Murtala Mohammed Way, Kano State',
            'blood_group': 'AB+', 'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'father', 'surname': 'Yusuf', 'first_name': 'Ibrahim',
            'state_of_origin': 'Kano', 'phone_number': '+234 810 123 4567',
            'email': 'i.yusuf@example.com', 'occupation': 'Banker',
            'place_of_employment': 'Diamond Bank', 'is_primary_contact': True
        }
    },
    {
        'email': 'applicant2@example.com',
        'password': 'applicant123',
        'class': jss_class,
        'biodata': {
            'surname': 'Williams', 'first_name': 'David', 'other_names': 'Oluwatobi',
            'gender': 'male', 'date_of_birth': date(2012, 6, 14),
            'nationality': 'Nigerian', 'state_of_origin': 'Lagos',
            'permanent_address': '89 Victoria Island, Lagos State',
            'blood_group': 'O-', 'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'mother', 'surname': 'Williams', 'first_name': 'Funmilayo',
            'state_of_origin': 'Lagos', 'phone_number': '+234 811 234 5678',
            'email': 'f.williams@example.com', 'occupation': 'Accountant',
            'place_of_employment': 'PwC Nigeria', 'is_primary_contact': True
        }
    }
]

def create_student_record(data, is_applicant=False):
    try:
        # Create user
        user = User.objects.create(
            email=data['email'],
            user_type='applicant' if is_applicant else 'student',
            is_active=True
        )
        user.set_password(data['password'])
        user.save()
        
        # Create student profile - Applicant status first
        student = Student.objects.create(
            user=user,
            school=data['class'].school,
            class_model=data['class'],
            status='applicant',
            source='online_application' if is_applicant else 'admin_registration',
            created_by=admin_user
        )
        
        # Create biodata (before generated admission number)
        bio_info = data['biodata']
        BioData.objects.create(
            student=student,
            surname=bio_info['surname'],
            first_name=bio_info['first_name'],
            other_names=bio_info.get('other_names', ''),
            gender=bio_info['gender'],
            date_of_birth=bio_info['date_of_birth'],
            nationality=bio_info['nationality'],
            state_of_origin=bio_info['state_of_origin'],
            permanent_address=bio_info['permanent_address'],
            blood_group=bio_info.get('blood_group', ''),
            has_medical_condition=bio_info.get('has_medical_condition', False)
        )
        
        # Create guardian
        if 'guardian' in data:
            guard_info = data['guardian']
            Guardian.objects.create(
                student=student,
                guardian_type=guard_info['guardian_type'],
                surname=guard_info['surname'],
                first_name=guard_info['first_name'],
                state_of_origin=guard_info['state_of_origin'],
                phone_number=guard_info['phone_number'],
                email=guard_info.get('email', ''),
                occupation=guard_info['occupation'],
                place_of_employment=guard_info['place_of_employment'],
                is_primary_contact=guard_info.get('is_primary_contact', False)
            )
            
        # If not just an applicant, upgrade to enrolled
        if not is_applicant and data.get('status') == 'enrolled':
            student.status = 'enrolled'
            student.enrollment_date = date.today()
            student.save() # This triggers admission number generation
            print(f"  ✓ Created enrolled student: {data['email']} (Admission: {student.admission_number})")
        else:
            print(f"  ✓ Created applicant: {data['email']}")
            
    except Exception as e:
        print(f"  ✗ Error creating {data['email']}: {str(e)}")

print("\n🚀 Creating Enrolled Students...")
for d in student_data:
    create_student_record(d)

print("\n🚀 Creating Applicants...")
for d in applicant_data:
    create_student_record(d, is_applicant=True)

print("\n" + "=" * 70)
print("✅ DONE")
print("=" * 70)
