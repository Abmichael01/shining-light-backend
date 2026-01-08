#!/usr/bin/env python
"""Script to create sample users (students, staff, and applicants)"""
import os
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.user import User
from api.models.staff import Staff, StaffEducation, SalaryGrade, StaffSalary
from api.models.student import Student, BioData, Guardian
from api.models.academic import Class, School

print("=" * 70)
print("Creating Sample Users: Students, Staff, and Applicants")
print("=" * 70)

# Get admin user for created_by fields
admin_user = User.objects.filter(email='admin@gmail.com').first()
if not admin_user:
    admin_user = User.objects.filter(is_superuser=True).first()

# ========== CREATE STAFF USERS ==========
print("\n📋 Creating Staff Users...")
print("-" * 70)

staff_data = [
    {
        'email': 'teacher1@shininglightschools.com',
        'password': 'password123',
        'title': 'mr',
        'surname': 'Adeyemi',
        'first_name': 'Oluwaseun',
        'other_names': 'Adebayo',
        'nationality': 'Nigerian',
        'state_of_origin': 'Lagos',
        'date_of_birth': date(1990, 3, 15),
        'permanent_address': '45 Allen Avenue, Ikeja, Lagos State',
        'phone_number': '+234 803 123 4567',
        'marital_status': 'married',
        'religion': 'christian',
        'entry_date': date(2020, 9, 1),
        'staff_type': 'teaching',
        'zone': 'ransowa',
        'account_name': 'Oluwaseun Adeyemi Adebayo',
        'account_number': '0123456789',
        'bank_name': 'First Bank Nigeria',
        'education': {
            'level': 'tertiary',
            'institution_name': 'University of Lagos',
            'year_of_graduation': 2015,
            'degree': 'bed'
        }
    },
    {
        'email': 'teacher2@shininglightschools.com',
        'password': 'password123',
        'title': 'mrs',
        'surname': 'Ibrahim',
        'first_name': 'Fatima',
        'other_names': 'Zainab',
        'nationality': 'Nigerian',
        'state_of_origin': 'Kano',
        'date_of_birth': date(1988, 7, 22),
        'permanent_address': '12 Ahmadu Bello Way, Kano State',
        'phone_number': '+234 805 234 5678',
        'marital_status': 'married',
        'religion': 'muslim',
        'entry_date': date(2019, 1, 15),
        'staff_type': 'teaching',
        'zone': 'omoowo',
        'account_name': 'Fatima Zainab Ibrahim',
        'account_number': '0234567890',
        'bank_name': 'GTBank',
        'education': {
            'level': 'tertiary',
            'institution_name': 'Ahmadu Bello University',
            'year_of_graduation': 2012,
            'degree': 'bsc'
        }
    },
    {
        'email': 'admin.staff@shininglightschools.com',
        'password': 'password123',
        'title': 'miss',
        'surname': 'Okafor',
        'first_name': 'Chioma',
        'other_names': 'Grace',
        'nationality': 'Nigerian',
        'state_of_origin': 'Enugu',
        'date_of_birth': date(1992, 11, 8),
        'permanent_address': '78 Independence Layout, Enugu State',
        'phone_number': '+234 807 345 6789',
        'marital_status': 'single',
        'religion': 'christian',
        'entry_date': date(2021, 3, 1),
        'staff_type': 'non_teaching',
        'zone': 'ransowa',
        'account_name': 'Chioma Grace Okafor',
        'account_number': '0345678901',
        'bank_name': 'UBA',
        'education': {
            'level': 'tertiary',
            'institution_name': 'University of Nigeria, Nsukka',
            'year_of_graduation': 2016,
            'degree': 'bsc'
        }
    }
]

created_staff = []
for staff_info in staff_data:
    try:
        # Create user account
        user, user_created = User.objects.get_or_create(
            email=staff_info['email'],
            defaults={
                'user_type': 'staff',
                'is_staff': False,
                'is_active': True
            }
        )
        if user_created:
            user.set_password(staff_info['password'])
            user.save()
            print(f"  ✓ Created user: {staff_info['email']}")
        else:
            print(f"  • User exists: {staff_info['email']}")
        
        # Create or update staff profile
        staff, staff_created = Staff.objects.get_or_create(
            user=user,
            defaults={
                'title': staff_info['title'],
                'surname': staff_info['surname'],
                'first_name': staff_info['first_name'],
                'other_names': staff_info.get('other_names', ''),
                'nationality': staff_info['nationality'],
                'state_of_origin': staff_info['state_of_origin'],
                'date_of_birth': staff_info['date_of_birth'],
                'permanent_address': staff_info['permanent_address'],
                'phone_number': staff_info['phone_number'],
                'marital_status': staff_info['marital_status'],
                'religion': staff_info['religion'],
                'entry_date': staff_info['entry_date'],
                'staff_type': staff_info['staff_type'],
                'zone': staff_info['zone'],
                'account_name': staff_info.get('account_name', ''),
                'account_number': staff_info.get('account_number', ''),
                'bank_name': staff_info.get('bank_name', ''),
                'status': 'active',
                'created_by': admin_user
            }
        )
        
        if staff_created:
            print(f"  ✓ Created staff profile: {staff.get_full_name()} ({staff.staff_id})")
            
            # Create education record
            if 'education' in staff_info:
                edu_info = staff_info['education']
                edu, edu_created = StaffEducation.objects.get_or_create(
                    staff=staff,
                    level=edu_info['level'],
                    institution_name=edu_info['institution_name'],
                    defaults={
                        'year_of_graduation': edu_info['year_of_graduation'],
                        'degree': edu_info.get('degree', '')
                    }
                )
                if edu_created:
                    print(f"    → Added education: {edu_info['degree'].upper()} from {edu_info['institution_name']}")
            
            created_staff.append(staff)
        else:
            print(f"  • Staff profile exists: {staff.get_full_name()}")
            
    except Exception as e:
        print(f"  ✗ Error creating staff {staff_info['email']}: {str(e)}")

# ========== CREATE STUDENT USERS (ENROLLED) ==========
print("\n👨‍🎓 Creating Enrolled Student Users...")
print("-" * 70)

# Get some classes for assignment
primary_class = Class.objects.filter(name__icontains='Primary 3').first()
jss_class = Class.objects.filter(name__icontains='JSS 2').first()
sss_class = Class.objects.filter(name__icontains='SSS 1').first()

student_data = [
    {
        'email': 'student1@shininglightschools.com',
        'password': 'student123',
        'class': primary_class,
        'status': 'enrolled',
        'biodata': {
            'surname': 'Ajayi',
            'first_name': 'Emmanuel',
            'other_names': 'Oluwafemi',
            'gender': 'male',
            'date_of_birth': date(2014, 5, 12),
            'nationality': 'Nigerian',
            'state_of_origin': 'Oyo',
            'permanent_address': '23 Bodija Estate, Ibadan, Oyo State',
            'blood_group': 'O+',
            'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'father',
            'surname': 'Ajayi',
            'first_name': 'Babatunde',
            'state_of_origin': 'Oyo',
            'phone_number': '+234 808 456 7890',
            'email': 'b.ajayi@example.com',
            'occupation': 'Civil Engineer',
            'place_of_employment': 'Oyo State Ministry of Works',
            'is_primary_contact': True
        }
    },
    {
        'email': 'student2@shininglightschools.com',
        'password': 'student123',
        'class': jss_class,
        'status': 'enrolled',
        'biodata': {
            'surname': 'Musa',
            'first_name': 'Aisha',
            'other_names': 'Hauwa',
            'gender': 'female',
            'date_of_birth': date(2011, 9, 18),
            'nationality': 'Nigerian',
            'state_of_origin': 'Kaduna',
            'permanent_address': '56 Kachia Road, Kaduna State',
            'blood_group': 'A+',
            'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'mother',
            'surname': 'Musa',
            'first_name': 'Zainab',
            'state_of_origin': 'Kaduna',
            'phone_number': '+234 809 567 8901',
            'email': 'z.musa@example.com',
            'occupation': 'Teacher',
            'place_of_employment': 'Government Secondary School',
            'is_primary_contact': True
        }
    },
    {
        'email': 'student3@shininglightschools.com',
        'password': 'student123',
        'class': sss_class,
        'status': 'enrolled',
        'biodata': {
            'surname': 'Okonkwo',
            'first_name': 'Chinedu',
            'other_names': 'Ikenna',
            'gender': 'male',
            'date_of_birth': date(2009, 2, 25),
            'nationality': 'Nigerian',
            'state_of_origin': 'Anambra',
            'permanent_address': '102 Ogbaru Street, Onitsha, Anambra State',
            'blood_group': 'B+',
            'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'father',
            'surname': 'Okonkwo',
            'first_name': 'Emeka',
            'state_of_origin': 'Anambra',
            'phone_number': '+234 806 678 9012',
            'email': 'e.okonkwo@example.com',
            'occupation': 'Business Owner',
            'place_of_employment': 'Okonkwo Trading Company',
            'is_primary_contact': True
        }
    }
]

created_students = []
for student_info in student_data:
    try:
        if not student_info['class']:
            print(f"  ✗ Skipping student (class not found)")
            continue
            
        # Create user account
        user, user_created = User.objects.get_or_create(
            email=student_info['email'],
            defaults={
                'user_type': 'student',
                'is_staff': False,
                'is_active': True
            }
        )
        if user_created:
            user.set_password(student_info['password'])
            user.save()
            print(f"  ✓ Created user: {student_info['email']}")
        else:
            print(f"  • User exists: {student_info['email']}")
        
        # Create student profile with applicant status first (to avoid admission number generation)
        student = Student(
            user=user,
            school=student_info['class'].school,
            class_model=student_info['class'],
            status='applicant',  # Start as applicant
            source='admin_registration',
            created_by=admin_user
        )
        student.save()
        print(f"  ✓ Created student: {student.application_number}")
        
        # Create biodata
        bio_info = student_info['biodata']
        biodata = BioData.objects.create(
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
            has_medical_condition=bio_info.get('has_medical_condition', False),
            medical_condition_details=bio_info.get('medical_condition_details', '')
        )
        full_name = f"{biodata.surname} {biodata.first_name}"
        print(f"    → Full Name: {full_name}")
        print(f"    → Age: {biodata.get_age()} years")
        
        # Create guardian
        if 'guardian' in student_info:
            guard_info = student_info['guardian']
            guardian = Guardian.objects.create(
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
            print(f"    → Guardian: {guardian}")
        
        # Now update to enrolled status (admission number will be generated)
        if student_info['status'] == 'enrolled':
            student.status = 'enrolled'
            student.enrollment_date = date.today()
            student.save()
            print(f"    → Status: Enrolled (Admission: {student.admission_number})")
        
        created_students.append(student)
        
    except Exception as e:
        print(f"  ✗ Error creating student {student_info['email']}: {str(e)}")

# ========== CREATE APPLICANT USERS ==========
print("\n📝 Creating Applicant Users...")
print("-" * 70)

applicant_data = [
    {
        'email': 'applicant1@example.com',
        'password': 'applicant123',
        'class': primary_class,
        'biodata': {
            'surname': 'Yusuf',
            'first_name': 'Maryam',
            'other_names': 'Khadija',
            'gender': 'female',
            'date_of_birth': date(2015, 1, 30),
            'nationality': 'Nigerian',
            'state_of_origin': 'Kano',
            'permanent_address': '34 Murtala Mohammed Way, Kano State',
            'blood_group': 'AB+',
            'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'father',
            'surname': 'Yusuf',
            'first_name': 'Ibrahim',
            'state_of_origin': 'Kano',
            'phone_number': '+234 810 123 4567',
            'email': 'i.yusuf@example.com',
            'occupation': 'Banker',
            'place_of_employment': 'Diamond Bank',
            'is_primary_contact': True
        }
    },
    {
        'email': 'applicant2@example.com',
        'password': 'applicant123',
        'class': jss_class,
        'biodata': {
            'surname': 'Williams',
            'first_name': 'David',
            'other_names': 'Oluwatobi',
            'gender': 'male',
            'date_of_birth': date(2012, 6, 14),
            'nationality': 'Nigerian',
            'state_of_origin': 'Lagos',
            'permanent_address': '89 Victoria Island, Lagos State',
            'blood_group': 'O-',
            'has_medical_condition': False
        },
        'guardian': {
            'guardian_type': 'mother',
            'surname': 'Williams',
            'first_name': 'Funmilayo',
            'state_of_origin': 'Lagos',
            'phone_number': '+234 811 234 5678',
            'email': 'f.williams@example.com',
            'occupation': 'Accountant',
            'place_of_employment': 'PwC Nigeria',
            'is_primary_contact': True
        }
    }
]

created_applicants = []
for applicant_info in applicant_data:
    try:
        if not applicant_info['class']:
            print(f"  ✗ Skipping applicant (class not found)")
            continue
            
        # Create user account
        user, user_created = User.objects.get_or_create(
            email=applicant_info['email'],
            defaults={
                'user_type': 'applicant',
                'is_staff': False,
                'is_active': True
            }
        )
        if user_created:
            user.set_password(applicant_info['password'])
            user.save()
            print(f"  ✓ Created user: {applicant_info['email']}")
        else:
            print(f"  • User exists: {applicant_info['email']}")
        
        # Create student profile with applicant status
        student = Student(
            user=user,
            school=applicant_info['class'].school,
            class_model=applicant_info['class'],
            status='applicant',
            source='online_application',
            created_by=admin_user
        )
        student.save()
        print(f"  ✓ Created applicant: {student.application_number}")
        
        # Create biodata
        bio_info = applicant_info['biodata']
        biodata = BioData.objects.create(
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
            has_medical_condition=bio_info.get('has_medical_condition', False),
            medical_condition_details=bio_info.get('medical_condition_details', '')
        )
        print(f"    → Full Name: {biodata.get_full_name()}")
        
        # Create guardian
        if 'guardian' in applicant_info:
            guard_info = applicant_info['guardian']
            guardian = Guardian.objects.create(
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
            print(f"    → Guardian: {guardian}")
        
        created_applicants.append(student)
        
    except Exception as e:
        print(f"  ✗ Error creating applicant {applicant_info['email']}: {str(e)}")

# Print Summary
print("\n" + "=" * 70)
print("✅ SUMMARY")
print("=" * 70)
print(f"Staff created: {len(created_staff)}")
print(f"Students created: {len(created_students)}")
print(f"Applicants created: {len(created_applicants)}")
print("\n📋 Sample Login Credentials:")
print("-" * 70)
print("\nSTAFF:")
for staff_info in staff_data[:2]:  # Show first 2
    print(f"  Email: {staff_info['email']}")
    print(f"  Password: {staff_info['password']}")
    print()

print("STUDENTS:")
for student_info in student_data[:2]:  # Show first 2
    print(f"  Email: {student_info['email']}")
    print(f"  Password: {student_info['password']}")
    print()

print("APPLICANTS:")
for applicant_info in applicant_data[:2]:  # Show first 2
    print(f"  Email: {applicant_info['email']}")
    print(f"  Password: {applicant_info['password']}")
    print()

print("=" * 70)
print("✅ Script completed successfully!")
print("=" * 70)
