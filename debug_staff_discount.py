import os
import django
import sys
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Student, FeeType, FeePayment, User, Staff, BioData
from api.models.academic import Session, SessionTerm, School, Class
from api.serializers import RecordFeePaymentSerializer
from rest_framework.test import APIRequestFactory

def debug_staff_discount():
    print("--- Debugging Staff Discount Logic ---")
    
    # 1. Setup Environment
    school = School.objects.first() or School.objects.create(name="Test School", slug="test-school")
    cls = Class.objects.first() or Class.objects.create(name="JSS1", school=school)
    
    session = Session.objects.filter(is_current=True).first()
    if not session:
        session = Session.objects.create(name="2025/2026 Test", is_current=True)
    
    term = SessionTerm.objects.filter(is_current=True).first()
    if not term:
        term = SessionTerm.objects.create(session=session, name="First Term Test", is_current=True)

    # 2. Create Staff
    user_staff = User.objects.create_user(email='staff_parent@example.com', password='password123', user_type='staff')
    staff = Staff.objects.create(
        user=user_staff,
        surname="Parent",
        first_name="Staff",
        staff_id="STF-TEST-001",
        school=school,
        date_of_birth="1980-01-01"
    )
    print(f"Created Staff: {staff}")

    # 3. Create Student (Staff Kid)
    user_student = User.objects.create_user(email='staff_kid@example.com', password='password123', user_type='student')
    student = Student.objects.create(
        user=user_student,
        school=school,
        class_model=cls,
        application_number="APP-KID-001"
    )
    BioData.objects.create(
        student=student,
        surname="Parent",
        first_name="Kid",
        gender="male",
        date_of_birth="2015-01-01",
        state_of_origin="Lagos",
        permanent_address="Staff Quarters"
    )
    print(f"Created Student: {student}")
    
    # 4. Link Student to Staff
    staff.children.add(student)
    print("✅ Linked Student to Staff")
    
    # Verify Link
    if student.staff_parents.exists():
        print("✅ Student.staff_parents.exists() is True")
    else:
        print("❌ Student.staff_parents.exists() is False")

    # 5. Create Fee Type with Discount
    FULL_AMOUNT = 10000
    DISCOUNT_AMOUNT = 5000
    
    fee_type, _ = FeeType.objects.get_or_create(
        name="Staff Kid Fee Test",
        school=school,
        defaults={
            'amount': FULL_AMOUNT, 
            'staff_children_amount': DISCOUNT_AMOUNT,
            'is_mandatory': True, 
            'is_active': True,
            'is_recurring_per_term': True
        }
    )
    # Ensure values are correct (in case it existed)
    fee_type.amount = FULL_AMOUNT
    fee_type.staff_children_amount = DISCOUNT_AMOUNT
    fee_type.save()
    
    print(f"Fee Type: {fee_type.name} (Full: {fee_type.amount}, Staff Kid: {fee_type.staff_children_amount})")
    
    # Check Applicable Amount
    applicable = fee_type.get_applicable_amount(student)
    print(f"Applicable Amount for Student: {applicable}")
    
    if applicable == DISCOUNT_AMOUNT:
        print("✅ Correctly identified discounted amount")
    else:
        print(f"❌ Failed to identify discount. Got {applicable}, Expected {DISCOUNT_AMOUNT}")

    # 6. Pay Discounted Amount
    print("\n--- Paying Discounted Amount ---")
    
    # Clean up previous payments
    FeePayment.objects.filter(student=student, fee_type=fee_type).delete()

    data = {
        'student': student.id,
        'fee_type': fee_type.id,
        'amount': DISCOUNT_AMOUNT,
        'payment_method': 'cash',
        'notes': 'Staff Kid Payment',
        'session': session.id,
        'session_term': term.id
    }
    
    factory = APIRequestFactory()
    request = factory.post('/api/record-payment/', data)
    request.user = User.objects.filter(is_superuser=True).first()
    
    serializer = RecordFeePaymentSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        payment = serializer.save()
        print(f"Payment Created: {payment.amount}")
        
        # 7. Check Status
        status = fee_type.get_student_status(student.id, session=session.id, session_term=term.id)
        print(f"Fee Status: {status}")
        
        if status == 'paid':
             print("✅ Status is PAID")
        else:
             print(f"❌ Status is {status} (Expected PAID)")
    else:
        print("Validation Failed:", serializer.errors)

if __name__ == "__main__":
    try:
        debug_staff_discount()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
