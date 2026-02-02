import os
import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType, Student
from django.db.models import Q
from api.serializers import StudentFeeStatusSerializer
from django.db.models import Sum

@pytest.mark.django_db
def test_prereq():
    print("Testing Prerequisite Logic...")
    
    # 1. Setup Data
    from api.models import School, Class, Session, SessionTerm
    from django.utils import timezone
    
    # Create School
    school, _ = School.objects.get_or_create(
        school_type='Junior Secondary',
        defaults={'name': 'Test School'}
    )
    
    # Create Class
    class_model, _ = Class.objects.get_or_create(
        name='JSS 1',
        school=school,
        defaults={'class_code': 'JSS1'}
    )
    
    # Create Session/Term
    session, _ = Session.objects.get_or_create(
        name='2025/2026',
        defaults={
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timezone.timedelta(days=365)
        }
    )
    term = session.session_terms.first()
    
    # Create Student
    student = Student.objects.create(
        school=school,
        class_model=class_model,
        first_name="Test",
        surname="Student"
    )
    print(f"Student: {student.get_full_name()}")
    
    # 2. Create Fees
    jss_tuition = FeeType.objects.create(
        name='JSS Tuition', 
        school=school, 
        amount=50000
    )
    pta_fee = FeeType.objects.create(
        name='PTA Fee', 
        school=school,
        amount=5000
    )
    
    # 3. Add Prereq (Tuition depends on PTA)
    print(f"Adding dependency: {jss_tuition.name} requires {pta_fee.name}")
    jss_tuition.prerequisites.add(pta_fee)
    jss_tuition.save()
    
    # 4. Mock View Logic (Simulate what student_fees view does)
    # Check JSS Tuition Status
    is_locked = False
    locked_message = ""
    
    prereqs = jss_tuition.prerequisites.all()
    for p in prereqs:
        paid = p.get_student_total_paid(student.id)
        print(f"Checking {p.name}: Paid {paid} / {p.amount}")
        if paid < p.amount:
            is_locked = True
            locked_message = f"Requires {p.name} to be paid first"
            break
            
    print(f"\nResult for {jss_tuition.name}:")
    print(f"Is Locked? {is_locked}")
    print(f"Message: {locked_message}")
    
    # Toggle off for future testing ease? (Optional, maybe keep it to show user)
    # jss_tuition.prerequisites.remove(pta_fee)

if __name__ == '__main__':
    test_prereq()
