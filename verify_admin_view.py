
import os
import django
from unittest.mock import patch, MagicMock

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver,localhost,127.0.0.1')
os.environ.setdefault('DEBUG', 'True')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from api.models import User, Student, FeeType, Class, SessionTerm, School, Session
from api.views.fee import FeePaymentViewSet
import datetime


def run_verification():
    print("--- Starting Admin View Verification (Existing Data) ---")

    # 1. Fetching existing test data...
    print("\n1. Fetching existing test data...")
    
    student = Student.objects.last() # Get latest student
    if not student:
        print("❌ No students found in database. Cannot test.")
        return

    admin_user = User.objects.filter(user_type='admin').first() or User.objects.filter(is_staff=True).first()
    if not admin_user:
        print("❌ No admin user found. Cannot test.")
        return

    # Try to find a session/term
    session = Session.objects.filter(is_current=True).first() or Session.objects.last()
    term = SessionTerm.objects.filter(is_current=True, session=session).first() if session else SessionTerm.objects.last()

    print(f"   Using Student: {student.admission_number} (ID: {student.id})")
    print(f"   Using Admin: {admin_user.email}")
    if session: print(f"   Using Session: {session.name} (ID: {session.id})")
    if term: print(f"   Using Term: {term.term_name} (ID: {term.id})")

    factory = APIRequestFactory()
    view = FeePaymentViewSet.as_view({'get': 'student_fees'})
    
    # 2. Case A: Request WITHOUT Params (Admin View Simulation)
    print("\n2. Case A: Request WITHOUT Params (Admin View)")
    # Admin portal usually calls: /api/fee-payments/student_fees/?student=ID
    request_a = factory.get(f'/api/fee-payments/student_fees/?student={student.id}')
    force_authenticate(request_a, user=admin_user)
    
    response_a = view(request_a)
    print(f"   Status Code: {response_a.status_code}")
    if response_a.status_code == 200:
        data_a = response_a.data
        count_a = len(data_a)
        print(f"   Fees Found: {count_a}")
    else:
        print(f"   Error: {response_a.data}")
        count_a = 0
    
    # 3. Case B: Request WITH Params (Student Portal Simulation)
    print("\n3. Case B: Request WITH Params (Student View)")
    if session and term:
        url_b = f'/api/fee-payments/student_fees/?student={student.id}&session={session.id}&session_term={term.id}'
        request_b = factory.get(url_b)
        force_authenticate(request_b, user=admin_user)
        
        response_b = view(request_b)
        print(f"   Status Code: {response_b.status_code}")
        if response_b.status_code == 200:
            data_b = response_b.data
            count_b = len(data_b)
            print(f"   Fees Found: {count_b}")
        else:
            print(f"   Error: {response_b.data}")
            count_b = 0
    else:
        print("   Skipping Case B: No session/term found.")
        count_b = 0

    print("\n--- Summary ---")
    if count_a == 0 and count_b > 0:
        print("✅ HYPOTHESIS CONFIRMED: Admin view (no params) returns 0 fees, while specific session params return data.")
    elif count_a == count_b and count_a > 0:
        print("ℹ️  Both views return data. The issue might be frontend data handling or specific to the user's browser state (e.g., stale cache).")
    elif count_a == 0 and count_b == 0:
        print("❌ Both views return 0. The student likely has NO fees assigned for this session/term.")

if __name__ == "__main__":
    run_verification()
