import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType, PaymentPurpose, Class, School, User
from django.db.models import Q

def seed_fees():
    print("🌱 Seeding Fee Data (Refined)...")
    
    schools = School.objects.all()
    if not schools.exists():
        print("❌ No school found.")
        return
        
    admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
    
    for school in schools:
        print(f"\n🏫 Processing School: {school.name} ({school.id})")
        
        # 1. Cleanup Old Global Tuition
        global_tuition = FeeType.objects.filter(name="Tuition Fee", school=school)
        if global_tuition.exists():
            count = global_tuition.count()
            global_tuition.delete()
            print(f"  🗑️  Deleted {count} old 'Tuition Fee' record(s).")
        
        # 2. Define Fees
        # ... (fees_config same as before)
        fees_config = [
            # Tiered Tuition
            {
                "name": "Nursery Tuition",
                "amount": 40000.00,
                "description": "Tuition for Nursery classes",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "Nursery"
            },
            {
                "name": "Primary Tuition",
                "amount": 50000.00,
                "description": "Tuition for Primary classes",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "Primary"
            },
            {
                "name": "JSS Tuition",
                "amount": 60000.00,
                "description": "Tuition for Junior Secondary classes",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "JSS"
            },
            {
                "name": "SSS Tuition",
                "amount": 70000.00,
                "description": "Tuition for Senior Secondary classes",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "SSS"
            },
            
            # General Fees
            {
                "name": "PTA Fee",
                "amount": 5000.00,
                "description": "Parents Teachers Association levy",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "all"
            },
            {
                "name": "Exam Fee",
                "amount": 2000.00,
                "description": "Examination materials",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "all"
            },
            {
                "name": "Lab Fee",
                "amount": 10000.00,
                "description": "Science laboratory practicals",
                "is_mandatory": True,
                "is_recurring": True,
                "target": "senior_only"
            }
        ]
        
        for fee in fees_config:
            # Check if exists (by name)
            if FeeType.objects.filter(name=fee['name'], school=school).exists():
                print(f"  ⚠️  Fee '{fee['name']}' already exists. Skipping.")
                continue
            
            ft = FeeType.objects.create(
                name=fee['name'],
                school=school,
                amount=fee['amount'],
                description=fee['description'],
                is_mandatory=fee['is_mandatory'],
                is_recurring_per_term=fee['is_recurring'],
                created_by=admin
            )
            print(f"  ✅ Created '{fee['name']}'")

            # Assign Classes
            target = fee['target']
            classes_to_assign = []
            
            if target == 'all':
                ft.applicable_classes.clear()
            else:
                if target == 'Nursery':
                    classes_to_assign = Class.objects.filter(name__icontains='Nursery', school=school)
                    # Fallback if classes shared across schools (usually Class has FK to School)
                    if not classes_to_assign.exists():
                         classes_to_assign = Class.objects.filter(name__icontains='Nursery')
                elif target == 'Primary':
                    classes_to_assign = Class.objects.filter(name__icontains='Primary', school=school)
                    if not classes_to_assign.exists():
                         classes_to_assign = Class.objects.filter(name__icontains='Primary')
                elif target == 'JSS':
                    classes_to_assign = Class.objects.filter(name__icontains='JSS', school=school)
                    if not classes_to_assign.exists():
                         classes_to_assign = Class.objects.filter(name__icontains='JSS')
                elif target == 'SSS' or target == 'senior_only':
                    classes_to_assign = Class.objects.filter(name__icontains='SSS', school=school)
                    if not classes_to_assign.exists():
                         classes_to_assign = Class.objects.filter(name__icontains='SSS')
                
                if classes_to_assign.exists():
                    ft.applicable_classes.set(classes_to_assign)
                    print(f"     -> Assigned to {classes_to_assign.count()} classes ({target})")
                else:
                    print(f"     ⚠️  No classes found for target '{target}' in this school")

if __name__ == '__main__':
    seed_fees()
