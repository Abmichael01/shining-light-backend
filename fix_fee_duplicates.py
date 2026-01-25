import os
import django
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType, FeePayment, School

def cleanup_duplicates():
    print("🧹 Starting Fee De-duplication...")
    
    schools = School.objects.all()
    total_deleted = 0
    
    for school in schools:
        print(f"\nScanning School: {school.name} ({school.id})")
        
        # Group fees by name
        fees = FeeType.objects.filter(school=school).order_by('created_at')
        grouped = defaultdict(list)
        
        for fee in fees:
            grouped[fee.name].append(fee)
            
        for name, fee_list in grouped.items():
            if len(fee_list) > 1:
                print(f"  Found {len(fee_list)} copies of '{name}'")
                
                # Check payments
                to_keep = None
                to_delete = []
                
                # Prioritize keeping one with payments
                for fee in fee_list:
                    payment_count = FeePayment.objects.filter(fee_type=fee).count()
                    if payment_count > 0:
                        if to_keep is None:
                            to_keep = fee
                            print(f"    - Keeping ID {fee.id} (Has {payment_count} payments)")
                        else:
                            print(f"    - WARNING: Multiple fees named '{name}' have payments! Skipping delete for safety.")
                            to_keep = None # Abort for this group to be safe
                            break
                
                # If non have payments, or we found safe one
                if to_keep is None:
                    # Keep the LATEST created one (assuming it's the most correct/recent seed)
                    to_keep = fee_list[-1]
                    print(f"    - Keeping ID {to_keep.id} (Latest created)")
                
                # Mark others for deletion
                for fee in fee_list:
                    if fee.id != to_keep.id:
                        to_delete.append(fee)
                
                # Execute delete
                if to_delete:
                    delete_count = len(to_delete)
                    ids = [str(f.id) for f in to_delete]
                    FeeType.objects.filter(id__in=[f.id for f in to_delete]).delete()
                    print(f"    🗑️  Deleted {delete_count} duplicates (IDs: {', '.join(ids)})")
                    total_deleted += delete_count

    print(f"\n✅ cleanup complete. Total deleted: {total_deleted}")

if __name__ == '__main__':
    cleanup_duplicates()
