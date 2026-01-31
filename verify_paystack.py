
import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from api.models import User, Student, FeeType
from api.views.fee import FeePaymentViewSet

def verify_paystack_init():
    print("--- Verifying Paystack Initialization Endpoint ---")
    
    # 1. Get Data
    student = Student.objects.last()
    fee_type = FeeType.objects.last()
    admin_user = User.objects.filter(user_type='admin').first() or User.objects.filter(is_superuser=True).first()
    
    if not student or not fee_type or not admin_user:
        print("❌ Missing test data (Student, FeeType, or Admin)")
        return

    print(f"   Student: {student.admission_number}")
    print(f"   Fee Type: {fee_type.name}")

    # 2. Simulate Request
    factory = APIRequestFactory()
    view = FeePaymentViewSet.as_view({'post': 'initialize_payment'})
    
    data = {
        'fee_type_id': fee_type.id,
        'amount': '5000',
        'student_id': student.id  # New required param for Admin
    }
    
    print("   Testing as Admin User...")
    request = factory.post('/api/fee-payments/initialize_payment/', data, format='json')
    force_authenticate(request, user=admin_user)
    
    try:
        response = view(request)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.data.keys()}")
            if 'authorization_url' in response.data:
                print("   ✅ Paystack Init Successful (URL returned)")
            else:
                print(f"   ❌ Paystack Init Failed (No URL): {response.data}")
        else:
            print(f"   ❌ Endpoint Error: {response.data}")
            
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    verify_paystack_init()
