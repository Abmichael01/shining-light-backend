import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType, Student
from django.db.models import Q
from api.serializers import StudentFeeStatusSerializer
from django.db.models import Sum

def test_prereq():
    print("Testing Prerequisite Logic...")
    
    # 1. Get Student
    student = Student.objects.first()
    print(f"Student: {student.get_full_name()}")
    
    # 2. Get Fees
    jss_tuition = FeeType.objects.filter(name='JSS Tuition', school=student.school).last()
    pta_fee = FeeType.objects.filter(name='PTA Fee', school=student.school).last()
    
    if not jss_tuition or not pta_fee:
        print("Fees not found. Exiting.")
        return

    # 3. Add Prereq (Tuition depends on PTA)
    print(f"Adding dependency: {jss_tuition.name} requires {pta_fee.name}")
    jss_tuition.prerequisites.clear() # Clear first
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
