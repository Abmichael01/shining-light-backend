import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Biometric

def reset_biometrics():
    print("🚀 Starting Biometric Data Reset...")
    
    biometrics = Biometric.objects.all()
    count = biometrics.count()
    
    if count == 0:
        print("ℹ️ No biometric records found to delete.")
        return

    print(f"⚠️ Found {count} biometric records. Deleting...")
    
    # Bulk delete
    Biometric.objects.all().delete()
        
    print(f"✅ Successfully deleted {count} biometric records.")

if __name__ == "__main__":
    reset_biometrics()
