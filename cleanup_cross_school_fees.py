import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType

def cleanup_cross_school():
    print("🧹 Cleaning up Cross-School Fee Assignments...")
    
    all_fees = FeeType.objects.all()
    deleted_count = 0
    
    for fee in all_fees:
        # Check if fee has classes
        classes = fee.applicable_classes.all()
        if not classes.exists():
            continue
            
        # Check if any class belongs to a DIFFERENT school
        # Note: Class model usually has 'school' FK.
        # If class.school != fee.school, it's a cross-school assignment (result of bad seeding fallback)
        
        has_foreign_classes = False
        foreign_schools = set()
        
        for cls in classes:
            if cls.school_id != fee.school_id:
                has_foreign_classes = True
                foreign_schools.add(cls.school.name)
        
        if has_foreign_classes:
            print(f"  ❌ Invalid Fee: '{fee.name}' in '{fee.school.name}' targets classes in {foreign_schools}")
            # Delete it
            fee.delete()
            deleted_count += 1
            
    print(f"\n✅ Cleanup complete. Deleted {deleted_count} invalid fee records.")

if __name__ == '__main__':
    cleanup_cross_school()
