
import os
import django
from unittest.mock import patch, MagicMock

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver,localhost,127.0.0.1')
os.environ.setdefault('DEBUG', 'True')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from api.models import User, Student, FeeType, FeePayment, Class, SessionTerm, School, Session
from api.views.fee import FeePaymentViewSet
from decimal import Decimal
import datetime

def run_verification():
    print("--- Starting Fee Payment Verification ---")

    # 1. Setup Data
    print("\n1. Setting up test data...")
    
    # Create School & Session
    school, _ = School.objects.get_or_create(
        name="Test School", 
        defaults={'school_type': 'Secondary_Test', 'code': 'TEST-SCH'}
    )
    # If it existed, we use it. If it's new, we set defaults.
    # Note: school_type choices might be restricted. Let's check choices or use a valid one if we can't create random strings.
    # Based on model definition: SCHOOL_TYPE_CHOICES = ['Nursery', 'Primary', 'Junior Secondary', 'Senior Secondary']
    # And it's unique. So we should probably try to GET one of the existing types first, or try creating one if it doesn't exist.
    
    # Better approach: Try to get 'Primary' school, if fail, try 'Junior Secondary', etc.
    school = School.objects.first()
    if not school:
        school = School.objects.create(name="Test School", school_type="Primary")
    
    print(f"   Using School: {school.name} ({school.school_type})")
    
    session, _ = Session.objects.get_or_create(name="2025/2026", defaults={'start_date': datetime.date(2025, 9, 1), 'end_date': datetime.date(2026, 7, 30)})
    # Ensure session is current
    if not session.is_current:
        session.is_current = True
        session.save()
        
    term, _ = SessionTerm.objects.get_or_create(
        term_name="1st Term", 
        session=session,
        defaults={
             'start_date': datetime.date(2025, 9, 1),
             'end_date': datetime.date(2025, 12, 15),
             'is_current': True
        }
    )
    
    import time
    timestamp = int(time.time())
    
    # Create Class
    class_model, _ = Class.objects.get_or_create(
        name="JSS 1", 
        school=school,
        defaults={'class_code': f'JSS1-TEST-{timestamp}'} 
    )
    
    # Create Student
    user, _ = User.objects.get_or_create(email="student@test.com", defaults={'user_type': 'student'})
    student, _ = Student.objects.get_or_create(
        user=user,
        school=school,
        class_model=class_model,
        defaults={'admission_number': f'TEST/{timestamp}'}
    )
    print(f"   Student created: {student.admission_number}")

    # Create Staff (Admin)
    staff_user, _ = User.objects.get_or_create(email="admin@test.com", defaults={'user_type': 'admin'})
    
    # Create Fee Type (Total: 200)
    fee_type, _ = FeeType.objects.get_or_create(
        name="Tuition Fee",
        school=school,
        defaults={
            'amount': 200.00,
            'is_active': True,
            'is_mandatory': True
        }
    )
    # Ensure amount is 200 for test
    fee_type.amount = 200.00
    fee_type.save()
    print(f"   Fee Type created: {fee_type.name} (Amount: {fee_type.amount})")

    # 2. Test Manual Payment (Partial: 100)
    print("\n2. Testing Manual Payment (100.00)...")
    
    factory = APIRequestFactory()
    view = FeePaymentViewSet.as_view({'post': 'record_payment'})
    
    data = {
        'student': student.id,
        'fee_type': fee_type.id,
        'amount': 100.00,
        'payment_method': 'cash',
        'payment_date': datetime.date.today(),
        'reference_number': 'REF-001'
    }
    
    request = factory.post('/api/fee-payments/record_payment/', data)
    force_authenticate(request, user=staff_user)

    # MOCK the email function to verify it gets called
    with patch('api.utils.email.send_student_fee_receipt') as mock_email:
        mock_email.return_value = True
        
        response = view(request)
        
        if response.status_code == 201:
            print("   ✅ Payment recorded successfully (HTTP 201)")
            
            # Verify Email was called
            if mock_email.called:
                print("   ✅ EMAIL VERIFICATION: send_student_fee_receipt was triggered.")
                payment_arg = mock_email.call_args[0][0]
                print(f"      Receipt sent for payment ID: {payment_arg.id}, Amount: {payment_arg.amount}")
            else:
                print("   ❌ EMAIL VERIFICATION FAILED: email function was NOT called.")
        else:
            print(f"   ❌ Payment failed: {response.data}")
            return

    # 3. Verify Partial Balance
    print("\n3. Verifying Remaining Balance...")
    
    # Calculate balance using the model method (simulating what the view does)
    # We can also call the 'student_fees' endpoint to be sure
    
    view_status = FeePaymentViewSet.as_view({'get': 'student_fees'})
    request_status = factory.get(f'/api/fee-payments/student_fees/?student={student.id}')
    force_authenticate(request, user=staff_user) # Viewing as admin for student
    
    response_status = view_status(request_status)
    
    if response_status.status_code == 200:
        student_fees = response_status.data
        # Find our fee
        target_fee = next((f for f in student_fees if f['fee_type_id'] == fee_type.id), None)
        
        if target_fee:
            print(f"   Fee Status Summary:")
            print(f"   - Total Amount: {target_fee['total_amount']}")
            print(f"   - Amount Paid: {target_fee['amount_paid']}")
            print(f"   - Amount Remaining: {target_fee['amount_remaining']}")
            print(f"   - Status: {target_fee['status']}")
            
            if float(target_fee['amount_remaining']) == 100.00:
                print("   ✅ BALANCE VERIFICATION: Remaining amount is correctly 100.00")
            else:
                print(f"   ❌ BALANCE VERIFICATION FAILED: Expected 100.00, got {target_fee['amount_remaining']}")
                
            if target_fee['status'] == 'partial':
                 print("   ✅ STATUS VERIFICATION: Status is correctly 'partial'")
            else:
                 print(f"   ❌ STATUS VERIFICATION FAILED: Expected 'partial', got {target_fee['status']}")

        else:
            print("   ❌ Could not find fee type in status response")
    else:
        print(f"   ❌ Failed to fetch student fees: {response_status.data}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
