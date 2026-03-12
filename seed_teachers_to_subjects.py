#!/usr/bin/env python
import os
import django
import random
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.user import User
from api.models.staff import Staff
from api.models.academic import Subject, School

def seed_teachers():
    print("🚀 Starting teacher seeding...")
    
    # Get an admin for created_by
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("❌ No admin user found. Please create a superuser first.")
        return

    # Get schools
    schools = list(School.objects.all())
    if not schools:
        print("❌ No schools found. Please seed schools first.")
        return

    teacher_names = [
        ("Adebayo", "Oluwaseun", "mr"),
        ("Ibrahim", "Fatima", "mrs"),
        ("Okafor", "Chioma", "miss"),
        ("Williams", "David", "mr"),
        ("Yusuf", "Maryam", "mrs")
    ]

    new_teachers = []

    for surname, first_name, title in teacher_names:
        email = f"{first_name.lower()}.{surname.lower()}@shininglightschools.com"
        
        # Create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'user_type': 'staff',
                'is_active': True
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            print(f"  ✓ Created user: {email}")
        
        # Create staff
        staff, created = Staff.objects.get_or_create(
            user=user,
            defaults={
                'title': title,
                'surname': surname,
                'first_name': first_name,
                'state_of_origin': 'Lagos',
                'date_of_birth': date(1990, 1, 1),
                'permanent_address': '123 School Road',
                'phone_number': '08000000000',
                'marital_status': 'single',
                'religion': 'christian',
                'staff_type': 'teaching',
                'school': random.choice(schools),
                'zone': 'ransowa',
                'status': 'active',
                'created_by': admin_user
            }
        )
        if created:
            print(f"  ✓ Created staff: {staff.get_full_name()} ({staff.staff_id})")
        
        new_teachers.append(staff)

    # Assign all subjects to all teachers (user request: "add them to all subjects available")
    print("\n📚 Assigning teachers to subjects...")
    all_subjects = Subject.objects.all()
    
    for subject in all_subjects:
        # Add all 5 teachers to each subject
        subject.assigned_teachers.add(*new_teachers)
        print(f"  ✓ Assigned teachers to {subject.name} ({subject.code})")

    print("\n✅ Seeding completed successfully!")

if __name__ == "__main__":
    seed_teachers()
