import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType

def cleanup_orphans():
    print("🧹 Cleaning up Orphaned/Invalid Global Fees...")
    
    # Fees that MUST have class restrictions. 
    # If they have 0 classes, it means they failed to find their target classes in that school
    # and defaulted to 'Global', which is wrong.
    strict_targeted_fees = [
        "Nursery Tuition",
        "Primary Tuition", 
        "JSS Tuition", 
        "SSS Tuition", 
        "Lab Fee"
    ]
    
    total_deleted = 0
    
    for name in strict_targeted_fees:
        # Find fees with this name that have NO applicable classes
        orphans = FeeType.objects.filter(name=name, applicable_classes__isnull=True)
        # Note: In Django ManyToMany, filter(field__isnull=True) checks for empty relation? 
        # Actually safer is annotate Count.
        
        from django.db.models import Count
        orphans = FeeType.objects.filter(name=name).annotate(
            class_count=Count('applicable_classes')
        ).filter(class_count=0)
        
        count = orphans.count()
        if count > 0:
            print(f"  Found {count} invalid global '{name}' records.")
            for fee in orphans:
                print(f"    - Deleting '{fee.name}' from School: {fee.school.name} ({fee.school.id})")
                fee.delete()
            total_deleted += count
            
    print(f"\n✅ Cleanup complete. Total deleted: {total_deleted}")

if __name__ == '__main__':
    cleanup_orphans()
